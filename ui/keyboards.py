"""
Инлайн-клавиатуры и текстовые константы, которые показываются пользователю.
Здесь нет бизнес-логики — только разметка интерфейса.
"""
import urllib.parse
from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from core.config import DONATIONALERTS_URL, OZON_DONATE_URL, PREMIUM_PLANS, BOT_SHARE_URL, STARS_MIN, STARS_MAX, MAX_VIDEO_MB
from core.helpers import html_escape, code
from i18n import tr
from ui.screens_text import build as _build_screens

# ================== ЭКРАНЫ (тексты) ==================
# Тексты собирает ui/screens_text.build() (единый стиль — ui/theme.py); переводы — i18n/screens.py.
_RU = _build_screens("ru")
START_TEXT = _RU["start"]
HELP_TEXT = _RU["help"]
DONATE_TEXT = _RU["donate"]
STARS_MENU_TEXT = _RU["stars"]
RUB_DONATE_TEXT = _RU["rub"]
SUPPORT_TEXT = _RU["support"]
SUPPORT_SENT_TEXT = _RU["sent"]
SUPPORT_TIMEOUT_TEXT = _RU["timeout"]
PHOTO_CHOICE_TEXT = _RU["photo_choice"]
QUALITY_CHOICE_TEXT = _RU["quality"]
PREMIUM_TEXT = _RU["premium"]
PREMIUM_OK_TEXT = _RU["premium_ok"]
HELP_SECTIONS = {k: _RU[f"help_{k}"] for k in ("video", "photo", "groups", "limits", "inline")}


def help_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=tr(lang, "🎬 Видео"), callback_data="help:video"),
                InlineKeyboardButton(text=tr(lang, "🖼 Фото"), callback_data="help:photo"),
            ],
            [
                InlineKeyboardButton(text=tr(lang, "👥 Группы"), callback_data="help:groups"),
                InlineKeyboardButton(text=tr(lang, "📳 Inline"), callback_data="help:inline"),
            ],
            [
                InlineKeyboardButton(text=tr(lang, "⏱ Лимиты"), callback_data="help:limits"),
                InlineKeyboardButton(text=tr(lang, "❌ Закрыть"), callback_data="help:close"),
            ],
        ]
    )


def help_section_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=tr(lang, "⬅️ Назад"), callback_data="help:back"),
                InlineKeyboardButton(text=tr(lang, "❌ Закрыть"), callback_data="help:close"),
            ]
        ]
    )


# ================== STATS / TOP KEYBOARDS ==================
def stats_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 День", callback_data="ad:stats:d"),
                InlineKeyboardButton(text="🗓 Неделя", callback_data="ad:stats:n"),
                InlineKeyboardButton(text="🗓 Месяц", callback_data="ad:stats:m"),
            ],
            [
                InlineKeyboardButton(text="📆 Год", callback_data="ad:stats:y"),
                InlineKeyboardButton(text="📊 Всё время", callback_data="ad:stats:all"),
            ],
            [
                InlineKeyboardButton(text="🏆 Топ", callback_data="ad:top"),
                InlineKeyboardButton(text="💥 Ошибки", callback_data="ad:errors"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="ad:back"),
                InlineKeyboardButton(text="❌ Закрыть", callback_data="ad:close"),
            ],
        ]
    )

def top_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 День", callback_data="ad:top:d"),
                InlineKeyboardButton(text="🗓 Неделя", callback_data="ad:top:n"),
                InlineKeyboardButton(text="🗓 Месяц", callback_data="ad:top:m"),
            ],
            [
                InlineKeyboardButton(text="📆 Год", callback_data="ad:top:y"),
                InlineKeyboardButton(text="📊 Всё время", callback_data="ad:top:all"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="ad:back"),
                InlineKeyboardButton(text="❌ Закрыть", callback_data="ad:close"),
            ],
        ]
    )

# ================== START ==================

# ================== DONATE ==================
def donate_main_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tr(lang, "⭐ Донат звёздами"), callback_data="donate:stars")],
            [InlineKeyboardButton(text="💎 Premium", callback_data="premium:open")],
            [InlineKeyboardButton(text=tr(lang, "🎁 Подарить подарок"), callback_data="donate:gifts")],
            [InlineKeyboardButton(text=tr(lang, "🇷🇺 Донат рублями (для РФ)"), callback_data="donate:rub")],
            [InlineKeyboardButton(text="💳 Donation Alerts", url=DONATIONALERTS_URL)],
            [InlineKeyboardButton(text=tr(lang, "🆘 Поддержка"), callback_data="donate:support")],
        ]
    )


def rub_donate_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Вкладка «Донат рублями (для РФ)»: оплата по СБП с любого банка."""
    rows = []
    if OZON_DONATE_URL:
        rows.append([InlineKeyboardButton(text=tr(lang, "🏦 Любой банк (СБП)"), url=OZON_DONATE_URL)])
    rows.append([InlineKeyboardButton(text=tr(lang, "⬅️ Назад"), callback_data="donate:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def premium_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Тарифы Premium: по кнопке на каждый срок + назад."""
    rows = [[InlineKeyboardButton(text=tr(lang, "💎 {days} дн. — {stars} ⭐", days=d, stars=st), callback_data=f"premium:buy:{d}")]
            for d, st in PREMIUM_PLANS]
    rows.append([InlineKeyboardButton(text=tr(lang, "⬅️ Назад"), callback_data="donate:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def nudge_kb(lang: str = "ru", kind: str = "donate") -> InlineKeyboardMarkup:
    """Кнопки, приклеенные к напоминанию после скачивания."""
    if kind == "premium":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Premium", callback_data="premium:open")],
            [InlineKeyboardButton(text=tr(lang, "💛 Донат"), callback_data="donate:open")],
        ])
    if kind == "support":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=tr(lang, "🆘 Поддержка"), callback_data="donate:support"),
             InlineKeyboardButton(text=tr(lang, "💛 Донат"), callback_data="donate:open")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=tr(lang, "⭐ Донат звёздами"), callback_data="donate:stars"),
         InlineKeyboardButton(text=tr(lang, "🏦 Любой банк (СБП)"), callback_data="donate:rub")],
        [InlineKeyboardButton(text="💳 Donation Alerts", url=DONATIONALERTS_URL),
         InlineKeyboardButton(text="💎 Premium", callback_data="premium:open")],
    ])


def stars_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ 10", callback_data="stars:10"),
                InlineKeyboardButton(text="⭐ 50", callback_data="stars:50"),
                InlineKeyboardButton(text="⭐ 100", callback_data="stars:100"),
            ],
            [
                InlineKeyboardButton(text="⭐ 250", callback_data="stars:250"),
                InlineKeyboardButton(text="⭐ 500", callback_data="stars:500"),
                InlineKeyboardButton(text="⭐ 1000", callback_data="stars:1000"),
            ],
            [InlineKeyboardButton(text=tr(lang, "✍️ Другая сумма"), callback_data="stars:custom")],
            [InlineKeyboardButton(text=tr(lang, "⬅️ Назад"), callback_data="donate:back")],
        ]
    )

SHARE_TEXT = "🔥 Нашёл топового бота для скачивания видео и фото из TikTok — без водяных знаков и подписок. Залетай ☝️"

# ================== HELP ==================




# ================== POST-DOWNLOAD / VIDEO KEYBOARDS ==================
def _share_url(lang: str = "ru") -> str:
    """Ссылка «Поделиться»: в шаре подставляется url, текст — про бота (ссылка вставляется сама)."""
    share_url = urllib.parse.quote_plus(BOT_SHARE_URL)
    share_text = urllib.parse.quote_plus(tr(lang, SHARE_TEXT))
    return f"https://t.me/share/url?url={share_url}&text={share_text}"

def post_download_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Кнопки под последним фото (приклеены прямо к фото, отдельного сообщения нет)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=tr(lang, "💛 Донат"), callback_data="donate:open"),
                InlineKeyboardButton(text="💎 Premium", callback_data="premium:open"),
            ],
            [InlineKeyboardButton(text=tr(lang, "🔗 Поделиться"), url=_share_url(lang))],
        ]
    )


def song_kb(lang: str = "ru", song: Optional[dict] = None, req_id: str = "", can_download: bool = False) -> InlineKeyboardMarkup:
    """Карточка песни: поиск в музыкальных сервисах (URL-кнопки по две в ряд) + «Скачать аудио», если звук ещё не отправлен."""
    from downloaders.song_search import search_links
    rows: List[List[InlineKeyboardButton]] = []
    links = [InlineKeyboardButton(text=label, url=url) for label, url in search_links(song or {})]
    for i in range(0, len(links), 2):
        rows.append(links[i:i + 2])
    if can_download and req_id:
        rows.append([InlineKeyboardButton(text=tr(lang, "⬇️ Скачать аудио"), callback_data=f"dl:audio:{req_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def under_video_kb(has_music: bool = False, has_description: bool = False, req_id: str = "", lang: str = "ru",
                   has_song: bool = False) -> InlineKeyboardMarkup:
    """Кнопки под скачанным видео: Музыка / Найти песню / Описание (если есть) + донат/Premium/поделиться."""
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    if has_music:
        row.append(InlineKeyboardButton(text=tr(lang, "🎵 Музыка"), callback_data=f"dl:audio:{req_id}"))
    if has_song:
        row.append(InlineKeyboardButton(text=tr(lang, "🔎 Найти песню"), callback_data=f"dl:song:{req_id}"))
    if row:
        rows.append(row)
    if has_description:
        rows.append([InlineKeyboardButton(text=tr(lang, "📝 Описание"), callback_data=f"dl:desc:{req_id}")])
    rows.append([
        InlineKeyboardButton(text=tr(lang, "💛 Донат"), callback_data="donate:open"),
        InlineKeyboardButton(text="💎 Premium", callback_data="premium:open"),
        InlineKeyboardButton(text=tr(lang, "🔗 Поделиться"), url=_share_url(lang)),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _fmt_size(num_bytes) -> str:
    if not num_bytes:
        return ""
    mb = num_bytes / (1024 * 1024)
    if mb < 1:
        return ""
    return f" (~{mb:.0f} МБ)" if mb < 1024 else f" (~{mb/1024:.1f} ГБ)"  # единицы переводит quality_choice_kb


def quality_choice_kb(req_id: str, qualities: List[dict], lang: str = "ru") -> InlineKeyboardMarkup:
    """
    Кнопки выбора качества перед скачиванием видео из YouTube/Instagram/VK/
    Pinterest: одна кнопка на каждое доступное разрешение (2 в ряд) плюс
    отдельная строка "Только звук (MP3)" и "Отмена".
    """
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for q in qualities:
        height = q["height"]
        size_txt = _fmt_size(q.get('filesize')).replace(" МБ", " " + tr(lang, "МБ")).replace(" ГБ", " " + tr(lang, "ГБ"))
        label = f"🎬 {q['label']}{size_txt}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"q:v:{height}:{req_id}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text=tr(lang, "✨ Лучшее качество"), callback_data=f"q:v:0:{req_id}")])
    rows.append([InlineKeyboardButton(text=tr(lang, "🎵 Только звук (MP3)"), callback_data=f"q:a:0:{req_id}")])
    rows.append([InlineKeyboardButton(text=tr(lang, "❌ Отмена"), callback_data=f"q:x:0:{req_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def video_choice_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Только «Скачать видео» и «Отмена» — кнопка музыки перенесена под видео."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tr(lang, "🎬 Скачать видео"), callback_data="vd:video")],
            [InlineKeyboardButton(text=tr(lang, "❌ Отмена"), callback_data="vd:cancel")],
        ]
    )

# ================== ADMIN UI ==================
def admin_menu_kb(tex_on: bool = False) -> InlineKeyboardMarkup:
    tex_text = "🔧 Тех. режим: ВКЛ → выкл" if tex_on else "🔧 Тех. режим: выкл → вкл"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="ad:stats"),
                InlineKeyboardButton(text="🏆 Топ", callback_data="ad:top"),
            ],
            [
                InlineKeyboardButton(text="📣 Рассылки", callback_data="ad:bc"),
                InlineKeyboardButton(text="💎 Premium", callback_data="ad:prem"),
            ],
            [InlineKeyboardButton(text="✉️ Написать пользователю", callback_data="ad:msg")],
            [
                InlineKeyboardButton(text="💥 Ошибки", callback_data="ad:errors"),
                InlineKeyboardButton(text="🚫 Бан-лист", callback_data="ad:banlist"),
            ],
            [InlineKeyboardButton(text=tex_text, callback_data="ad:tex")],
            [
                InlineKeyboardButton(text="👑 Администраторы", callback_data="ad:adminlist"),
                InlineKeyboardButton(text="🗄 Дамп БД", callback_data="ad:dbfile"),
            ],
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="ad:back"),
                InlineKeyboardButton(text="🧾 Команды", callback_data="ad:help"),
            ],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="ad:close")],
        ]
    )


def support_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Под экраном поддержки: можно отменить, если открыли случайно."""
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(lang, "❌ Отмена"), callback_data="support:cancel")]])


def admin_reply_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    """Под сообщением от администрации: пользователь может сразу ответить через поддержку."""
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=tr(lang, "💬 Ответить"), callback_data="support:open")]])


def admin_msg_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="ad:msgcancel")]])


def admin_broadcast_menu_kb() -> InlineKeyboardMarkup:
    """Раздел «Рассылки»: готовые шаблоны (core/nudge_texts.BROADCAST_PRESETS) и ручной текст."""
    from core.nudge_texts import BROADCAST_PRESETS
    rows = [[InlineKeyboardButton(text=title, callback_data=f"ad:bp:{pid}")] for pid, (title, _t) in BROADCAST_PRESETS.items()]
    rows.append([InlineKeyboardButton(text="📌 Напоминание про /support", callback_data="ad:bp:support")])
    rows.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="ad:back"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="ad:close"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="ad:back"),
                InlineKeyboardButton(text="❌ Закрыть", callback_data="ad:close"),
            ]
        ]
    )

ADMIN_MENU_TEXT = "🛠 <b>Админ-панель TikSaves</b>"  # запасной текст; живая сводка — core.stats.admin_dashboard_text()

ADMIN_HELP_TEXT = (
    "🧾 <b>Команды администратора</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"

    "📊 <b>Статистика</b>\n"
    f"├ {code('/stats d')} — день\n"
    f"├ {code('/stats n')} — неделя\n"
    f"├ {code('/stats m')} — месяц\n"
    f"├ {code('/stats y')} — год\n"
    f"├ {code('/stats all')} — всё время\n"
    f"└ {code('/stats 2026-02-01 2026-02-07')} — диапазон\n\n"

    "🏆 <b>Топ пользователей</b>\n"
    f"├ {code('/top d')} {code('/top n')} {code('/top m')} {code('/top y')} {code('/top all')}\n"
    f"└ {code('/top 2026-02-01 2026-02-07')} — диапазон\n"
    "   <i>(топ рефереров показывается там же автоматически)</i>\n\n"

    "✉️ <b>Сообщения и диагностика</b>\n"
    f"├ {code('/msg ID текст')} — написать пользователю (ID или @username)\n"
    f"└ {code('/botapi')} — режим Bot API: лимит файлов 50 МБ или 2 ГБ и почему\n\n"
    "💎 <b>Premium</b>\n"
    f"├ {code('/premium ID дней')} — выдать/продлить\n"
    f"├ {code('/premium ID off')} — снять\n"
    f"└ {code('/premium')} — список активных\n\n"

    "🛠 <b>Технический режим</b>\n"
    f"├ {code('/tex текст')} — включить (бот отвечает этим текстом всем, кроме админов)\n"
    f"└ {code('/tex off')} — выключить\n\n"

    "🚫 <b>Баны</b>\n"
    f"├ {code('/ban ID 2h причина')} — забанить\n"
    f"├ {code('/unban ID')} — разбанить\n"
    f"└ {code('/banlist')} — список банов\n\n"

    "👑 <b>Администраторы</b>\n"
    f"├ {code('/adminlist')} — список всех админов\n"
    f"├ {code('/adminadd ID')} — добавить (только суперадмин)\n"
    f"└ {code('/admindel ID')} — удалить (только суперадмин)\n\n"

    "👤 <b>Пользователь</b>\n"
    f"└ {code('/info ID')} — информация о пользователе\n\n"

    "🧾 <b>История скачиваний</b>\n"
    f"├ {code('/history')} — своя история файлом\n"
    f"├ {code('/history ID')} или {code('/history @username')} — история человека\n"
    f"├ {code('/history all')} — последние скачивания всех пользователей\n"
    f"└ {code('csv')} в конце команды — таблицей, напр. {code('/history all csv')}\n\n"

    "💛 <b>Донаты (ручная правка)</b>\n"
    f"├ {code('/stars ID 250')} — установить сумму доната звёздами\n"
    f"└ {code('/money ID 500')} — установить сумму доната в рублях\n\n"

    "🗄 <b>База данных</b>\n"
    f"└ {code('/dbfile')} — дамп БД файлом\n\n"

    "📣 <b>Рассылка</b>\n"
    f"├ {code('/broadcast текст')} — своя рассылка\n"
    f"├ {code('/reminder_message')} — напоминание\n"
    f"└ {code('/advertisement_message')} — реклама\n"
)

def admin_broadcast_confirm_kb(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить всем", callback_data=f"ad:send:{kind}")],
            [
                InlineKeyboardButton(text="⬅️ К шаблонам", callback_data="ad:bc"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="ad:cancel"),
            ],
        ]
    )

def broadcast_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⛔ Остановить рассылку", callback_data="ad:bcancel")],
        ]
    )
