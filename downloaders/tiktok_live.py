"""
TikTok: live-фото и запасной разбор страницы.

Live-фото — кадр поста, у которого есть короткий «живой» клип. Разные источники (tikwm, JSON страницы TikTok)
кладут ссылку на клип под разными ключами, поэтому ищем её не по одному полю, а рекурсивно внутри описания кадра:
берём URL, который выглядит как видео (mp4 / video/tos / mime_type=video) или лежит под «живым» ключом.

Всё здесь — чистые функции без сети (их проверяют tests/test_tiktok_live.py).
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

_LIVE_KEY_HINTS = ("live", "motion", "dynamic", "animated", "video", "mp4", "clip")
_LIVE_KEYS_EXACT = {"play", "play_url", "playurl", "play_addr", "playaddr", "url_mp4"}
_NOT_LIVE_KEY_PARTS = ("cover", "thumb", "avatar", "music", "watermark")
_IMG_EXT_RE = re.compile(r"(?:\.(?:jpe?g|webp|heic|png|avif|gif|image)(?:[?#~]|$)|tplv-[\w-]*image)", re.I)
_VIDEO_HINT_RE = re.compile(r"(?:\.mp4(?:[?#]|$)|mime_type=video|/video/tos/|video_mp4|\.mov(?:[?#]|$))", re.I)


def _urls_in(obj: Any, path: str = "", depth: int = 0) -> List[Tuple[str, str]]:
    """Все http-строки внутри obj вместе с путём ключей («livePhoto.url_list»): [(path, url)]."""
    out: List[Tuple[str, str]] = []
    if depth > 5 or obj is None:
        return out
    if isinstance(obj, str):
        if obj.startswith("http"):
            out.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(_urls_in(v, f"{path}.{k}" if path else str(k), depth + 1))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_urls_in(v, path, depth + 1))
    return out


def find_live_url(item: Any, photo_url: str = "") -> Optional[str]:
    """Ссылка на live-клип внутри описания одного кадра (или None, если кадр — обычное фото)."""
    best: Optional[str] = None
    for path, url in _urls_in(item):
        if url == photo_url or _IMG_EXT_RE.search(url):
            continue
        if _VIDEO_HINT_RE.search(url):
            return url  # явно видео
        p = path.lower()
        if any(b in p for b in _NOT_LIVE_KEY_PARTS):
            continue
        last = p.rsplit(".", 1)[-1]
        if best is None and (last in _LIVE_KEYS_EXACT or any(h in p for h in _LIVE_KEY_HINTS)):
            best = url
    return best


def _first_url(v: Any) -> str:
    if isinstance(v, str):
        return v if v.startswith("http") else ""
    if isinstance(v, dict):
        for k in ("urlList", "url_list", "UrlList"):
            ul = v.get(k)
            if isinstance(ul, list) and ul:
                return _first_url(ul[0])
        for k in ("url", "image", "imageURL", "image_url", "display_image", "displayImage", "owner_watermark_image"):
            if k in v:
                u = _first_url(v[k])
                if u:
                    return u
    if isinstance(v, list) and v:
        return _first_url(v[0])
    return ""


def photos_and_live(images: List[Any]) -> Tuple[List[str], Dict[str, str]]:
    """images — список кадров (строки или dict'ы) из любого источника -> (фото, {фото_url: live_url})."""
    photos: List[str] = []
    live: Dict[str, str] = {}
    for it in images or []:
        pu = _first_url(it) if not isinstance(it, str) else (it if it.startswith("http") else "")
        if not pu:
            continue
        photos.append(pu)
        if isinstance(it, dict):
            lu = find_live_url(it, pu)
            if lu:
                live[pu] = lu
    return photos, live


# ---------------------------------------------------------------- страница TikTok
_REHYDRATION_RE = re.compile(
    r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', re.S | re.I)
_SIGI_RE = re.compile(r'<script[^>]+id="SIGI_STATE"[^>]*>(.*?)</script>', re.S | re.I)


def _find_item_struct(obj: Any, depth: int = 0) -> Optional[Dict[str, Any]]:
    if depth > 6 or obj is None:
        return None
    if isinstance(obj, dict):
        if isinstance(obj.get("itemStruct"), dict):
            return obj["itemStruct"]
        if isinstance(obj.get("imagePost"), dict) or (isinstance(obj.get("video"), dict) and "desc" in obj):
            return obj
        for v in obj.values():
            r = _find_item_struct(v, depth + 1)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_item_struct(v, depth + 1)
            if r:
                return r
    return None


def parse_page_html(html: str) -> Dict[str, Any]:
    """
    HTML страницы поста -> {"video", "photos", "live", "music", "description"}.
    Бросает RuntimeError, если на странице нет данных поста (нужен логин / IP заблокирован / удалено).
    """
    raw = None
    for rx in (_REHYDRATION_RE, _SIGI_RE):
        m = rx.search(html or "")
        if m:
            raw = m.group(1)
            break
    if not raw:
        raise RuntimeError("TikTok: на странице нет данных поста")
    try:
        data = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"TikTok: не разобрал JSON страницы ({type(e).__name__})")
    item = _find_item_struct(data)
    if not item:
        scope = data.get("__DEFAULT_SCOPE__") if isinstance(data, dict) else None
        status = ""
        if isinstance(scope, dict):
            vd = scope.get("webapp.video-detail") or {}
            status = str(vd.get("statusMsg") or vd.get("statusCode") or "")
        raise RuntimeError("TikTok: пост недоступен" + (f" ({status})" if status else ""))

    photos: List[str] = []
    live: Dict[str, str] = {}
    ip = item.get("imagePost")
    if isinstance(ip, dict):
        photos, live = photos_and_live(ip.get("images") or [])

    video = None
    v = item.get("video")
    if isinstance(v, dict) and not photos:
        video = v.get("playAddr") or v.get("downloadAddr") or ""
        if not video:
            for br in v.get("bitrateInfo") or []:
                ul = ((br.get("PlayAddr") or {}).get("UrlList")) or []
                if ul:
                    video = ul[0]
                    break

    music = None
    mu = item.get("music")
    if isinstance(mu, dict):
        music = mu.get("playUrl") or None

    from downloaders.song_search import song_from_page
    return {
        "song": song_from_page(mu),
        "video": video or None,
        "photos": photos,
        "live": live,
        "music": music if isinstance(music, str) and music.startswith("http") else None,
        "description": (item.get("desc") or "").strip() or None,
    }


# ---------------------------------------------------------------- короткие ссылки (oEmbed)
def url_from_oembed(js: Any) -> Optional[str]:
    """Ответ https://www.tiktok.com/oembed?url=<короткая ссылка> -> полный URL поста."""
    if not isinstance(js, dict):
        return None
    vid = str(js.get("embed_product_id") or "")
    if not vid:
        m = re.search(r"/(?:video|photo)/(\d{8,})", str(js.get("html") or "") + " " + str(js.get("author_url") or ""))
        vid = m.group(1) if m else ""
    if not re.fullmatch(r"\d{8,}", vid):
        return None
    user = str(js.get("author_unique_id") or "").strip().lstrip("@")
    if not user:
        m = re.search(r"tiktok\.com/@([^/?\"'\s]+)", str(js.get("author_url") or ""))
        user = m.group(1) if m else ""
    return f"https://www.tiktok.com/@{user}/video/{vid}" if user else f"https://www.tiktok.com/@/video/{vid}"


def live_note(photos: List[str], live: Optional[Dict[str, str]]) -> List[int]:
    """Номера (с 1) кадров, у которых есть live-клип."""
    live = live or {}
    return [i + 1 for i, p in enumerate(photos) if live.get(p)]
