"""
Конфигурация бота: переменные окружения, константы, логгер.
"""
import os
import re
import logging
from pathlib import Path
from datetime import timezone
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

# ================== CONFIG ==================
ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден. Добавь BOT_TOKEN в .env рядом с bot.py")
if not re.match(r"^\d+:[A-Za-z0-9_-]{30,}$", BOT_TOKEN):
    raise RuntimeError("❌ BOT_TOKEN имеет неверный формат. Проверь токен в .env")

# База данных (PostgreSQL на Render)
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
# Render даёт postgres://, asyncpg требует postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

# Путь к JSON для первичной миграции данных (если файл существует — мигрируем)
DATA_FILE = Path("data.json")

API_URL = "https://tikwm.com/api/"
ADMINS = {7233257134}  # <-- твой Telegram ID

# Главный админ, куда в ЛС боту приходят заявки в поддержку (/support) —
# сообщения пользователей пересылаются сюда, обрабатываются ответом
# (Reply) на пересланное сообщение прямо в этом чате.
SUPPORT_ADMIN_ID = next(iter(ADMINS))

ADMIN_LOG_FILE = Path("admin.log")

# ========= ЛОКАЛЬНЫЙ BOT API SERVER (нужен, чтобы слать файлы > 50 МБ) =========
# Обычный облачный Bot API (api.telegram.org) физически не даёт боту
# ОТПРАВЛЯТЬ файлы тяжелее 50 МБ — это ограничение Telegram, не бота, и
# никакими настройками в коде оно не обходится. Чтобы отправлять видео
# весом до 2000 МБ (2 ГБ), нужен свой Local Bot API Server
# (https://github.com/tdlib/telegram-bot-api).
#
# Тут два варианта:
# 1) Просто заполни API_ID и API_HASH (my.telegram.org -> API development
#    tools) — bot.py сам запустит telegram-bot-api рядом с ботом (на этом
#    же устройстве, в т.ч. в Termux) и подключится к нему на 127.0.0.1.
# 2) Если сервер уже поднят где-то отдельно (свой процесс/другая машина) —
#    просто укажи LOCAL_BOT_API_URL напрямую, тогда API_ID/API_HASH не нужны.
#
# Если ничего из этого не задано — работаем как обычно, лимит 49 МБ.
API_ID = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()

# Путь к бинарнику telegram-bot-api (если не в PATH — укажи полный путь,
# например /data/data/com.termux/files/usr/bin/telegram-bot-api).
LOCAL_BOT_API_BIN = os.getenv("LOCAL_BOT_API_BIN", "telegram-bot-api").strip()
LOCAL_BOT_API_PORT = int(os.getenv("LOCAL_BOT_API_PORT", "8081"))
# Куда telegram-bot-api будет сохранять временные файлы (свои, не путать
# с temp-файлами самого бота).
LOCAL_BOT_API_DIR = os.getenv("LOCAL_BOT_API_DIR", "").strip() or str(Path.home() / ".telegram-bot-api")

_explicit_local_url = os.getenv("LOCAL_BOT_API_URL", "").strip().rstrip("/")
if _explicit_local_url:
    # Сервер поднят отдельно (возможно, не локально) — просто ходим туда.
    LOCAL_BOT_API_URL = _explicit_local_url
    LOCAL_BOT_API_IS_LOCAL = os.getenv("LOCAL_BOT_API_IS_LOCAL", "1").strip() == "1"
elif API_ID and API_HASH:
    # API_ID/API_HASH заданы — bot.py сам поднимет сервер на этом устройстве
    # и мы всегда ходим на локальный порт.
    LOCAL_BOT_API_URL = f"http://127.0.0.1:{LOCAL_BOT_API_PORT}"
    LOCAL_BOT_API_IS_LOCAL = True
else:
    LOCAL_BOT_API_URL = ""
    LOCAL_BOT_API_IS_LOCAL = False

# Запасной контакт для уже забаненных пользователей (гейт блокирует им
# доступ ко всем командам бота, включая /support, поэтому у них должен
# остаться способ написать напрямую).
SUPPORT_USERNAME = "@tiksavesbotsupport"
try:
    MSK_TZ = ZoneInfo("Europe/Moscow")
except Exception:
    MSK_TZ = timezone.utc

# Канал для логов (бот должен быть админом канала)
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1003763229922"))

# Технический канал ТОЛЬКО для получения file_id при кэшировании inline-режима
# (см. handlers/inline_handler.py). ОБЯЗАТЕЛЬНО отдельный от LOG_CHANNEL_ID —
# туда не должны попадать все скачанные через инлайн видео/фото, это не
# журнал действий, просто техническое хранилище для повторного использования
# уже скачанного файла без повторного скачивания. Если не задан (0) —
# инлайн-режим просто не кэширует и не будет мгновенно отвечать на повторные
# запросы (каждый раз качает заново).
INLINE_CACHE_CHANNEL_ID = int(os.getenv("INLINE_CACHE_CHANNEL_ID", "0"))

# Любые поддомены (www, m, vm, vt, lite, ...) + новые короткие домены TikTok
# (напр. https://www.tt.site/t/XXXX/). Раньше regex знал только
# tiktok.com / vm. / vt., из-за чего новые форматы ссылок просто игнорировались.
TIKTOK_DOMAINS = r"(?:tiktok\.com|tiktokv\.com|tiktokv\.us|tiktok\.us|tt\.site)"
TIKTOK_RE = re.compile(r"(?<![\w.@/=-])(?:https?://)?(?:[a-z0-9-]+\.)*" + TIKTOK_DOMAINS + r"(?=[/?#]|$|\s)", re.I)
# Короткие/редиректные ссылки: их надо сначала раскрыть в полный URL видео.
TIKTOK_SHORT_RE = re.compile(
    r"^https?://(?:(?:vm|vt|vo|m|lite)\.tiktok\.com/|(?:[a-z0-9-]+\.)?tiktok\.com/t/|(?:[a-z0-9-]+\.)?tt\.site/)",
    re.I,
)

# ========= YOUTUBE =========
YOUTUBE_RE = re.compile(
    r"(https?://)?(www\.|m\.)?(youtube\.com/(watch\?|shorts/|live/)|youtu\.be/)", re.I
)

# ========= ДРУГИЕ ИСТОЧНИКИ (через тот же движок yt-dlp, что и YouTube) =========
# Работают только с ПУБЛИЧНЫМ контентом без логина — это ограничение самих
# площадок (закрытые профили/приватные посты без авторизации не скачать),
# а не бота.
INSTAGRAM_RE = re.compile(r"(https?://)?(www\.)?instagram\.com/(reel|reels|p|tv)/", re.I)
VK_RE = re.compile(r"(https?://)?(www\.|m\.)?(vk\.com|vk\.ru|vkvideo\.ru)/(video|clip)", re.I)
PINTEREST_RE = re.compile(r"(https?://)?(www\.)?(pinterest\.[a-z.]+/pin/|pin\.it/)", re.I)
LIKEE_RE = re.compile(r"(https?://)?([a-z0-9-]+\.)?(likee\.video|likee\.com|like-video\.com)/\S+", re.I)
TWITTER_RE = re.compile(
    r"(https?://)?(www\.|mobile\.|m\.)?(twitter\.com|x\.com|fxtwitter\.com|vxtwitter\.com|fixupx\.com)/(?:i/web/|i/)?(?:[A-Za-z0-9_]+/)?status(?:es)?/\d+",
    re.I,
)
# Одноклассники: ok.ru / m.ok.ru / odnoklassniki.ru; video/ID, videoembed/ID, live/ID, movie/ID,
# а также profile/…/video/ID, group/…/video/ID, старые ссылки dk?st.cmd=movieLayer&st.mvId=ID и web-api/video/moviePlayer/ID.
# Перед yt-dlp ссылка приводится к https://ok.ru/video/ID (см. helpers._norm_ok).
_OK_HOST = r"(?:[a-z0-9-]+\.)?(?:ok\.ru|odnoklassniki\.ru)"
OK_RE = re.compile(
    r"(?<![\w.-])(?:https?://)?" + _OK_HOST + r"/(?:"
    r"(?:[^\s?#]*?/)?(?:video|videoembed|live|movie|movies|clips?)/\d+"
    r"|clips?\?[^\s]*?clip_id=\d+"
    r"|web-api/video/moviePlayer/\d+"
    r"|dk\?[^\s]*?st\.mvId=\d+"
    r")",
    re.I,
)
# Reddit: reddit.com/r/<sub>/comments/<id>/…, reddit.com/r/<sub>/s/<код> (короткая «поделиться»), reddit.com/comments/<id>,
# redd.it/<id>, v.redd.it/<id>; поддомены www./old./np./m./new. — любые.
REDDIT_RE = re.compile(
    r"(?<![\w.-])(?:https?://)?(?:"
    r"(?:[a-z0-9-]+\.)?reddit\.com/(?:(?:r|u|user)/[^\s/?#]+/(?:comments|s)/\w+|comments/\w+)"
    r"|(?:v\.)?redd\.it/\w+"
    r")",
    re.I,
)
# Rutube: video/<32 hex>, video/private/<id>, shorts/<id>, play/embed/<id>, embed/<id>
RUTUBE_RE = re.compile(
    r"(?<![\w.-])(?:https?://)?(?:www\.|m\.)?rutube\.ru/(?:video(?:/private)?|play/embed|embed|shorts)/[0-9a-f]{32}",
    re.I,
)

# История скачиваний для /history: сколько последних записей хранить на человека.
HISTORY_MAX_PER_USER = int(os.getenv("HISTORY_MAX_PER_USER", "300"))

YOUTUBE_MAX_DURATION_SEC = int(os.getenv("YOUTUBE_MAX_DURATION_SEC", str(3 * 3600)))  # 3 часа
# Для вертикальных Shorts yt-dlp репортит "height" как реальную высоту в
# пикселях (у "1080p"-шортса это 1920, а не 1080!) — если тут стоит 720,
# такие шортсы срезаются до огрызка качества. Ставим с запасом, чтобы
# доставало и обычным горизонтальным видео (720/1080p), и вертикальным Shorts.
YOUTUBE_MAX_HEIGHT = int(os.getenv("YOUTUBE_MAX_HEIGHT", "1920"))

# Telegram (обычный облачный Bot API) не даёт боту отправлять файлы больше
# 50 МБ — берём с небольшим запасом снизу.
YOUTUBE_MAX_VIDEO_MB = int(os.getenv("YOUTUBE_MAX_VIDEO_MB", "1990" if LOCAL_BOT_API_URL else "49"))
YOUTUBE_MAX_VIDEO_BYTES = YOUTUBE_MAX_VIDEO_MB * 1024 * 1024

MEDIA_GROUP_LIMIT = 10
PAGE_SIZE = 10
PENDING_TTL_SEC = 300

# ========= ВЫБОР КАЧЕСТВА ВИДЕО (YouTube/Instagram/VK/Pinterest) =========
# Сколько времени у пользователя есть, чтобы нажать на кнопку качества,
# прежде чем предложение "протухнет" и нужно будет прислать ссылку заново.
QUALITY_CHOICE_TTL_SEC = int(os.getenv("QUALITY_CHOICE_TTL_SEC", "600"))

# ========= СКОРОСТЬ СКАЧИВАНИЯ (yt-dlp: YouTube/Instagram/VK/Pinterest) =========
# Параллельные фрагменты для DASH/HLS-потоков — резко ускоряет скачивание
# больших видео (YouTube/VK часто отдают именно такими потоками). Без этого
# yt-dlp тянет фрагменты строго по одному.
YOUTUBE_CONCURRENT_FRAGMENTS = int(os.getenv("YOUTUBE_CONCURRENT_FRAGMENTS", "8"))
# Размер "чанка" при скачивании обычных (progressive) HTTP-ссылок — параллельные
# HTTP Range-запросы вместо одного сплошного потока.
YOUTUBE_HTTP_CHUNK_MB = int(os.getenv("YOUTUBE_HTTP_CHUNK_MB", "10"))

# ========= DONATE =========
DONATIONALERTS_URL = os.getenv("DONATIONALERTS_URL", "").strip() or "https://dalink.to/tiksavesbot"
BOT_SHARE_URL = os.getenv("BOT_SHARE_URL", "").strip() or "https://t.me/tiksavesbot"
STARS_MIN = int(os.getenv("STARS_MIN", "1"))
STARS_MAX = int(os.getenv("STARS_MAX", "1000"))
WAITING_STARS_TTL_SEC = 120

# ========= GLOBAL LIMITS =========
# Сколько скачиваний могут обрабатываться параллельно (а не одно за другим).
# Раньше было = 1 (строгая очередь "один за раз, ~раз в минуту").
GLOBAL_CONCURRENCY = int(os.getenv("GLOBAL_CONCURRENCY", "12"))

# ========= SPAM LIMIT (тихий cooldown, без страйков) =========
# Лимиты сделаны мягкими: обычный человек, кидающий пачку ссылок подряд,
# в них не упирается. Всё переопределяется через переменные окружения.
EVENT_WINDOW_SEC = int(os.getenv("EVENT_WINDOW_SEC", "15"))
EVENT_MAX = int(os.getenv("EVENT_MAX", "30"))
SPAM_COOLDOWN_SEC = int(os.getenv("SPAM_COOLDOWN_SEC", "15"))

# ========= DOWNLOAD LIMIT =========
DL_WINDOW_SEC = int(os.getenv("DL_WINDOW_SEC", "60"))
DL_MAX_ACTIONS = int(os.getenv("DL_MAX_ACTIONS", "25"))

# ========= PHOTO VOLUME LIMIT =========
PHOTO_WINDOW_SEC = int(os.getenv("PHOTO_WINDOW_SEC", "60"))
PHOTO_LIMIT_PER_MIN = int(os.getenv("PHOTO_LIMIT_PER_MIN", "400"))

# ========= AUTOSAVE =========
AUTO_SAVE_INTERVAL_SEC = 5  # автосинхронизация раз в N сек

# ========= DESCRIPTION (CAPTION TEXT) =========
# Если описание видео влезает в это ограничение — шлём сообщением,
# иначе — файлом (.txt), чтобы не обрезать текст.
DESCRIPTION_TG_LIMIT = 3500

# ========= VIDEO/AUDIO FALLBACK DOWNLOAD =========
# Telegram (обычный облачный Bot API) не даёт боту отправлять файлы больше
# 50 МБ — это ограничение платформы, не бота.
MAX_VIDEO_MB = int(os.getenv("MAX_VIDEO_MB", "1990" if LOCAL_BOT_API_URL else "49"))
MAX_VIDEO_BYTES = MAX_VIDEO_MB * 1024 * 1024
# Если облачный Bot API (лимит 50 МБ) и файл тяжелее лимита — вместо отказа
# сжимаем видео через ffmpeg до нужного размера. Скачиваем при этом файлы
# до DOWNLOAD_HARD_CAP_MB (больше — уже отказ, чтобы не забить диск/время).
COMPRESS_OVER_LIMIT = os.getenv("COMPRESS_OVER_LIMIT", "1").strip() == "1"
DOWNLOAD_HARD_CAP_MB = int(os.getenv("DOWNLOAD_HARD_CAP_MB", "600"))
DOWNLOAD_HARD_CAP_BYTES = DOWNLOAD_HARD_CAP_MB * 1024 * 1024

# Куки для yt-dlp (YouTube "Sign in to confirm you're not a bot", Instagram,
# TikTok 18+). Либо путь к cookies.txt (Netscape), либо содержимое файла в
# base64 в переменной YTDLP_COOKIES_B64 (удобно для Render — без файлов).
YTDLP_COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "").strip()
YTDLP_COOKIES_B64 = os.getenv("YTDLP_COOKIES_B64", "").strip()
# Прокси для yt-dlp (http://user:pass@host:port или socks5://...). Бот-проверка YouTube
# завязана на IP: через прокси с "чистым" IP cookies не нужны.
YTDLP_PROXY = os.getenv("YTDLP_PROXY", "").strip()
# Опционально: URL сервера PO-токенов (https://github.com/Brainicism/bgutil-ytdlp-pot-provider),
# например http://127.0.0.1:4416. Нужен плагин bgutil-ytdlp-pot-provider.
YTDLP_POT_URL = os.getenv("YTDLP_POT_URL", "").strip()
# Автообновление yt-dlp (YouTube ломает старые версии каждые несколько недель).
YTDLP_AUTOUPDATE = os.getenv("YTDLP_AUTOUPDATE", "1").strip() == "1"
YTDLP_UPDATE_PRE = os.getenv("YTDLP_UPDATE_PRE", "1").strip() == "1"   # nightly-сборки — фиксы быстрее
YTDLP_UPDATE_EVERY_HOURS = int(os.getenv("YTDLP_UPDATE_EVERY_HOURS", "12"))

MAX_AUDIO_MB = int(os.getenv("MAX_AUDIO_MB", "25"))
MAX_AUDIO_BYTES = MAX_AUDIO_MB * 1024 * 1024

def downgrade_to_cloud_limits() -> None:
    """Local Bot API Server не поднялся — возвращаемся на лимит облачного API (49 МБ),
    в том числе в уже импортированных модулях (они копируют константы при import)."""
    import sys
    global LOCAL_BOT_API_URL, YOUTUBE_MAX_VIDEO_MB, YOUTUBE_MAX_VIDEO_BYTES, MAX_VIDEO_MB, MAX_VIDEO_BYTES
    LOCAL_BOT_API_URL = ""
    YOUTUBE_MAX_VIDEO_MB = MAX_VIDEO_MB = 49
    YOUTUBE_MAX_VIDEO_BYTES = MAX_VIDEO_BYTES = 49 * 1024 * 1024
    for mod in list(sys.modules.values()):
        if mod is None or getattr(mod, "__name__", "") == __name__:
            continue
        for name, val in (("MAX_VIDEO_MB", 49), ("MAX_VIDEO_BYTES", 49 * 1024 * 1024),
                          ("YOUTUBE_MAX_VIDEO_MB", 49), ("YOUTUBE_MAX_VIDEO_BYTES", 49 * 1024 * 1024)):
            if name in getattr(mod, "__dict__", {}):
                setattr(mod, name, val)


# ========= API FALLBACK / HEALTH =========
API_ERROR_WINDOW_SEC = 120
API_ERROR_THRESHOLD = 6

# Небольшая задержка между запросами к бесплатному tikwm API — чтобы не
# словить рейт-лимит/бан на их стороне при частых запросах.
TIKWM_COOLDOWN_SEC = float(os.getenv("TIKWM_COOLDOWN_SEC", "1.2"))

BAN_DURATION_SEC = int(os.getenv("BAN_DURATION_SEC", str(24 * 3600)))  # 24 часа по умолчанию
BAN_REASON_SPAM = "Авто-бан: спам/флуд"

# Подпись с указанием бота
CAPTION_PHOTO = (
    "✨ <b>Готово!</b> 🖼️\n"
    "Забирай — и приятного просмотра 😎\n\n"
    "📥 <i>Скачано в</i> @tiksavesbot"
)
CAPTION_VIDEO = (
    "✨ <b>Готово!</b> 🎬\n"
    "Без водяных знаков, как и должно быть 😉\n\n"
    "📥 <i>Скачано в</i> @tiksavesbot"
)
CAPTION_AUDIO = (
    "🎵 <b>Твой звук готов!</b>\n"
    "Сохраняй и слушай 🎧\n\n"
    "📥 <i>Скачано в</i> @tiksavesbot"
)

ALBUM_PAUSE_MIN = 0.4
ALBUM_PAUSE_MAX = 0.8

BROADCAST_DELAY_SEC = 0.35
BROADCAST_MAX_USERS = 5000

PHOTO_WARNING_TEXT = (
    "⚠️ <b>Прежде чем скачать</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Скачивай только свой контент или тот, на который у тебя есть разрешение автора.\n"
    "Уважай чужой труд 🙏"
)

MSG_SPAM = "🛡 <b>Слишком быстро!</b>\nПереведи дух ~{n} сек. и пробуй снова."
MSG_DL = "⏳ <b>Лимит скачиваний</b>\nПодожди ~{n} сек. — и продолжим."
MSG_PHOTO = "📸 <b>Лимит по фото</b>\nПодожди ~{n} сек. — и продолжим."

# ========= ПОДДЕРЖКА (/support) =========
# Сколько ждём сообщение пользователя после /support, прежде чем считать
# заявку неактуальной.
SUPPORT_WAIT_TTL_SEC = 600

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("tiktok_bot")
