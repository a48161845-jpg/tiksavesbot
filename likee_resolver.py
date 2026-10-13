"""
Likee: короткие ссылки (l.likee.video/v/XXXX) серверам часто отдают редирект на главную
(https://likee.video/), и yt-dlp падает с «Unsupported URL». Поэтому ссылку разбираем сами:
  1) идём по редиректам с разными User-Agent и ищем в конечном URL/истории/HTML id поста;
  2) по id поста спрашиваем у API Likee прямую ссылку на видео;
  3) отдаём либо прямую ссылку (yt-dlp умеет качать прямой mp4), либо каноническую
     ссылку на пост, либо исходную — если ничего не вышло.
Все сетевые ошибки глотаются: в худшем случае возвращается исходная ссылка.
"""
import re
from typing import Any, List, Optional

import aiohttp

_UAS = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
)
_API = "https://api.like-video.com/likee-activity-flow-micro/videoApi/getVideoInfo"
_POST_ID_RES = (
    re.compile(r"/video/(\d{12,})"),
    re.compile(r"[\"']?post_?[iI]d[\"']?\s*[:=]\s*[\"']?(\d{12,})"),
    re.compile(r"[\"']?video_?[iI]d[\"']?\s*[:=]\s*[\"']?(\d{12,})"),
)
_VIDEO_META_RES = (
    re.compile(r"property=[\"']og:video(?::url|:secure_url)?[\"']\s+content=[\"']([^\"']+)", re.I),
    re.compile(r"content=[\"']([^\"']+\.mp4[^\"']*)[\"']\s+property=[\"']og:video", re.I),
    re.compile(r"[\"'](?:videoUrl|video_url|playUrl)[\"']\s*:\s*[\"'](https?:[^\"']+?)[\"']"),
)


def _is_home(url: str) -> bool:
    m = re.match(r"https?://[^/]+/?(?:\?.*)?$", url or "")
    return bool(m)


def _find_post_id(*texts: str) -> Optional[str]:
    for t in texts:
        for rx in _POST_ID_RES:
            m = rx.search(t or "")
            if m:
                return m.group(1)
    return None


def _deep_video_urls(data: Any, out: List[str], depth: int = 0) -> None:
    if depth > 6:
        return
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, str) and v.startswith("http") and k.lower() in ("videourl", "video_url", "playurl", "nowmurl", "url") and (
                ".mp4" in v or "video" in v.lower()
            ):
                out.append(v.replace("\\/", "/"))
            else:
                _deep_video_urls(v, out, depth + 1)
    elif isinstance(data, list):
        for v in data:
            _deep_video_urls(v, out, depth + 1)


async def _api_video_url(session: aiohttp.ClientSession, post_id: str) -> Optional[str]:
    try:
        async with session.post(
            _API,
            data={"postIds": post_id, "lang": "en", "country": "US"},
            headers={"User-Agent": _UAS[2], "Referer": "https://likee.video/", "Origin": "https://likee.video"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as r:
            js = await r.json(content_type=None)
    except Exception:
        return None
    urls: List[str] = []
    _deep_video_urls(js, urls)
    return urls[0] if urls else None


async def resolve_likee(url: str) -> str:
    """Возвращает ссылку, которую сможет скачать yt-dlp (прямой mp4 / страница поста), иначе исходную."""
    post_id = _find_post_id(url)
    final_urls: List[str] = []
    page_text = ""
    meta_video: Optional[str] = None

    try:
        async with aiohttp.ClientSession() as session:
            if not post_id:
                for ua in _UAS:
                    try:
                        async with session.get(
                            url, allow_redirects=True, headers={"User-Agent": ua, "Accept": "text/html,*/*"},
                            timeout=aiohttp.ClientTimeout(total=15),
                        ) as resp:
                            final_urls = [str(h.url) for h in resp.history] + [str(resp.url)]
                            body = await resp.content.read(400_000)
                            page_text = body.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    post_id = _find_post_id(*final_urls, page_text)
                    for rx in _VIDEO_META_RES:
                        m = rx.search(page_text)
                        if m:
                            meta_video = m.group(1).replace("\\u002F", "/").replace("\\/", "/").replace("&amp;", "&")
                            break
                    if post_id or meta_video:
                        break

            if post_id:
                direct = await _api_video_url(session, post_id)
                if direct:
                    return direct
                return f"https://likee.video/@likee/video/{post_id}"
            if meta_video:
                return meta_video
    except Exception:
        pass

    # хоть какая-то осмысленная итоговая ссылка (не главная страница)
    for u in reversed(final_urls):
        if not _is_home(u):
            return u
    return url
