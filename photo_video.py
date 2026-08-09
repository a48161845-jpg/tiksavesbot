"""
Сборка фото-слайдшоу TikTok (фото + музыка) в одно MP4-видео — опция
"Как видео" в меню перед фото-пикером, аналог того, что иногда сам TikTok
предлагает для постов-каруселей ("посмотреть как видео").

Всё, что тут может пойти не так (сеть при скачивании фото/музыки, зависший
или упавший ffmpeg, нехватка ресурсов) — оборачивается в один тип исключения
SlideshowBuildError, чтобы вызывающий код мог поймать ровно одно исключение
и никогда не падал целиком из-за необработанной ошибки отсюда.
"""
import asyncio
import subprocess
from pathlib import Path
from typing import List, Optional

import aiohttp

from youtube_provider import _FFMPEG_PATH

PHOTO_DURATION_SEC = 2.5  # сколько секунд показывается каждое фото
MAX_PHOTOS_FOR_VIDEO = 20  # ограничение, чтобы не грузить сервер слишком большим слайдшоу
FFMPEG_TIMEOUT_SEC = 90  # с запасом, но не настолько долго, чтобы "подвесить" воркер


class SlideshowBuildError(Exception):
    pass


async def _download_file(session: aiohttp.ClientSession, url: str, dest: Path) -> None:
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status >= 400:
                raise SlideshowBuildError(f"HTTP {resp.status} при скачивании {url}")
            with dest.open("wb") as f:
                async for chunk in resp.content.iter_chunked(65536):
                    f.write(chunk)
    except SlideshowBuildError:
        raise
    except Exception as e:
        # Любая сетевая/файловая ошибка — тоже SlideshowBuildError, чтобы
        # вызывающий код гарантированно мог её поймать.
        raise SlideshowBuildError(f"Не удалось скачать {url}: {e.__class__.__name__}: {e}") from e


def _build_sync(photo_paths: List[Path], audio_path: Optional[Path], out_path: Path) -> None:
    if not _FFMPEG_PATH:
        raise SlideshowBuildError("ffmpeg недоступен на сервере")
    if not photo_paths:
        raise SlideshowBuildError("нет фото для сборки")

    list_path = out_path.with_suffix(".txt")
    try:
        lines = []
        for p in photo_paths:
            lines.append(f"file '{p.resolve().as_posix()}'")
            lines.append(f"duration {PHOTO_DURATION_SEC}")
        # Особенность concat-демуксера ffmpeg: последний файл нужно продублировать
        # без строки duration, иначе он не покажется полный положенный срок.
        lines.append(f"file '{photo_paths[-1].resolve().as_posix()}'")
        list_path.write_text("\n".join(lines), encoding="utf-8")

        cmd = [
            _FFMPEG_PATH, "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(list_path),
        ]
        if audio_path:
            # Зацикливаем звук на всю длину слайдшоу; -shortest потом обрежет
            # по видео (оно короче бесконечного луп-аудио).
            cmd += ["-stream_loop", "-1", "-i", str(audio_path)]
        cmd += [
            "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-r", "20",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
        ]
        if audio_path:
            cmd += ["-c:a", "aac", "-b:a", "128k", "-shortest"]
        cmd += ["-movflags", "+faststart", str(out_path)]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT_SEC)
        except subprocess.TimeoutExpired as e:
            raise SlideshowBuildError(f"ffmpeg не уложился в {FFMPEG_TIMEOUT_SEC} сек") from e
        except OSError as e:
            raise SlideshowBuildError(f"не удалось запустить ffmpeg: {e}") from e

        if result.returncode != 0 or not out_path.exists():
            err_tail = result.stderr.decode("utf-8", "ignore")[-500:] if result.stderr else "нет вывода"
            raise SlideshowBuildError(f"ffmpeg завершился с ошибкой: {err_tail}")
    finally:
        list_path.unlink(missing_ok=True)


async def build_photo_slideshow_video(
    session: aiohttp.ClientSession,
    photo_urls: List[str],
    music_url: Optional[str],
    out_dir: Path,
    name_prefix: str,
) -> Path:
    """Скачивает фото (+ музыку, если есть) и собирает их в одно MP4-видео через ffmpeg."""
    if not _FFMPEG_PATH:
        raise SlideshowBuildError("ffmpeg недоступен на сервере")
    if not photo_urls:
        raise SlideshowBuildError("нет фото для сборки")

    photo_urls = photo_urls[:MAX_PHOTOS_FOR_VIDEO]

    photo_paths: List[Path] = []
    audio_path: Optional[Path] = None
    try:
        for i, url in enumerate(photo_urls):
            p = out_dir / f"{name_prefix}_p{i}.jpg"
            await _download_file(session, url, p)
            photo_paths.append(p)

        if music_url:
            audio_path = out_dir / f"{name_prefix}_a.m4a"
            try:
                await _download_file(session, music_url, audio_path)
            except Exception:
                audio_path = None  # без музыки тоже нормально, просто продолжаем без звука

        out_path = out_dir / f"{name_prefix}_slideshow.mp4"
        try:
            await asyncio.to_thread(_build_sync, photo_paths, audio_path, out_path)
        except SlideshowBuildError:
            raise
        except Exception as e:
            raise SlideshowBuildError(f"{e.__class__.__name__}: {e}") from e
        return out_path
    except SlideshowBuildError:
        raise
    except Exception as e:
        raise SlideshowBuildError(f"{e.__class__.__name__}: {e}") from e
    finally:
        for p in photo_paths:
            p.unlink(missing_ok=True)
        if audio_path:
            audio_path.unlink(missing_ok=True)
