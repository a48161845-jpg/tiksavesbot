"""
Сборка фото-слайдшоу TikTok (фото + live-клипы + музыка) в одно MP4-видео —
опция «Как видео» перед фото-пикером.

Как собираем (надёжно и без чёрных полос):
  1) каждый кадр рендерится в отдельный мини-ролик 720x1280@25fps: фото на
     размытом фоне из него же (вместо чёрных полос), у кадров с live photo
     вместо статичного фото берётся сам live-клип;
  2) ролики склеиваются concat-демуксером без перекодирования (одинаковые параметры);
  3) сверху накладывается музыка (зациклена и обрезана по длине видео, с затуханием).

Всё, что может пойти не так (сеть, ffmpeg), превращается в SlideshowBuildError —
вызывающий код ловит ровно одно исключение.
"""
import asyncio
import contextlib
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp

from youtube_provider import _FFMPEG_PATH
from media_fetch import download_url, MediaFetchError

log = logging.getLogger("photo_video")

PHOTO_DURATION_SEC = 2.5      # сколько секунд показывается каждое фото
LIVE_MAX_SEC = 3.5            # максимум секунд live-клипа в ролике
MAX_PHOTOS_FOR_VIDEO = 30     # ограничение на размер слайдшоу
SEG_TIMEOUT_SEC = 60
W, H, FPS = 720, 1280, 25


class SlideshowBuildError(Exception):
    pass


async def _download_file(session, url, dest, kind="photo", bot=None, chat_id=None):
    try:
        await download_url(session, url, dest, kind=kind, bot=bot, chat_id=chat_id)
    except MediaFetchError as e:
        raise SlideshowBuildError(str(e)) from e
    except Exception as e:
        raise SlideshowBuildError(f"Не удалось скачать {url}: {e.__class__.__name__}: {e}") from e


_FILTER = (
    f"split[a][b];"
    f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:6[bg];"
    f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
    f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS},format=yuv420p"
)


def _run(cmd: List[str], timeout: int, what: str) -> None:
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise SlideshowBuildError(f"ffmpeg ({what}) не уложился в {timeout} сек") from e
    except OSError as e:
        raise SlideshowBuildError(f"не удалось запустить ffmpeg: {e}") from e
    if r.returncode != 0:
        tail = r.stderr.decode("utf-8", "ignore")[-400:] if r.stderr else "нет вывода"
        raise SlideshowBuildError(f"ffmpeg ({what}) завершился с ошибкой: {tail}")


def _seg_still(img: Path, out: Path) -> None:
    _run([
        _FFMPEG_PATH, "-y", "-loglevel", "error",
        "-loop", "1", "-t", str(PHOTO_DURATION_SEC), "-i", str(img),
        "-vf", _FILTER, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(FPS), str(out),
    ], SEG_TIMEOUT_SEC, "кадр")


def _seg_live(clip: Path, out: Path) -> None:
    _run([
        _FFMPEG_PATH, "-y", "-loglevel", "error",
        "-t", str(LIVE_MAX_SEC), "-i", str(clip),
        "-vf", _FILTER, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(FPS), str(out),
    ], SEG_TIMEOUT_SEC, "live-клип")


def _probe_duration(src: Path) -> float:
    """Длительность файла в секундах (парсим stderr `ffmpeg -i`, ffprobe может отсутствовать); 0 — не удалось."""
    try:
        r = subprocess.run([_FFMPEG_PATH, "-hide_banner", "-i", str(src)], capture_output=True, timeout=30)
    except Exception:
        return 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr.decode("utf-8", "ignore"))
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def _mux_music(video: Path, audio: Path, out_path: Path) -> None:
    """
    Накладывает музыку на готовое видео без звука.

    БЫЛО (баг «звук не вставляется»): стоял фильтр afade=t=out:st=0:d=0.01 — то есть затухание
    начиналось на 0-й секунде и за 0.01 с звук гасился полностью, дальше шла тишина. Видео при этом
    собиралось «успешно», поэтому ошибки никто не видел. Теперь затухание — только последняя секунда.
    """
    dur = _probe_duration(video)
    base = [
        _FFMPEG_PATH, "-y", "-loglevel", "error", "-i", str(video),
        "-stream_loop", "-1", "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
    ]
    tail = ["-movflags", "+faststart", str(out_path)]
    attempts = []
    if dur > 0:
        fade = min(1.0, dur / 2)
        attempts.append(base + ["-af", f"afade=t=out:st={max(0.0, dur - fade):.2f}:d={fade:.2f}", "-t", f"{dur:.2f}"] + tail)
        attempts.append(base + ["-t", f"{dur:.2f}"] + tail)  # без фильтров — на случай капризного аудио
    attempts.append(base + ["-shortest"] + tail)

    last_err: Optional[Exception] = None
    for cmd in attempts:
        try:
            _run(cmd, SEG_TIMEOUT_SEC, "музыка")
            if out_path.exists() and out_path.stat().st_size > 0:
                return
        except SlideshowBuildError as e:
            last_err = e
            log.warning("photo_video: не удалось наложить музыку: %s", e)
    # музыка не легла (битый файл) — отдаём видео без звука, это лучше, чем ошибка
    log.error("photo_video: музыка не наложена, видео уйдёт без звука: %s", last_err)
    video.replace(out_path)


def _build_sync(items: List[Tuple[Path, Optional[Path]]], audio_path: Optional[Path], out_path: Path) -> None:
    if not _FFMPEG_PATH:
        raise SlideshowBuildError("ffmpeg недоступен на сервере")
    if not items:
        raise SlideshowBuildError("нет фото для сборки")

    segs: List[Path] = []
    list_path = out_path.with_suffix(".txt")
    joined = out_path.with_suffix(".joined.mp4")
    try:
        for i, (img, clip) in enumerate(items):
            seg = out_path.with_suffix(f".seg{i}.mp4")
            segs.append(seg)
            done = False
            if clip is not None:
                try:
                    _seg_live(clip, seg)
                    done = seg.exists() and seg.stat().st_size > 0
                except SlideshowBuildError:
                    done = False
            if not done:
                _seg_still(img, seg)

        list_path.write_text("\n".join(f"file '{s.resolve().as_posix()}'" for s in segs), encoding="utf-8")
        target = out_path if not audio_path else joined
        _run([
            _FFMPEG_PATH, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
            "-i", str(list_path), "-c", "copy", "-movflags", "+faststart", str(target),
        ], SEG_TIMEOUT_SEC, "склейка")

        if audio_path:
            _mux_music(joined, audio_path, out_path)
        if not out_path.exists() or out_path.stat().st_size == 0:
            raise SlideshowBuildError("ffmpeg не создал файл")
    finally:
        list_path.unlink(missing_ok=True)
        joined.unlink(missing_ok=True)
        for s in segs:
            s.unlink(missing_ok=True)


async def build_photo_slideshow_video(
    session: aiohttp.ClientSession,
    photo_urls: List[str],
    music_url: Optional[str],
    out_dir: Path,
    name_prefix: str,
    live: Optional[Dict[str, str]] = None,
    bot=None,
    chat_id: Optional[int] = None,
) -> Path:
    """Скачивает фото (+ live-клипы, музыку) и собирает MP4 через ffmpeg."""
    if not _FFMPEG_PATH:
        raise SlideshowBuildError("ffmpeg недоступен на сервере")
    if not photo_urls:
        raise SlideshowBuildError("нет фото для сборки")

    live = live or {}
    photo_urls = photo_urls[:MAX_PHOTOS_FOR_VIDEO]
    files: List[Path] = []
    items: List[Tuple[Path, Optional[Path]]] = []
    audio_path: Optional[Path] = None
    try:
        for i, url in enumerate(photo_urls):
            p = out_dir / f"{name_prefix}_p{i}.jpg"
            files.append(p)
            await _download_file(session, url, p, "photo", bot, chat_id)
            clip: Optional[Path] = None
            lu = live.get(url)
            if lu:
                c = out_dir / f"{name_prefix}_l{i}.mp4"
                files.append(c)
                try:
                    await _download_file(session, lu, c, "video", bot, chat_id)
                    clip = c
                except Exception:
                    clip = None  # live не скачался — останется обычное фото
            items.append((p, clip))

        if music_url:
            audio_path = out_dir / f"{name_prefix}_a.m4a"
            files.append(audio_path)
            try:
                await _download_file(session, music_url, audio_path, "audio", bot, chat_id)
            except Exception:
                audio_path = None

        out_path = out_dir / f"{name_prefix}_slideshow.mp4"
        try:
            await asyncio.to_thread(_build_sync, items, audio_path, out_path)
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
        for f in files:
            with contextlib.suppress(Exception):
                f.unlink(missing_ok=True)
