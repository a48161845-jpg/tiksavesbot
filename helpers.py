"""
Вспомогательные функции: HTML-разметка, работа с датами/временем,
парсинг и нормализация TikTok-ссылок.
"""
import re
import time
from typing import Optional, Dict, Any, List

import aiohttp
from datetime import datetime, timezone, timedelta

from config import MSK_TZ, TIKTOK_RE, TIKTOK_SHORT_RE, YOUTUBE_RE, INSTAGRAM_RE, VK_RE, PINTEREST_RE, LIKEE_RE, TWITTER_RE, OK_RE, RUTUBE_RE, ADMINS

# ================== HTML FORMATTING ==================
def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def plain(s: str) -> str:
    """Убирает HTML-теги — для мест, где разметка не поддерживается (алерты callback.answer)."""
    return re.sub(r"<[^>]+>", "", s or "")

_TAG_GLUE_RE = re.compile(r"(?<=\S)(?=[#@])")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_TRAILING_TAGS_RE = re.compile(r"[ \t]+((?:[#@]\S+[ \t]*){2,})$")

def normalize_description(text: Optional[str]) -> Optional[str]:
    """
    Скрейперы/API (tikwm, yt-dlp и т.п.) иногда отдают описание с хэштегами,
    склеенными друг с другом и с текстом без пробелов — "текст#тег1#тег2"
    вместо "текст #тег1 #тег2". Расклеиваем: вставляем пробел перед каждым
    "#"/"@", если перед ним нет пробела, и схлопываем случайные повторные
    пробелы (переносы строк не трогаем).

    Дополнительно: если в конце описания идёт "хвост" из 2+ хэштегов/упоминаний
    подряд (частый паттерн — основной текст, потом блок тегов), отделяем его
    пустой строкой от текста, как обычно и выглядит в самих приложениях.
    """
    if not text:
        return text
    t = _TAG_GLUE_RE.sub(" ", text)
    t = _MULTI_SPACE_RE.sub(" ", t)
    m = _TRAILING_TAGS_RE.search(t)
    if m:
        t = t[: m.start()] + "\n\n" + m.group(1).strip()
    return t.strip()

def code(s: Any) -> str:
    return f"<code>{html_escape(str(s))}</code>"

def bold(s: Any) -> str:
    """Жирный текст: <b>текст</b>"""
    return f"<b>{html_escape(str(s))}</b>"

def italic(s: Any) -> str:
    """Курсив: <i>текст</i>"""
    return f"<i>{html_escape(str(s))}</i>"

def underline(s: Any) -> str:
    """Подчеркивание: <u>текст</u>"""
    return f"<u>{html_escape(str(s))}</u>"

def strikethrough(s: Any) -> str:
    """Зачеркивание: <s>текст</s>"""
    return f"<s>{html_escape(str(s))}</s>"

def link(text: str, url: str) -> str:
    """Ссылка: <a href='url'>текст</a>"""
    return f'<a href="{html_escape(url)}">{html_escape(text)}</a>'

def spoiler(s: Any) -> str:
    """Спойлер (скрытый текст): <tg-spoiler>текст</tg-spoiler>"""
    return f"<tg-spoiler>{html_escape(str(s))}</tg-spoiler>"

def to_html_simple(markup: str) -> str:
    t = html_escape(markup)
    # Подчеркивание: __текст__
    t = re.sub(r"__([^_]+)__", r"<u>\1</u>", t)
    # Жирный текст: **текст**
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    # Курсив: *текст*
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
    # Моноширинный текст (бэкстики): `код`
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    # Ссылки: [текст](url)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    # Зачеркивание: ~~текст~~
    t = re.sub(r"~~([^~]+)~~", r"<s>\1</s>", t)
    return t

# ================== TIME / DATE ==================
def now_msk_str() -> str:
    return datetime.now(tz=MSK_TZ).strftime("%d.%m.%Y %H:%M:%S МСК")

def msk_now() -> datetime:
    return datetime.now(tz=MSK_TZ)

def period_keys(dt: datetime) -> Dict[str, str]:
    day = dt.strftime("%Y-%m-%d")
    month = dt.strftime("%Y-%m")
    year = dt.strftime("%Y")
    iso = dt.isocalendar()
    week = f"{iso.year}-W{iso.week:02d}"
    return {"d": day, "n": week, "m": month, "y": year}

def week_range_str(dt: datetime) -> str:
    iso = dt.isocalendar()
    monday = datetime.fromisocalendar(iso.year, iso.week, 1).replace(tzinfo=MSK_TZ)
    sunday = monday + timedelta(days=6)
    return f"{monday.strftime('%d.%m.%Y')} - {sunday.strftime('%d.%m.%Y')}"

def parse_stats_mode(text: str) -> str:
    t = (text or "").strip().lower()
    if t in {"d", "n", "m", "y", "all"}:
        return t
    return "all"

def parse_date_token(text: str) -> Optional[datetime]:
    s = (text or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=MSK_TZ)
        except ValueError:
            continue
    return None

def iter_day_keys(start_dt: datetime, end_dt: datetime) -> List[str]:
    start = start_dt.date()
    end = end_dt.date()
    if end < start:
        start, end = end, start
    out: List[str] = []
    cur = start
    while cur <= end:
        out.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return out

def format_msk(ts_unix: int) -> str:
    dt = datetime.fromtimestamp(ts_unix, tz=timezone.utc).astimezone(MSK_TZ)
    return dt.strftime("%d.%m.%Y %H:%M")

def ms_since(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)

# ================== MISC / DOMAIN HELPERS ==================
def clamp_reason(e: Exception, limit: int = 220) -> str:
    s = str(e).strip() or e.__class__.__name__
    s = s.replace("\n", " ").replace("\r", " ")
    if len(s) > limit:
        s = s[:limit - 3] + "..."
    return s

def exc_type_name(e: Exception) -> str:
    """Имя класса исключения — для подробных логов ошибок."""
    return e.__class__.__name__

def is_admin(uid: int) -> bool:
    from storage import store
    return uid in ADMINS or uid in store.data.get("admins_extra", [])

def is_tiktok(text: str) -> bool:
    return bool(TIKTOK_RE.search(text or ""))

def extract_tiktok_url(text: str) -> Optional[str]:
    if not text:
        return None
    # Берём первую TikTok-ссылку из текста, даже если перед ней есть другие ссылки.
    for m in re.finditer(r"https?://\S+", text):
        url = m.group(0)
        if is_tiktok(url):
            return url
    # maybe without scheme
    m2 = TIKTOK_RE.search(text)
    if m2:
        url = text[m2.start():].split()[0]
        if not url.startswith("http"):
            url = "https://" + url
        return url
    return None

def normalize_tiktok_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    if u[0] in "<([" and u[-1] in ">)]":
        u = u[1:-1].strip()
    while u and u[-1] in ".,;!?)\"]}":
        u = u[:-1]
    if not u.startswith("http"):
        u = "https://" + u
    if TIKTOK_RE.search(u):
        # трекинговые параметры (?_r=1&u_code=...) tikwm/yt-dlp только мешают
        u = u.split("?", 1)[0].split("#", 1)[0]
    return u

_TT_VIDEO_ID_RE = re.compile(r"/(?:video|photo|v)/(\d{8,})")

def extract_tiktok_video_id(url: str) -> Optional[str]:
    m = _TT_VIDEO_ID_RE.search(url or "")
    return m.group(1) if m else None

def is_tiktok_short_url(url: str) -> bool:
    return bool(TIKTOK_SHORT_RE.match(url or ""))

def is_youtube(text: str) -> bool:
    return bool(YOUTUBE_RE.search(text or ""))

def extract_youtube_url(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"https?://\S+", text)
    if m:
        url = m.group(0)
        return url if is_youtube(url) else None
    # maybe without scheme
    m2 = YOUTUBE_RE.search(text)
    if m2:
        url = text[m2.start():].split()[0]
        if not url.startswith("http"):
            url = "https://" + url
        return url
    return None

def normalize_youtube_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    if u[0] in "<([" and u[-1] in ">)]":
        u = u[1:-1].strip()
    while u and u[-1] in ".,;!?)\"]}":
        u = u[:-1]
    if not u.startswith("http"):
        u = "https://" + u
    # В отличие от TikTok, у YouTube query-параметры значимы (?v=ID) —
    # обрезать их нельзя, поэтому просто возвращаем как есть после очистки.
    return u

def is_instagram(text: str) -> bool:
    return bool(INSTAGRAM_RE.search(text or ""))

def is_vk(text: str) -> bool:
    return bool(VK_RE.search(text or ""))

def is_pinterest(text: str) -> bool:
    return bool(PINTEREST_RE.search(text or ""))

def is_likee(text: str) -> bool:
    return bool(LIKEE_RE.search(text or ""))

def is_twitter(text: str) -> bool:
    return bool(TWITTER_RE.search(text or ""))

def is_ok(text: str) -> bool:
    return bool(OK_RE.search(text or ""))

def is_rutube(text: str) -> bool:
    return bool(RUTUBE_RE.search(text or ""))

# (platform, regex) — порядок важен только для читаемости, паттерны не пересекаются.
_OTHER_PLATFORMS = (
    ("instagram", INSTAGRAM_RE),
    ("vk", VK_RE),
    ("pinterest", PINTEREST_RE),
    ("likee", LIKEE_RE),
    ("twitter", TWITTER_RE),
    ("ok", OK_RE),
    ("rutube", RUTUBE_RE),
)

def detect_other_platform(text: str) -> Optional[str]:
    """Платформа из набора «через yt-dlp» (кроме YouTube) или None."""
    for name, rx in _OTHER_PLATFORMS:
        if rx.search(text or ""):
            return name
    return None

def is_other_source(text: str) -> bool:
    """Instagram / VK / Pinterest / Likee / X / OK / Rutube — всё, что идёт через тот же движок, что и YouTube."""
    return detect_other_platform(text) is not None

_TW_MIRRORS_RE = re.compile(r"://(?:www\.|mobile\.|m\.)?(?:fxtwitter|vxtwitter|fixupx)\.com/", re.I)

_OK_ID_RES = (
    re.compile(r"/(?:video|videoembed|live|movie|movies)/(\d+)", re.I),
    re.compile(r"/moviePlayer/(\d+)", re.I),
    re.compile(r"[?&]st\.mvId=(\d+)", re.I),
)
_RUTUBE_ID_RE = re.compile(r"rutube\.ru/(video/private|video|play/embed|embed|shorts)/([0-9a-f]{32})", re.I)

def _norm_ok(url: str) -> str:
    """Любую ссылку OK на видео -> https://ok.ru/video/ID (так её понимает yt-dlp)."""
    for rx in _OK_ID_RES:
        m = rx.search(url)
        if m:
            kind = "live" if re.search(r"/live/\d+", url, re.I) else "video"
            return f"https://ok.ru/{kind}/{m.group(1)}"
    return url

def _norm_rutube(url: str) -> str:
    """shorts/embed -> обычная страница видео; private сохраняем вместе с ключом ?p=…"""
    m = _RUTUBE_ID_RE.search(url)
    if not m:
        return url
    kind, vid = m.group(1).lower(), m.group(2).lower()
    if kind == "video/private":
        q = re.search(r"[?&]p=([\w-]+)", url)
        return f"https://rutube.ru/video/private/{vid}/" + (f"?p={q.group(1)}" if q else "")
    return f"https://rutube.ru/video/{vid}/"

def _fix_other_url(url: str) -> str:
    # зеркала X (fxtwitter и т.п.) yt-dlp не знает — возвращаем настоящий домен
    url = _TW_MIRRORS_RE.sub("://twitter.com/", url)
    if OK_RE.search(url):
        return _norm_ok(url)
    if RUTUBE_RE.search(url):
        return _norm_rutube(url)
    return url

def extract_other_source_url(text: str) -> Optional[str]:
    u = _extract_other_source_url_raw(text)
    return _fix_other_url(u) if u else u

def _extract_other_source_url_raw(text: str) -> Optional[str]:
    if not text:
        return None
    for m in re.finditer(r"https?://\S+", text):
        url = m.group(0).rstrip(").,;]>\"'")
        if is_other_source(url):
            return url
    for _name, rx in _OTHER_PLATFORMS:
        m2 = rx.search(text)
        if m2:
            url = text[m2.start():].split()[0]
            if not url.startswith("http"):
                url = "https://" + url
            return url
    return None

async def resolve_tiktok_redirect(session: aiohttp.ClientSession, url: str) -> str:
    """Раскрывает короткую ссылку (vt./vm./tiktok.com/t/ /tt.site/t/) в полный URL видео."""
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
                      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Accept": "*/*",
    }
    try:
        async with session.get(url, headers=headers, allow_redirects=True,
                               timeout=aiohttp.ClientTimeout(total=12)) as resp:
            final = str(resp.url)
            if extract_tiktok_video_id(final):
                return final
            # некоторые короткие домены отдают HTML с canonical / og:url вместо 30x
            try:
                body = (await resp.content.read(200_000)).decode("utf-8", "ignore")
            except Exception:
                body = ""
            m = re.search(r"https?://(?:www\.)?tiktok\.com/@[^\"'\s<>?]+/(?:video|photo)/\d+", body)
            if m:
                return m.group(0)
            return final
    except Exception:
        return url

def is_download_message(text: str) -> bool:
    return is_tiktok(text)

def is_chatty_message(text: str) -> bool:
    if not text:
        return False
    if text.startswith("/"):
        return False
    if is_tiktok(text):
        return False
    return True

# ================== DURATION PARSING (для /ban) ==================
_DUR_RE = re.compile(r"(?i)(\d+)\s*([dhm])")

def parse_duration(s: str) -> int:
    if not s:
        raise ValueError("empty duration")
    total = 0
    for num, unit in _DUR_RE.findall(s.replace(" ", "")):
        n = int(num)
        u = unit.lower()
        if u == "d":
            total += n * 86400
        elif u == "h":
            total += n * 3600
        elif u == "m":
            total += n * 60
    if total <= 0:
        raise ValueError("bad duration")
    return total


def _empty_period_bucket() -> dict:
    return {
        "users_new": 0,
        "downloads": {"video_ops": 0, "photo_ops": 0, "video_sent": 0, "photos_sent": 0, "audio_sent": 0},
        "errors": {"total": 0, "by_stage": {}, "by_type": {}},
        "bans_total": 0,
        "stars_total": 0,
    }


async def resolve_generic_redirect(url: str, timeout: float = 10.0) -> str:
    """Раскрывает короткую ссылку (например l.likee.video/v/...) — возвращает финальный URL или исходный."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"},
            ) as resp:
                return str(resp.url) or url
    except Exception:
        return url
