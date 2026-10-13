"""
Запасной путь для X/Twitter, когда yt-dlp не справляется (чаще всего — 18+/«sensitive» твиты,
которые без входа в аккаунт не отдаются). Публичные зеркала FxTwitter / VxTwitter сами достают
твит и отдают прямые ссылки на mp4 (video.twimg.com) — вход не нужен.
Любая сетевая ошибка → None/исключение TwitterFallbackError, вызывающий код решает, что дальше.
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

_TW_ID_RE = re.compile(r"(?:twitter|x|fxtwitter|vxtwitter|fixupx)\.com/(?:i/web/|i/)?(?:([A-Za-z0-9_]+)/)?status(?:es)?/(\d+)", re.I)
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class TwitterFallbackError(Exception):
    pass


def is_twitter_url(url: str) -> bool:
    return bool(_TW_ID_RE.search(url or ""))


def _parse_ids(url: str):
    m = _TW_ID_RE.search(url or "")
    if not m:
        raise TwitterFallbackError("не удалось разобрать ссылку на твит")
    return (m.group(1) or "i"), m.group(2)


async def _get_json(session: aiohttp.ClientSession, api_url: str) -> Any:
    async with session.get(
        api_url, headers={"User-Agent": _UA, "Accept": "application/json"}, timeout=aiohttp.ClientTimeout(total=20)
    ) as r:
        if r.status >= 400:
            raise TwitterFallbackError(f"HTTP {r.status} от {api_url.split('/')[2]}")
        return await r.json(content_type=None)


def _from_fx(js: Dict[str, Any]) -> Dict[str, Any]:
    tw = js.get("tweet") or {}
    media = tw.get("media") or {}
    videos = []
    for v in media.get("videos") or media.get("all") or []:
        if not isinstance(v, dict) or v.get("type") not in (None, "video", "gif"):
            continue
        u = v.get("url")
        if isinstance(u, str) and u.startswith("http"):
            videos.append({"url": u, "width": int(v.get("width") or 0), "height": int(v.get("height") or 0),
                           "duration": float(v.get("duration") or 0)})
    return {"title": (tw.get("text") or "")[:200], "videos": videos}


def _from_vx(js: Dict[str, Any]) -> Dict[str, Any]:
    videos = []
    for v in js.get("media_extended") or []:
        if not isinstance(v, dict) or v.get("type") not in ("video", "gif"):
            continue
        u = v.get("url")
        if isinstance(u, str) and u.startswith("http"):
            size = v.get("size") or {}
            videos.append({"url": u, "width": int(size.get("width") or 0), "height": int(size.get("height") or 0),
                           "duration": float(v.get("duration_millis") or 0) / 1000.0})
    return {"title": (js.get("text") or "")[:200], "videos": videos}


async def fetch_twitter_media(url: str) -> Dict[str, Any]:
    """{'title', 'videos': [{'url','width','height','duration'}]}; бросает TwitterFallbackError, если видео не нашлось."""
    user, tid = _parse_ids(url)
    errors: List[str] = []
    async with aiohttp.ClientSession() as session:
        for api, parser in (
            (f"https://api.fxtwitter.com/{user}/status/{tid}", _from_fx),
            (f"https://api.fxtwitter.com/status/{tid}", _from_fx),
            (f"https://api.vxtwitter.com/{user}/status/{tid}", _from_vx),
        ):
            try:
                data = parser(await _get_json(session, api))
                if data["videos"]:
                    return data
                errors.append("в твите нет видео")
            except Exception as e:
                errors.append(f"{e.__class__.__name__}: {e}")
    raise TwitterFallbackError("; ".join(errors[-3:]) or "видео не найдено")


def pick_video(videos: List[Dict[str, Any]], max_height: Optional[int]) -> Dict[str, Any]:
    vids = sorted(videos, key=lambda v: v.get("height") or 0, reverse=True)
    if max_height:
        ok = [v for v in vids if (v.get("height") or 0) <= max_height or not v.get("height")]
        if ok:
            return ok[0]
        return vids[-1]
    return vids[0]


async def download_direct(url: str, dest: Path, max_bytes: int) -> Path:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers={"User-Agent": _UA, "Referer": "https://x.com/"},
                timeout=aiohttp.ClientTimeout(total=600),
            ) as r:
                if r.status >= 400:
                    raise TwitterFallbackError(f"HTTP {r.status} при скачивании видео")
                size = 0
                with dest.open("wb") as f:
                    async for chunk in r.content.iter_chunked(1 << 16):
                        size += len(chunk)
                        if size > max_bytes:
                            raise TwitterFallbackError(f"File too large (> {max_bytes} bytes)")
                        f.write(chunk)
        if size == 0:
            raise TwitterFallbackError("пустой файл")
        return dest
    except TwitterFallbackError:
        dest.unlink(missing_ok=True)
        raise
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise TwitterFallbackError(f"{e.__class__.__name__}: {e}") from e
