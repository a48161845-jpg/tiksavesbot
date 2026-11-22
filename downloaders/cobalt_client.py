"""
Запасной способ скачивания БЕЗ cookies: cobalt API (https://github.com/imputnet/cobalt).

Зачем: YouTube/Instagram с IP дата-центров (Render, VPS) часто отвечают yt-dlp
"Sign in to confirm you're not a bot". cobalt-инстанс умеет обходить это на своей
стороне. Включается переменными:
  COBALT_API_URL=https://твой-cobalt.example.com   (свой инстанс — надёжнее всего)
  COBALT_API_KEY=...                               (если инстанс требует ключ)
Если COBALT_API_URL не задан — модуль ничего не делает.
"""
import os
from pathlib import Path
from typing import Optional

import aiohttp

COBALT_API_URL = os.getenv("COBALT_API_URL", "").strip().rstrip("/")
COBALT_API_KEY = os.getenv("COBALT_API_KEY", "").strip()


def cobalt_enabled() -> bool:
    return bool(COBALT_API_URL)


class CobaltError(Exception):
    pass


async def cobalt_download(url: str, out_dir: Path, *, height: Optional[int] = None, audio_only: bool = False,
                          max_bytes: int = 0) -> Path:
    if not COBALT_API_URL:
        raise CobaltError("COBALT_API_URL не задан")
    headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "tiksavesbot"}
    if COBALT_API_KEY:
        headers["Authorization"] = f"Api-Key {COBALT_API_KEY}"
    body = {"url": url, "filenameStyle": "basic"}
    if audio_only:
        body.update({"downloadMode": "audio", "audioFormat": "mp3"})
    else:
        body.update({"downloadMode": "auto", "videoQuality": str(height or 1080), "youtubeVideoCodec": "h264"})

    timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=120)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.post(COBALT_API_URL + "/", json=body, headers=headers) as r:
            try:
                js = await r.json(content_type=None)
            except Exception:
                raise CobaltError(f"cobalt: неверный ответ (HTTP {r.status})")
        status = js.get("status")
        if status == "picker":
            items = js.get("picker") or []
            if not items:
                raise CobaltError("cobalt: пустой picker")
            js = {"status": "tunnel", "url": items[0].get("url"), "filename": "video.mp4"}
            status = "tunnel"
        if status not in ("tunnel", "redirect", "stream") or not js.get("url"):
            err = (js.get("error") or {}).get("code") if isinstance(js.get("error"), dict) else js.get("error")
            raise CobaltError(f"cobalt: {status or 'error'} {err or ''}".strip())

        name = js.get("filename") or ("audio.mp3" if audio_only else "video.mp4")
        suffix = Path(name).suffix or (".mp3" if audio_only else ".mp4")
        dest = out_dir / f"cobalt_{abs(hash(url)) % 10**10}{suffix}"
        size = 0
        async with s.get(js["url"], headers={"User-Agent": "Mozilla/5.0"}) as r2:
            if r2.status >= 400:
                raise CobaltError(f"cobalt: скачивание HTTP {r2.status}")
            try:
                with dest.open("wb") as f:
                    async for chunk in r2.content.iter_chunked(1 << 16):
                        size += len(chunk)
                        if max_bytes and size > max_bytes:
                            raise CobaltError("File too large")
                        f.write(chunk)
            except BaseException:
                dest.unlink(missing_ok=True)
                raise
    if size <= 0:
        dest.unlink(missing_ok=True)
        raise CobaltError("cobalt: пустой файл")
    return dest
