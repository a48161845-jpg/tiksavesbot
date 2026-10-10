"""
Сжатие видео через ffmpeg до заданного размера.

Нужно, когда бот работает через облачный Bot API (лимит отправки ~50 МБ):
вместо отказа "файл больше лимита" перекодируем видео так, чтобы оно
влезло. Если подключён Local Bot API Server (лимит 2 ГБ) — до сжатия дело
обычно не доходит.
"""
import asyncio
import re
import subprocess
from pathlib import Path
from typing import Optional

from youtube_provider import _FFMPEG_PATH

AUDIO_BITRATE = 96_000          # бит/с
MIN_VIDEO_BITRATE = 120_000     # ниже — картинка превращается в кашу, лучше отказать
FFMPEG_TIMEOUT_SEC = 900


class CompressError(Exception):
    pass


def _probe_duration(src: Path) -> float:
    """Длительность в секундах — парсим из stderr `ffmpeg -i` (ffprobe может отсутствовать)."""
    try:
        r = subprocess.run([_FFMPEG_PATH, "-hide_banner", "-i", str(src)],
                           capture_output=True, timeout=60)
    except Exception as e:
        raise CompressError(f"не удалось определить длительность: {e}") from e
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", r.stderr.decode("utf-8", "ignore"))
    if not m:
        raise CompressError("не удалось определить длительность видео")
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


def _run_ffmpeg(src: Path, dst: Path, v_bitrate: int, height: Optional[int]) -> None:
    vf = f"scale=-2:'min({height},ih)'," if height else ""
    vf += "format=yuv420p"
    cmd = [
        _FFMPEG_PATH, "-y", "-loglevel", "error", "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast",
        "-b:v", str(v_bitrate), "-maxrate", str(int(v_bitrate * 1.3)), "-bufsize", str(v_bitrate * 2),
        "-c:a", "aac", "-b:a", str(AUDIO_BITRATE),
        "-movflags", "+faststart",
        str(dst),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT_SEC)
    except subprocess.TimeoutExpired as e:
        raise CompressError("сжатие заняло слишком много времени") from e
    except OSError as e:
        raise CompressError(f"не удалось запустить ffmpeg: {e}") from e
    if r.returncode != 0 or not dst.exists():
        tail = r.stderr.decode("utf-8", "ignore")[-300:] if r.stderr else ""
        raise CompressError(f"ffmpeg завершился с ошибкой: {tail}")


def _compress_sync(src: Path, max_bytes: int) -> Path:
    if not _FFMPEG_PATH:
        raise CompressError("ffmpeg недоступен")
    duration = _probe_duration(src)
    if duration <= 0:
        raise CompressError("нулевая длительность")

    dst = src.with_name(src.stem + "_c.mp4")
    budget = 0.90  # запас на контейнер/погрешность rate-control
    for _ in range(3):
        total_bps = int(max_bytes * budget * 8 / duration)
        v_bps = total_bps - AUDIO_BITRATE
        if v_bps < MIN_VIDEO_BITRATE:
            raise CompressError("видео слишком длинное, чтобы уместиться в лимит Telegram")
        # Чем меньше битрейт — тем ниже разрешение, иначе будут квадраты.
        height = 1080 if v_bps > 3_000_000 else 720 if v_bps > 1_200_000 else 480 if v_bps > 500_000 else 360
        _run_ffmpeg(src, dst, v_bps, height)
        if dst.stat().st_size <= max_bytes:
            return dst
        budget *= 0.8
    dst.unlink(missing_ok=True)
    raise CompressError("не удалось сжать видео до нужного размера")


async def compress_to_limit(src: Path, max_bytes: int) -> Path:
    """Возвращает путь к сжатому файлу (≤ max_bytes). Исходный файл не трогает."""
    return await asyncio.to_thread(_compress_sync, src, max_bytes)
