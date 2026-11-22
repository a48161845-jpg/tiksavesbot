"""
Обрезка фото под формат кадра (как в редакторе: 1:1, 4:3, 3:4, 16:9, 9:16) — по центру.

Чистая логика (crop_box) отделена от работы с файлами, чтобы её можно было проверять без Pillow.
Pillow импортируется лениво: если его нет или файл не открылся, вызывающий код отправит оригинал.
"""
import asyncio
from pathlib import Path
from typing import Dict, Optional, Tuple

# код формата -> (ширина, высота); orig — без обрезки
RATIOS: Dict[str, Optional[Tuple[int, int]]] = {
    "orig": None,
    "1x1": (1, 1),
    "4x3": (4, 3),
    "3x4": (3, 4),
    "16x9": (16, 9),
    "9x16": (9, 16),
}
RATIO_CODES = tuple(RATIOS)                      # порядок кнопок
RATIO_TITLES = {"1x1": "1:1", "4x3": "4:3", "3x4": "3:4", "16x9": "16:9", "9x16": "9:16"}

# Telegram принимает фото, у которых ширина + высота <= 10000 и соотношение сторон <= 20
_TG_MAX_SUM = 10000


def normalize_ratio(code: Optional[str]) -> str:
    return code if code in RATIOS else "orig"


def crop_box(w: int, h: int, rw: int, rh: int) -> Tuple[int, int, int, int]:
    """Рамка (left, top, right, bottom) максимального куска нужного формата по центру кадра."""
    if w <= 0 or h <= 0:
        raise ValueError("bad image size")
    target = rw / rh
    cur = w / h
    if abs(cur - target) < 0.004:
        return 0, 0, w, h
    if cur > target:  # кадр шире нужного — режем бока
        nw = max(1, round(h * target))
        left = (w - nw) // 2
        return left, 0, left + nw, h
    nh = max(1, round(w / target))  # кадр уже/выше нужного — режем верх и низ
    top = (h - nh) // 2
    return 0, top, w, top + nh


def _crop_sync(src: Path, dst: Path, ratio: str) -> Path:
    from PIL import Image, ImageOps  # ленивый импорт

    rw_rh = RATIOS[normalize_ratio(ratio)]
    if rw_rh is None:
        raise ValueError("ratio is orig")
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        box = crop_box(im.width, im.height, *rw_rh)
        out = im.crop(box)
        if out.mode not in ("RGB", "L"):
            out = out.convert("RGB")
        if out.width + out.height > _TG_MAX_SUM:
            k = _TG_MAX_SUM / (out.width + out.height)
            out = out.resize((max(1, int(out.width * k)), max(1, int(out.height * k))), Image.LANCZOS)
        out.save(dst, "JPEG", quality=93, optimize=True)
    return dst


async def crop_image(src: Path, dst: Path, ratio: str) -> Path:
    """Обрезает src под формат ratio и сохраняет JPEG в dst (в потоке, event loop не блокируется)."""
    return await asyncio.to_thread(_crop_sync, src, dst, ratio)
