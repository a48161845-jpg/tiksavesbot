"""
Понятные объяснения ошибок скачивания.

Одна точка правды: по тексту причины (yt-dlp / API / наши RuntimeError) определяем
код ошибки и отдаём
  * user_text — что показать ПОЛЬЗОВАТЕЛЮ (коротко, без техники, с советом что делать);
  * admin_text — что написать АДМИНУ в лог-канал под строкой «Причина» (что это значит
    и можно ли это чинить на стороне бота).

Пользовательские тексты переведены на en/uk (остальные языки показывают русский оригинал,
см. i18n.py). Новую ошибку добавляем так: правило в _RULES + запись в _TEXTS.
"""
import html
import re
from typing import Dict, Optional, Tuple

from i18n import _reg

# code -> (user_ru, user_en, user_uk, admin_ru)
_TEXTS: Dict[str, Tuple[str, str, str, str]] = {
    "too_large": (
        "❌ Файл слишком тяжёлый — бот не может его скачать и отправить. Попробуй выбрать качество пониже или более короткое видео.",
        "❌ The file is too heavy for the bot to download and send. Try a lower quality or a shorter video.",
        "❌ Файл занадто важкий — бот не може його завантажити й надіслати. Спробуй нижчу якість або коротше відео.",
        "Файл больше лимита скачивания (DOWNLOAD_HARD_CAP_MB) или отправки. Не баг: видео просто очень тяжёлое.",
    ),
    "pin_no_video": (
        "❌ Pinterest не отдал видео из этого пина. Чаще всего так бывает, когда пин ограничен (18+ / нужен вход в аккаунт) "
        "или в нём на самом деле картинка. Открой пин в приложении, нажми «Поделиться» → «Копировать ссылку» и пришли её ещё раз.",
        "❌ Pinterest didn't give out the video from this pin. This usually happens when the pin is restricted (18+ / login required) "
        "or it's actually just an image. Open the pin in the app, tap Share → Copy link and send it again.",
        "❌ Pinterest не віддав відео з цього піна. Зазвичай так буває, коли пін обмежений (18+ / потрібен вхід) "
        "або це насправді картинка. Відкрий пін у застосунку, натисни «Поділитися» → «Копіювати посилання» і надішли ще раз.",
        "Pinterest: yt-dlp не нашёл форматов, а запасной способ (API/страница/виджет/crawler) тоже ничего не вернул. "
        "Это 18+/закрытый пин, пин-картинка, либо Pinterest режет IP сервера (api: HTTP 403). Лечится cookies залогиненного "
        "аккаунта Pinterest (YTDLP_COOKIES_FILE) или прокси (YTDLP_PROXY).",
    ),
    "pin_blocked": (
        "❌ Pinterest сейчас не пускает бота к этому пину. Попробуй ещё раз чуть позже.",
        "❌ Pinterest isn't letting the bot reach this pin right now. Try again a bit later.",
        "❌ Pinterest зараз не пускає бота до цього піна. Спробуй ще раз трохи згодом.",
        "Pinterest отвечает 403/429 на запросы с IP сервера (антибот). Нужны cookies Pinterest или прокси.",
    ),
    "ip_blocked": (
        "❌ Платформа временно блокирует бота при доступе к этому видео. Попробуй ещё раз позже — это не из-за твоей ссылки.",
        "❌ The platform is temporarily blocking the bot from this video. Try again later — it's not your link's fault.",
        "❌ Платформа тимчасово блокує бота при доступі до цього відео. Спробуй пізніше — річ не в твоєму посиланні.",
        "Платформа заблокировала IP сервера для этого поста (TikTok «Your IP address is blocked»). Лечится прокси "
        "(YTDLP_PROXY) или сменой IP/хоста; на ссылку пользователя это не влияет.",
    ),
    "suspended": (
        "❌ Аккаунт автора заблокирован (suspended) — видео больше недоступно, скачать его нельзя.",
        "❌ The author's account is suspended — the video is no longer available and can't be downloaded.",
        "❌ Акаунт автора заблоковано (suspended) — відео вже недоступне, завантажити його не можна.",
        "X/Twitter: аккаунт автора заблокирован, запасные зеркала (fxtwitter/vxtwitter) тоже ничего не знают. Чинить нечего.",
    ),
    "restricted": (
        "❌ Этот пост ограничен автором: его видят только определённые люди или нужен вход в аккаунт. Бот такие посты скачать не может.",
        "❌ The author restricted this post: only certain people can see it or login is required. The bot can't download such posts.",
        "❌ Цей пост обмежений автором: його бачать лише певні люди або потрібен вхід в акаунт. Бот такі пости завантажити не може.",
        "Instagram/и т.п.: «content isn't available to everyone» — закрытый аккаунт, возрастное/аудиторное ограничение или нужен "
        "логин. Иногда помогают свежие cookies (YTDLP_COOKIES_FILE), но для закрытых аккаунтов — нет.",
    ),
    "age": (
        "❌ Видео с возрастным ограничением (18+) — для него нужен вход в аккаунт, бот его скачать не может.",
        "❌ This video is age-restricted (18+) — it needs a logged-in account, so the bot can't download it.",
        "❌ Відео з віковим обмеженням (18+) — потрібен вхід в акаунт, бот його завантажити не може.",
        "Возрастное ограничение: нужен залогиненный аккаунт (cookies).",
    ),
    "url_parse": (
        "❌ Не удалось разобрать ссылку. Скопируй её заново через «Поделиться» → «Копировать ссылку» и пришли ещё раз.",
        "❌ Couldn't parse the link. Copy it again via Share → Copy link and resend.",
        "❌ Не вдалося розібрати посилання. Скопіюй його знову через «Поділитися» → «Копіювати посилання» і надішли ще раз.",
        "API не смог разобрать URL (часто у ссылки пустой ник: /@/video/ID). Бот пробует взять ник из полной ссылки; если "
        "повторяется — ссылка битая.",
    ),
    "private": (
        "❌ Видео приватное или недоступно.",
        "❌ The video is private or unavailable.",
        "❌ Відео приватне або недоступне.",
        "Пост приватный/скрыт — скачать нельзя.",
    ),
    "deleted": (
        "❌ Видео удалено или не найдено.",
        "❌ The video was deleted or not found.",
        "❌ Відео видалено або не знайдено.",
        "Пост удалён автором или ссылка неверная.",
    ),
    "geo": (
        "❌ Это видео недоступно в регионе, где находится бот. Скачать его не получится.",
        "❌ This video isn't available in the bot's region, so it can't be downloaded.",
        "❌ Це відео недоступне в регіоні, де розташований бот. Завантажити не вийде.",
        "Геоблок: видео закрыто для региона сервера. Помогает прокси из нужной страны (YTDLP_PROXY).",
    ),
    "rate_limit": (
        "❌ Платформа просит подождать — слишком много запросов. Попробуй через пару минут.",
        "❌ The platform asks to wait — too many requests. Try again in a couple of minutes.",
        "❌ Платформа просить зачекати — забагато запитів. Спробуй за кілька хвилин.",
        "429/Too Many Requests: временное ограничение частоты запросов с IP сервера.",
    ),
    "unsupported": (
        "❌ Эта ссылка не поддерживается. Пришли ссылку на видео из TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube или Reddit.",
        "❌ This link isn't supported. Send a video link from TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube or Reddit.",
        "❌ Це посилання не підтримується. Надішли посилання на відео з TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube або Reddit.",
        "yt-dlp: Unsupported URL — ссылка ведёт не на видео (профиль, главная и т.п.) или сайт не поддерживается.",
    ),
    "network": (
        "❌ Проблема с сетью/сервисом. Попробуй позже.",
        "❌ Network/service problem. Try again later.",
        "❌ Проблема з мережею/сервісом. Спробуй пізніше.",
        "Сетевая ошибка/таймаут при обращении к платформе или провайдеру. Обычно разовая.",
    ),
    "outdated": (
        "❌ Не удалось скачать: источник изменил защиту. Я уже в курсе — попробуй ещё раз немного позже.",
        "❌ Couldn't download: the source changed its protection. I'm on it — try again a bit later.",
        "❌ Не вдалося завантажити: джерело змінило захист. Я вже в курсі — спробуй ще раз трохи згодом.",
        "yt-dlp просит обновиться/сообщить о баге (extractor сломан). Обнови: pip install -U yt-dlp --break-system-packages "
        "(автообновление раз в 12 ч включено).",
    ),
    "unknown": (
        "❌ Не удалось скачать. Попробуй позже или пришли другую ссылку.",
        "❌ Couldn't download. Try again later or send another link.",
        "❌ Не вдалося завантажити. Спробуй пізніше або надішли інше посилання.",
        "Неклассифицированная ошибка — смотри текст причины выше.",
    ),
}

for _ru, _en, _uk, _ in _TEXTS.values():
    _reg(_ru, _en, _uk)

# (код, подстроки в нижнем регистре); порядок важен — первая совпавшая выигрывает.
_RULES = (
    ("too_large", ("file too large", "слишком тяжёл", "request entity too large")),
    ("suspended", ("suspended",)),
    ("ip_blocked", ("ip address is blocked", "your ip", "ip is blocked")),
    ("url_parse", ("url parsing", "parsing is failed")),
    ("age", ("age-restricted", "age restricted", "confirm your age", "18+ ", "inappropriate for some users")),
    ("restricted", ("isn't available to everyone", "isn’t available to everyone", "certain audiences",
                    "login required", "нет видеоформатов", "log in", "sign in", "requires login", "need to log in", "cookies")),
    ("geo", ("not available in your country", "geo restrict", "geo-restrict", "not made this video available in your country",
             "blocked it in your country")),
    ("private", ("private", "приват", "недоступ", "unavailable")),
    ("deleted", ("deleted", "удален", "удалён", "removed", "not found", "does not exist", "no longer available")),
    ("rate_limit", ("http 429", "too many requests", "rate limit", "rate-limit")),
    ("unsupported", ("unsupported url",)),
    ("outdated", ("please report this issue", "confirm you are on the latest version", "unable to extract")),
    ("network", ("timeout", "timed out", "connection reset", "cannot connect", "network", "ssl", "clientconnector",
                 "server disconnected", "temporary failure")),
)


def classify(reason: object, platform: Optional[str] = None, url: str = "") -> str:
    low = str(reason or "").lower()
    plat = (platform or "").lower()
    is_pin = plat == "pinterest" or "pinterest" in low or "pin.it/" in (url or "").lower() or "pinterest." in (url or "").lower()

    if is_pin:
        if "file too large" in low:
            return "too_large"
        if any(x in low for x in ("нет видео", "no video formats", "нет видеоформатов", "не нашёл id пина", "возможно, это картинка")):
            # 403 от API и пустая страница — это блок антибота, а не «просто картинка»
            return "pin_blocked" if ("http 403" in low and "http 429" in low) else "pin_no_video"
        if "http 403" in low or "http 429" in low:
            return "pin_blocked"

    for code, needles in _RULES:
        if any(n in low for n in needles):
            return code
    return "unknown"


def explain_user(reason: object, platform: Optional[str] = None, url: str = "") -> str:
    """Русский текст для пользователя (оборачивать в tr(..., text))."""
    return _TEXTS[classify(reason, platform, url)][0]


def explain_admin(reason: object, platform: Optional[str] = None, url: str = "") -> str:
    code = classify(reason, platform, url)
    return f"[{code}] {_TEXTS[code][3]}"


_TAG_RE = re.compile(r"<[^>]+>")


def explain_log_line(lines) -> Optional[str]:
    """По строкам dlerr-лога собирает строку «💡 Что это значит: …» (или None)."""
    reason = plat = url = ""
    for ln in lines:
        s = str(ln)
        if s.startswith("🧨 Причина:"):
            reason = html.unescape(_TAG_RE.sub("", s.split(":", 1)[1])).strip()
        elif s.startswith("🔗 Ссылка:"):
            url = html.unescape(_TAG_RE.sub("", s.split(":", 1)[1])).strip()
        elif s.startswith("❌ Категория:") or s.startswith("⚠️ Категория:"):
            m = re.search(r"\(([a-z0-9_]+)\)", html.unescape(_TAG_RE.sub("", s)))
            if m:
                plat = m.group(1)
    if not reason:
        return None
    return "💡 Что это значит: " + html.escape(explain_admin(reason, plat, url))
