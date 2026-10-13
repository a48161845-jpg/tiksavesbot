"""
Надёжная загрузка медиафайлов (фото/клипы/музыка) по прямым ссылкам CDN.

TikTok CDN (tiktokcdn*, p16/p19-common-sign…) нередко отвечает 403 серверным IP,
хотя Telegram сам эти же ссылки открывает без проблем. Поэтому порядок такой:
  1) несколько вариантов заголовков (с Referer / без / мобильный UA / Range);
  2) если всё равно 403/401 — просим сам Telegram забрать файл по URL
     (send_photo/send_video в технический чат), а затем скачиваем уже file_id.
Любая неудача → MediaFetchError (одно исключение для вызывающего кода).
"""
import contextlib
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp

from config import INLINE_CACHE_CHANNEL_ID


class MediaFetchError(Exception):
    pass


_UA_DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
_UA_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
_UA_APP = "com.zhiliaoapp.musically/2023700030 (Linux; U; Android 13; en_US; Pixel 7; Build/TQ3A.230901.001)"


def _header_variants(url: str) -> List[Dict[str, str]]:
    return [
        {"User-Agent": _UA_DESKTOP, "Accept": "*/*", "Referer": "https://www.tiktok.com/"},
        {"User-Agent": _UA_MOBILE, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"},
        {"User-Agent": _UA_APP, "Accept": "*/*"},
        {"User-Agent": _UA_DESKTOP, "Accept": "*/*", "Range": "bytes=0-"},
    ]


async def _http_get(session: aiohttp.ClientSession, url: str, dest: Path, max_bytes: int) -> Optional[int]:
    """Возвращает HTTP-статус при отказе (403/401/…), None при успехе."""
    last_status: Optional[int] = None
    for headers in _header_variants(url):
        try:
            async with session.get(
                url, headers=headers, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=40)
            ) as resp:
                if resp.status >= 400:
                    last_status = resp.status
                    if resp.status in (401, 403, 429):
                        continue
                    raise MediaFetchError(f"HTTP {resp.status} при скачивании {url}")
                size = 0
                with dest.open("wb") as f:
                    async for chunk in resp.content.iter_chunked(65536):
                        size += len(chunk)
                        if size > max_bytes:
                            raise MediaFetchError("файл слишком большой")
                        f.write(chunk)
                if size == 0:
                    last_status = 0
                    continue
                return None
        except MediaFetchError:
            raise
        except Exception as e:
            last_status = last_status or -1
            err = e
            continue
    return last_status if last_status is not None else -1


async def _via_telegram(bot, chat_id: int, url: str, dest: Path, kind: str) -> None:
    """Просим Telegram самому забрать URL, затем скачиваем file_id. Сообщение сразу удаляется."""
    msg = None
    try:
        if kind == "video":
            msg = await bot.send_video(chat_id, url, disable_notification=True)
            file_id = msg.video.file_id
        elif kind == "audio":
            msg = await bot.send_audio(chat_id, url, disable_notification=True)
            file_id = msg.audio.file_id
        else:
            msg = await bot.send_photo(chat_id, url, disable_notification=True)
            file_id = msg.photo[-1].file_id
        await bot.download(file_id, destination=dest)
    finally:
        if msg is not None:
            with contextlib.suppress(Exception):
                await bot.delete_message(chat_id, msg.message_id)


async def download_url(
    session: aiohttp.ClientSession,
    url: str,
    dest: Path,
    kind: str = "photo",
    bot=None,
    chat_id: Optional[int] = None,
    max_bytes: int = 200 * 1024 * 1024,
) -> Path:
    status = await _http_get(session, url, dest, max_bytes)
    if status is None:
        return dest
    dest.unlink(missing_ok=True)
    target = INLINE_CACHE_CHANNEL_ID or chat_id
    if bot is not None and target:
        for tgt in dict.fromkeys([t for t in (INLINE_CACHE_CHANNEL_ID, chat_id) if t]):
            try:
                await _via_telegram(bot, tgt, url, dest, kind)
                if dest.exists() and dest.stat().st_size > 0:
                    return dest
            except Exception:
                dest.unlink(missing_ok=True)
                continue
    raise MediaFetchError(f"HTTP {status} при скачивании {url}")


async def download_image_bytes(session, url: str, dest: Path, bot=None, chat_id: Optional[int] = None, kind: str = "photo") -> Path:
    """Совместимое имя (его ждёт send_helpers)."""
    return await download_url(session, url, dest, kind=kind, bot=bot, chat_id=chat_id)
