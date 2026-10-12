"""
Метаданные для отправки видео файлом: длительность, ширина/высота, миниатюра.

Зачем: если загрузить видео в Telegram "голым" файлом, без этих полей клиент
показывает чёрный квадрат вместо превью, не знает ориентацию (вертикальное
видео может выглядеть растянутым/обрезанным) и не показывает длительность.
Плюс "faststart" (moov-атом в начале файла) — без него видео нельзя
проигрывать до полной загрузки, а превью не строится.
"""
import asyncio
import contextlib
import re
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from aiogram.types import FSInputFile

from youtube_provider import _FFMPEG_PATH

FASTSTART_MAX_BYTES = 800 * 1024 * 1024  # не перепаковываем гигантские файлы — это долго


def _ffmpeg_info(path: Path) -> Dict[str, int]:
    """duration (сек), width, height из `ffmpeg -i` (ffprobe может отсутствовать). Нули — не удалось."""
    out = {"duration": 0, "width": 0, "height": 0}
    if not _FFMPEG_PATH:
        return out
    try:
        r = subprocess.run([_FFMPEG_PATH, "-hide_banner", "-i", str(path)], capture_output=True, timeout=30)
        txt = r.stderr.decode("utf-8", "ignore")
    except Exception:
        return out
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", txt)
    if m:
        out["duration"] = int(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)))
    m = re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", txt)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        # поворот из метаданных (rotate: 90/270) меняет ширину и высоту местами
        rot = re.search(r"rotate\s*:\s*(-?\d+)", txt)
        if rot and abs(int(rot.group(1))) in (90, 270):
            w, h = h, w
        out["width"], out["height"] = w, h
    return out


def _make_thumbnail(path: Path, duration: int) -> Optional[Path]:
    """JPEG ≤320 px по большей стороне (требование Telegram), кадр не из самого начала — он часто чёрный."""
    if not _FFMPEG_PATH:
        return None
    thumb = Path(tempfile.gettempdir()) / f"thumb_{uuid.uuid4().hex[:10]}.jpg"
    seek = 1 if duration >= 3 else 0
    vf = "scale='if(gt(iw,ih),320,-2)':'if(gt(iw,ih),-2,320)'"
    for ss in (seek, 0):
        try:
            subprocess.run(
                [_FFMPEG_PATH, "-y", "-loglevel", "error", "-ss", str(ss), "-i", str(path),
                 "-frames:v", "1", "-vf", vf, "-q:v", "5", str(thumb)],
                capture_output=True, timeout=60,
            )
        except Exception:
            continue
        if thumb.exists() and 0 < thumb.stat().st_size <= 200 * 1024:
            return thumb
        thumb.unlink(missing_ok=True)
    return None


def _faststart(path: Path) -> None:
    """Перепаковка mp4 без перекодирования, чтобы moov был в начале (стриминг + превью)."""
    if not _FFMPEG_PATH or path.suffix.lower() not in (".mp4", ".m4v", ".mov"):
        return
    try:
        if path.stat().st_size > FASTSTART_MAX_BYTES:
            return
        tmp = path.with_name(path.stem + ".fs.mp4")
        r = subprocess.run(
            [_FFMPEG_PATH, "-y", "-loglevel", "error", "-i", str(path),
             "-c", "copy", "-movflags", "+faststart", str(tmp)],
            capture_output=True, timeout=600,
        )
        if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
            tmp.replace(path)
        else:
            tmp.unlink(missing_ok=True)
    except Exception:
        with contextlib.suppress(Exception):
            path.with_name(path.stem + ".fs.mp4").unlink(missing_ok=True)


def _prepare_sync(path: Path) -> Dict[str, Any]:
    _faststart(path)
    info = _ffmpeg_info(path)
    kwargs: Dict[str, Any] = {"supports_streaming": True}
    if info["duration"]:
        kwargs["duration"] = info["duration"]
    if info["width"] and info["height"]:
        kwargs["width"], kwargs["height"] = info["width"], info["height"]
    thumb = _make_thumbnail(path, info["duration"])
    if thumb:
        kwargs["thumbnail"] = FSInputFile(thumb)
        kwargs["_thumb_path"] = thumb
    return kwargs


async def prepare_video_kwargs(path: Path) -> Dict[str, Any]:
    """
    Возвращает kwargs для answer_video/send_video: duration, width, height,
    thumbnail, supports_streaming. Никогда не бросает исключений — при любой
    проблеме отдаёт то, что удалось собрать (видео всё равно отправится).
    После отправки обязательно вызови cleanup_video_kwargs(kwargs).
    """
    try:
        return await asyncio.to_thread(_prepare_sync, path)
    except Exception:
        return {"supports_streaming": True}


def cleanup_video_kwargs(kwargs: Dict[str, Any]) -> None:
    thumb = kwargs.get("_thumb_path")
    if thumb:
        with contextlib.suppress(Exception):
            Path(thumb).unlink(missing_ok=True)


def telegram_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """kwargs без служебных полей — их и нужно передавать в answer_video."""
    return {k: v for k, v in kwargs.items() if not k.startswith("_")}
