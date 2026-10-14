"""
Запасные способы получить видео, когда yt-dlp не справился.

X (Twitter), 18+ контент
    yt-dlp без логина не может достать «чувствительные» твиты. Вместо cookies
    спрашиваем публичные API-зеркала (api.fxtwitter.com, api.vxtwitter.com) —
    они отдают прямые ссылки на mp4 с video.twimg.com. Свои хосты можно задать
    через TWITTER_FX_API_HOSTS (через запятую).

Reddit
    С IP дата-центров Reddit отвечает yt-dlp "Account authentication is required".
    Обход без cookies: 1) раскрываем короткую ссылку (/s/…, redd.it) и берём id поста;
    2) читаем JSON поста (www/old.reddit.com, хосты можно задать REDDIT_JSON_HOSTS) и
    качаем DASH-видео + аудиодорожку v.redd.it, склеивая ffmpeg-ом;
    3) если JSON закрыт — OG-страница зеркал (vxreddit.com, rxddit.com; свои — через
    REDDIT_MIRRORS), там уже лежит прямой mp4.

Всё вернёт info-словарь в формате yt-dlp (formats/height/duration/title/…),
чтобы дальше работали list_qualities() и отправка без изменений.
"""
import asyncio
import contextlib
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp

_UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

_FX_HOSTS = [
    h.strip().rstrip("/")
    for h in os.getenv("TWITTER_FX_API_HOSTS", "https://api.fxtwitter.com,https://api.vxtwitter.com").split(",")
    if h.strip()
]


# ---------------------------------------------------------------- общие утилиты
def is_twitter_url(url: str) -> bool:
    return bool(re.search(r"(?:^|//|\.)(?:twitter|x|fxtwitter|vxtwitter|fixupx)\.com/", url or "", re.I))


def is_reddit_url(url: str) -> bool:
    return bool(re.search(r"(?:^|//|\.)(?:reddit\.com|redd\.it)/", url or "", re.I))


def has_fallback(url: str) -> bool:
    return is_twitter_url(url) or is_reddit_url(url)


def _height_from_url(u: str) -> int:
    """video.twimg.com/.../vid/avc1/0/0/720x1280/x.mp4 -> меньшая сторона не нужна, нужна высота кадра."""
    m = re.search(r"/(\d{3,4})x(\d{3,4})/", u or "")
    return int(m.group(2)) if m else 0


async def download_direct(
    url: str,
    out_dir: Path,
    max_bytes: int = 0,
    headers: Optional[Dict[str, str]] = None,
    suffix: str = ".mp4",
) -> Path:
    """Простая потоковая закачка прямой ссылки на файл."""
    dest = Path(out_dir) / f"fb_{uuid.uuid4().hex[:10]}{suffix}"
    hdrs = {"User-Agent": _UA_DESKTOP, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=120)
    size = 0
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(url, headers=hdrs, allow_redirects=True) as r:
            if r.status >= 400:
                raise RuntimeError(f"HTTP {r.status} при скачивании файла")
            if max_bytes and (r.content_length or 0) > max_bytes:
                raise RuntimeError(f"File too large (> {max_bytes} bytes)")
            try:
                with dest.open("wb") as f:
                    async for chunk in r.content.iter_chunked(1 << 16):
                        size += len(chunk)
                        if max_bytes and size > max_bytes:
                            raise RuntimeError(f"File too large (> {max_bytes} bytes)")
                        f.write(chunk)
            except BaseException:
                dest.unlink(missing_ok=True)
                raise
    if size <= 0:
        dest.unlink(missing_ok=True)
        raise RuntimeError("Пустой файл")
    return dest


def _make_info(*, vid: str, url: str, media_url: str, title: str = "", duration: int = 0,
               width: int = 0, height: int = 0, extra_formats: Optional[List[Dict[str, Any]]] = None,
               source: str, has_audio: bool = True) -> Dict[str, Any]:
    height = int(height or _height_from_url(media_url) or 0)
    formats = [{
        "format_id": f"{source}-direct",
        "url": media_url,
        "ext": "mp4",
        "height": height or None,
        "width": int(width) if width else None,
        "vcodec": "h264",
        "acodec": "aac" if has_audio else "none",
    }]
    for f in extra_formats or []:
        formats.append(f)
    return {
        "id": vid,
        "title": title or "",
        "description": title or "",
        "duration": int(duration or 0),
        "webpage_url": url,
        "ext": "mp4",
        "acodec": "aac" if has_audio else "none",
        "formats": formats,
        "_fallback": source,
        "_direct_url": media_url,
        # чтобы quality_diagnostics не ругался на "урезанное качество yt-dlp"
        "_best_side": 99999,
    }


# ------------------------------------------------------------------- X (Twitter)
_TW_ID_RE = re.compile(r"/status(?:es)?/(\d+)")


def twitter_status_id(url: str) -> Optional[str]:
    m = _TW_ID_RE.search(url or "")
    return m.group(1) if m else None


def _pick_fx_video(js: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Достаёт лучшее видео/гифку из ответа fxtwitter ИЛИ vxtwitter. Возвращает dict(url,width,height,duration)."""
    # fxtwitter: {"tweet": {"media": {"videos": [...], "all": [...]}, "text": ...}}
    tw = js.get("tweet") if isinstance(js.get("tweet"), dict) else None
    if tw:
        media = tw.get("media") or {}
        cands = [m for m in (media.get("videos") or []) if isinstance(m, dict)]
        if not cands:
            cands = [m for m in (media.get("all") or []) if isinstance(m, dict) and m.get("type") in ("video", "gif")]
        for m in cands:
            variants = [v for v in (m.get("variants") or []) if isinstance(v, dict)
                        and "mp4" in str(v.get("content_type") or v.get("type") or "mp4")
                        and v.get("url")]
            if variants:
                variants.sort(key=lambda v: int(v.get("bitrate") or 0), reverse=True)
                url = variants[0]["url"]
            else:
                url = m.get("url")
            if url:
                return {
                    "url": url,
                    "width": m.get("width") or 0,
                    "height": m.get("height") or 0,
                    "duration": m.get("duration") or 0,
                    "title": tw.get("text") or "",
                    "gif": m.get("type") == "gif",
                }
        return None
    # vxtwitter: {"media_extended": [{"type": "video", "url":..., "size": {"width","height"}, "duration_millis"}], "text":...}
    for m in js.get("media_extended") or []:
        if isinstance(m, dict) and m.get("type") in ("video", "gif") and m.get("url"):
            size = m.get("size") or {}
            return {
                "url": m["url"],
                "width": size.get("width") or 0,
                "height": size.get("height") or 0,
                "duration": int((m.get("duration_millis") or 0) / 1000),
                "title": js.get("text") or "",
                "gif": m.get("type") == "gif",
            }
    return None


async def twitter_fx_info(url: str) -> Dict[str, Any]:
    sid = twitter_status_id(url)
    if not sid:
        raise RuntimeError("X: не нашёл id твита в ссылке")
    errors: List[str] = []
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        for host in _FX_HOSTS:
            api = f"{host}/Twitter/status/{sid}" if "vxtwitter" in host else f"{host}/status/{sid}"
            try:
                async with s.get(api, headers={"User-Agent": _UA_DESKTOP, "Accept": "application/json"}) as r:
                    if r.status >= 400:
                        errors.append(f"{host}: HTTP {r.status}")
                        continue
                    js = await r.json(content_type=None)
            except Exception as e:
                errors.append(f"{host}: {type(e).__name__}")
                continue
            if not isinstance(js, dict):
                errors.append(f"{host}: bad json")
                continue
            pick = _pick_fx_video(js)
            if not pick:
                errors.append(f"{host}: нет видео в твите")
                continue
            return _make_info(
                vid=sid, url=url, media_url=pick["url"], title=pick["title"],
                duration=int(pick["duration"] or 0), width=pick["width"], height=pick["height"],
                source="twitter-fx", has_audio=not pick.get("gif"),
            )
    raise RuntimeError("X fallback не сработал: " + "; ".join(errors or ["нет ответа"]))


# ----------------------------------------------------------------------- Reddit
_REDDIT_JSON_HOSTS = [
    h.strip().rstrip("/")
    for h in os.getenv("REDDIT_JSON_HOSTS", "https://www.reddit.com,https://old.reddit.com").split(",")
    if h.strip()
]
_REDDIT_MIRRORS = [
    h.strip().rstrip("/")
    for h in os.getenv("REDDIT_MIRRORS", "https://vxreddit.com,https://rxddit.com").split(",")
    if h.strip()
]
_UA_BOT = "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)"
_REDDIT_ID_RES = (
    re.compile(r"/comments/(\w+)", re.I),
    re.compile(r"(?://|\.)(?:v\.)?redd\.it/(\w+)", re.I),
)
_REDDIT_AUDIO_NAMES = (
    "DASH_AUDIO_128.mp4", "DASH_audio.mp4", "DASH_AUDIO_64.mp4",
    "CMAF_AUDIO_128.mp4", "CMAF_audio.mp4", "CMAF_AUDIO_64.mp4",
)


def _reddit_post_id(url: str) -> Optional[str]:
    for rx in _REDDIT_ID_RES:
        m = rx.search(url or "")
        if m:
            return m.group(1)
    return None


async def _reddit_resolve(session: "aiohttp.ClientSession", url: str) -> str:
    """Короткие ссылки /s/xxxx и redd.it/xxxx -> полный URL поста (редиректы вручную)."""
    if not url.startswith("http"):
        url = "https://" + url
    cur = url
    try:
        for _ in range(6):
            async with session.get(cur, allow_redirects=False,
                                   headers={"User-Agent": _UA_MOBILE, "Accept": "text/html,*/*"}) as r:
                loc = r.headers.get("Location")
                if r.status in (301, 302, 303, 307, 308) and loc:
                    cur = urljoin(cur, loc)
                    if "/comments/" in cur:
                        return cur
                    continue
                break
    except Exception:
        pass
    return cur


def _reddit_post_from_json(js: Any) -> Dict[str, Any]:
    try:
        post = js[0]["data"]["children"][0]["data"]
    except Exception:
        raise RuntimeError("Reddit: неожиданный формат JSON")
    xp = post.get("crosspost_parent_list")
    if isinstance(xp, list) and xp and isinstance(xp[0], dict):
        post = xp[0]
    return post


def _reddit_info_from_post(post: Dict[str, Any], url: str, pid: str) -> Dict[str, Any]:
    media = (post.get("secure_media") or post.get("media") or {}).get("reddit_video") \
        or (post.get("preview") or {}).get("reddit_video_preview")
    if not isinstance(media, dict) or not media.get("fallback_url"):
        dom = str(post.get("domain") or "")
        raise RuntimeError(f"Reddit: в посте нет видео на v.redd.it" + (f" (внешняя ссылка: {dom})" if dom else ""))
    vurl = str(media["fallback_url"])
    is_gif = bool(media.get("is_gif"))
    audio_urls: List[str] = []
    m = re.match(r"(https?://[^/]+/[^/]+/)", vurl)
    if m and not is_gif and media.get("has_audio", True) is not False:
        audio_urls = [m.group(1) + n for n in _REDDIT_AUDIO_NAMES]
    info = _make_info(
        vid=pid, url=url, media_url=vurl, title=str(post.get("title") or ""),
        duration=int(media.get("duration") or 0), width=int(media.get("width") or 0),
        height=int(media.get("height") or 0), source="reddit-json",
        has_audio=bool(audio_urls),
    )
    info["_audio_urls"] = audio_urls
    return info


async def reddit_info(url: str) -> Dict[str, Any]:
    errors: List[str] = []
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        full = url if "/comments/" in url else await _reddit_resolve(s, url)
        pid = _reddit_post_id(full) or _reddit_post_id(url)
        if not pid:
            raise RuntimeError("Reddit: не нашёл id поста в ссылке")

        # 1) JSON поста
        for host in _REDDIT_JSON_HOSTS:
            api = f"{host}/comments/{pid}/.json?raw_json=1"
            try:
                async with s.get(api, headers={"User-Agent": _UA_DESKTOP, "Accept": "application/json"}) as r:
                    if r.status >= 400:
                        errors.append(f"{urlparse(host).hostname}: HTTP {r.status}")
                        continue
                    js = await r.json(content_type=None)
                return _reddit_info_from_post(_reddit_post_from_json(js), url, pid)
            except Exception as e:
                errors.append(f"{urlparse(host).hostname}: {_short_err(e)}")

        # 2) зеркала: OG-страница с прямым mp4
        path = urlparse(full).path or f"/comments/{pid}"
        for host in _REDDIT_MIRRORS:
            try:
                async with s.get(host + path, headers={"User-Agent": _UA_BOT, "Accept": "text/html,*/*"}) as r:
                    if r.status >= 400:
                        errors.append(f"{urlparse(host).hostname}: HTTP {r.status}")
                        continue
                    html = await r.text(errors="ignore")
                mv = re.search(r'<meta[^>]+property=["\']og:video(?::url|:secure_url)?["\'][^>]+content=["\']([^"\']+)', html, re.I) \
                    or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:video', html, re.I)
                if not mv:
                    errors.append(f"{urlparse(host).hostname}: нет og:video")
                    continue
                media_url = mv.group(1).replace("&amp;", "&")
                if media_url.startswith("/"):
                    media_url = host + media_url
                mt = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)', html, re.I)
                mh = re.search(r'og:video:height["\'][^>]+content=["\'](\d+)', html, re.I)
                info = _make_info(vid=pid, url=url, media_url=media_url, title=(mt.group(1) if mt else ""),
                                  height=int(mh.group(1)) if mh else 0, source="reddit-mirror")
                info["_audio_urls"] = []
                return info
            except Exception as e:
                errors.append(f"{urlparse(host).hostname}: {_short_err(e)}")
    raise RuntimeError("Reddit fallback не сработал: " + "; ".join(errors or ["нет ответа"]))


def _short_err(e: BaseException) -> str:
    return (str(e) or type(e).__name__).replace("\n", " ")[:80]

# -------------------------------------------------------------- единая точка входа
async def fallback_info(url: str) -> Dict[str, Any]:
    if is_twitter_url(url):
        return await twitter_fx_info(url)
    if is_reddit_url(url):
        return await reddit_info(url)
    raise RuntimeError("для этой площадки нет запасного способа")


async def fallback_download(info: Dict[str, Any], out_dir: Path, max_bytes: int = 0,
                            ffmpeg: Optional[str] = None) -> Path:
    media_url = info.get("_direct_url")
    if not media_url:
        raise RuntimeError("fallback: нет прямой ссылки")
    headers = {}
    if str(info.get("_fallback", "")).startswith("reddit"):
        headers["Referer"] = "https://www.reddit.com/"
    video = await download_direct(media_url, out_dir, max_bytes=max_bytes, headers=headers)

    # Reddit: видео и звук лежат отдельными файлами — склеиваем (без ffmpeg отдаём видео без звука).
    audio_urls = info.get("_audio_urls") or []
    if audio_urls and ffmpeg:
        for aurl in audio_urls:
            try:
                audio = await download_direct(aurl, out_dir, max_bytes=max_bytes, headers=headers, suffix=".m4a")
            except Exception:
                continue
            try:
                merged = await ffmpeg_merge(ffmpeg, video, audio)
                video.unlink(missing_ok=True)
                return merged
            except Exception:
                break
            finally:
                audio.unlink(missing_ok=True)
    return video


async def ffmpeg_merge(ffmpeg: str, video: Path, audio: Path) -> Path:
    dst = video.with_name(video.stem + "_m.mp4")
    proc = await asyncio.create_subprocess_exec(
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(video), "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0", "-c", "copy", "-movflags", "+faststart", str(dst),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0 or not dst.exists() or dst.stat().st_size <= 0:
        dst.unlink(missing_ok=True)
        raise RuntimeError("ffmpeg не смог склеить видео и звук: " + (err or b"").decode("utf-8", "ignore")[:200])
    return dst


async def ffmpeg_to_mp3(ffmpeg: str, src: Path) -> Path:
    dst = src.with_suffix(".mp3")
    proc = await asyncio.create_subprocess_exec(
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
        "-vn", "-acodec", "libmp3lame", "-b:a", "192k", str(dst),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0 or not dst.exists() or dst.stat().st_size <= 0:
        dst.unlink(missing_ok=True)
        raise RuntimeError("ffmpeg не смог вытащить звук: " + (err or b"").decode("utf-8", "ignore")[:200])
    return dst
