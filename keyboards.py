"""
Инлайн-клавиатуры и текстовые константы, которые показываются пользователю.
Здесь нет бизнес-логики — только разметка интерфейса.
"""
import urllib.parse
from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import SUPPORT_USERNAME, CRYPTO_DONATE_URL, DONATIONALERTS_URL, BOT_SHARE_URL, STARS_MIN, STARS_MAX, GIFTS, MAX_VIDEO_MB
from helpers import html_escape, code

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
START_TEXT = (
    "👋 <b>Привет! Я TikSaves</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Скачиваю видео, фото-слайдшоу и музыку из TikTok, а ещё видео с YouTube (в т.ч. Shorts), Instagram, VK и Pinterest.\n\n"
    "📎 <b>Просто пришли ссылку</b> — остальное сделаю сам, без водяных знаков и подписок.\n\n"
    "🧭 <b>Полезное:</b>\n"
    "🧾 Помощь — /help\n"
    "📊 Моя статистика — /me\n"
    "🎁 Рефералы и подарки — /ref\n"
    "💛 Поддержать проект — /donate\n"
    "🆘 Поддержка — /support"
)

# ================== DONATE ==================
def donate_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Донат звёздами", callback_data="donate:stars")],
            [InlineKeyboardButton(text="💳 Donation Alerts", url=DONATIONALERTS_URL)],
            [InlineKeyboardButton(text="💲 Донат криптой", url=CRYPTO_DONATE_URL)],
            [InlineKeyboardButton(text="🆘 Поддержка", callback_data="donate:support")],
        ]
    )

def stars_kb() -> InlineKeyboardMarkup:
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
            [InlineKeyboardButton(text="✍️ Другая сумма", callback_data="stars:custom")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="donate:back")],
        ]
    )

DONATE_TEXT = (
    "💛 <b>Поддержать TikSaves</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Спасибо, что пользуешься ботом! Донат помогает держать его быстрым и стабильным:\n\n"
    "☁️ хостинг и трафик 24/7\n"
    "🔌 поддержка API и серверов\n"
    "🚀 новые фичи и улучшения\n\n"
    "Выбери удобный способ 👇"
)
STARS_MENU_TEXT = (
    "⭐ <b>Telegram Stars</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Самый быстрый способ поддержать проект прямо в Telegram.\n\n"
    f"Выбери сумму ({STARS_MIN}–{STARS_MAX} ⭐) или введи свою 👇"
)
SUPPORT_TEXT = (
    "🆘 <b>Поддержка</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    f"Есть вопрос или что-то не работает? Пиши сюда: {html_escape(SUPPORT_USERNAME)}\n\n"
    "Приложи ссылку на видео и опиши, что пошло не так — так разберёмся быстрее 🙌"
)
SHARE_TEXT = "🔥 Нашёл топового бота для скачивания видео и фото из TikTok — без водяных знаков и подписок. Залетай ☝️"

# ================== HELP ==================
HELP_TEXT = (
    "🧾 <b>Помощь по TikSaves</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "📎 Просто пришли ссылку на TikTok, YouTube, Instagram, VK или Pinterest — бот сам предложит варианты.\n\n"
    "🧭 <b>Кнопки помощи:</b>\n"
    "🎬 Скачать видео — помощь по скачиванию видео\n"
    "🖼️ Скачать фото — помощь по скачиванию фото\n"
    "⚠️ Лимиты — помощь по лимитам\n"
    "📳 Inline-режим — помощь по скачиванию видео в Inline-режиме\n"
    "👥 Реферальная система — помощь по реферальной системе"
)

def help_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Скачать видео", callback_data="help:video"),
                InlineKeyboardButton(text="🖼️ Скачать фото", callback_data="help:photo"),
            ],
            [
                InlineKeyboardButton(text="⚠️ Лимиты", callback_data="help:limits"),
            ],
            [
                InlineKeyboardButton(text="📳 Inline-режим", callback_data="help:inline"),
                InlineKeyboardButton(text="👥 Реферальная система", callback_data="help:referral"),
            ],
            [
                InlineKeyboardButton(text="❌ Закрыть", callback_data="help:close"),
            ],
        ]
    )

def help_section_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="help:back"),
                InlineKeyboardButton(text="❌ Закрыть", callback_data="help:close"),
            ]
        ]
    )

HELP_SECTIONS = {
    "video": (
        "🎬 <b>Помощь по скачиванию видео</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ Пришли ссылку на TikTok, YouTube, Instagram, VK или Pinterest 📱\n\n"
        "2️⃣ Подожди несколько секунд пока скачивается видео ⏳\n\n"
        "3️⃣ Получай готовое видео в хорошем качестве без водяных знаков 🎉\n\n"
        f"⛔ При ошибке повтори попытку, при повторной ошибке напиши в /support"
    ),
    "photo": (
        "🖼️ <b>Помощь по скачиванию фото</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ Пришли ссылку на TikTok-слайдшоу 📱\n\n"
        "2️⃣ Выбери скачать как фото или как видео\n\n"
        "3️⃣ При выборе «как фото» откроется меню с выбором страниц и возможностью скачать 🎵 Музыку / 📝 Описание\n\n"
        "4️⃣ При скачивании видео придёт файл с кнопками 🎵 Музыка / 📝 Описание\n\n"
        "🖼️ <b>Меню скачивания фото:</b>\n\n"
        "5️⃣ Цифры сверху — нажимая на цифру, ты выбираешь конкретное фото для скачивания. Можно выбрать 1, 2, 3 или все 10\n\n"
        "6️⃣ «Выбрать страницу» — выбираешь сразу все 10 фото на странице, если не хочешь выбирать вручную (есть кнопки переключения страниц)\n\n"
        "7️⃣ «Скачать всё» — скачиваются все фото, а также музыка и описание\n\n"
        "8️⃣ «🎵 Музыка» — выбирает музыку (нажимай, если не выбрал «Скачать всё»). «📝 Описание» — выбирает описание (нажимай, если не выбрал «Скачать всё»)\n\n"
        "9️⃣ «Очистить» — сбрасывает все выборы, «Продолжить» — скачивает всё, что выбрано\n\n"
        f"⛔ При ошибке повтори попытку, при повторной ошибке напиши в /support"
    ),
    "limits": (
        "⚠️ <b>Лимиты</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Слишком частые запросы придерживаются небольшим кулдауном — просто подожди пару секунд.\n"
        "При систематическом флуде возможна временная блокировка.\n\n"
        f"📦 <b>Размер файла:</b> Telegram не даёт ботам отправлять файлы тяжелее {MAX_VIDEO_MB} МБ — "
        "это ограничение платформы, не бота. Слишком тяжёлые видео (обычно очень длинные ролики "
        "с YouTube/VK) скачать не получится."
    ),
    "inline": (
        "📳 <b>Помощь по Inline-режиму</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Скачивай видео не только в боте 🎉\n\n"
        "1️⃣ Введи в любом чате <code>@tiksavesbot</code>, подожди немного пока появится результат, "
        "затем вставь ссылку на TikTok-слайдшоу или пришли ссылку на TikTok-видео, YouTube, Instagram, VK или Pinterest\n\n"
        "2️⃣ Подожди немного, пока загрузится видео или TikTok-слайдшоу\n\n"
        "3️⃣ Получай готовое видео в хорошем качестве без водяных знаков 🎉\n\n"
        f"⛔ При ошибке повтори попытку, при повторной ошибке напиши в /support"
    ),
    "referral": (
        "👥 <b>Помощь по реферальной системе</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ Забери свою ссылку в /ref\n\n"
        "2️⃣ Отправь её друзьям\n\n"
        "3️⃣ Как только друг скачает первое видео — тебе: 💎 +10 🎟\n\n"
        "4️⃣ Копи баллы и меняй их на подарки в магазине 🎁\n\n"
        "✋ Подарки выдаются вручную администрацией — обычно быстро.\n\n"
        "⛔ Перед выводом каждый реферал будет проверяться вручную, за накрутки будет отказано в выводе, "
        "а рефералы обнулены."
    ),
}

# ================== POST-DOWNLOAD / VIDEO KEYBOARDS ==================
def _share_url() -> str:
    """Ссылка «Поделиться»: в шаре подставляется url, текст — про бота (ссылка вставляется сама)."""
    share_url = urllib.parse.quote_plus(BOT_SHARE_URL)
    share_text = urllib.parse.quote_plus(SHARE_TEXT)
    return f"https://t.me/share/url?url={share_url}&text={share_text}"

def post_download_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💛 Донат", callback_data="donate:open"),
                InlineKeyboardButton(text="🔗 Поделиться", url=_share_url()),
            ]
        ]
    )

def under_video_kb(has_music: bool = False, has_description: bool = False, req_id: str = "") -> Optional[InlineKeyboardMarkup]:
    """Кнопки под скачанным видео: Музыка (если есть), Описание (если есть). Без доната/поделиться."""
    row: List[InlineKeyboardButton] = []
    if has_music:
        row.append(InlineKeyboardButton(text="🎵 Музыка", callback_data=f"dl:audio:{req_id}"))
    if has_description:
        row.append(InlineKeyboardButton(text="📝 Описание", callback_data=f"dl:desc:{req_id}"))

    if not row:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[row])

def video_choice_kb() -> InlineKeyboardMarkup:
    """Только «Скачать видео» и «Отмена» — кнопка музыки перенесена под видео."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎬 Скачать видео", callback_data="vd:video")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="vd:cancel")],
        ]
    )

# ================== ADMIN UI ==================
def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="ad:stats"),
            ],
            [
                InlineKeyboardButton(text="🚫 Бан-лист", callback_data="ad:banlist"),
                InlineKeyboardButton(text="🗄 Дамп БД", callback_data="ad:dbfile"),
            ],
            [
                InlineKeyboardButton(text="📌 Напоминание", callback_data="ad:reminder"),
                InlineKeyboardButton(text="💛 Донат", callback_data="ad:donate"),
            ],
            [
                InlineKeyboardButton(text="🎁 Рефералка", callback_data="ad:refreminder"),
            ],
            [
                InlineKeyboardButton(text="👑 Администраторы", callback_data="ad:adminlist"),
            ],
            [
                InlineKeyboardButton(text="🧾 Команды", callback_data="ad:help"),
                InlineKeyboardButton(text="❌ Закрыть", callback_data="ad:close"),
            ],
        ]
    )

def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="ad:back"),
                InlineKeyboardButton(text="❌ Закрыть", callback_data="ad:close"),
            ]
        ]
    )

ADMIN_MENU_TEXT = (
    "🛠 <b>Админ-панель TikSaves</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "📊 <b>Статистика</b> — по периодам (внутри — 🏆 Топ и 💥 Ошибки)\n"
    "🚫 <b>Бан-лист</b> — активные баны\n"
    "🗄 <b>Дамп БД</b> — скачать базу данных\n"
    "👑 <b>Администраторы</b> — список и управление\n"
    "📌 <b>Напоминание</b> / 💛 <b>Донат</b> / 🎁 <b>Рефералка</b> — рассылки вручную\n"
    "🧾 <b>Команды</b> — полный список\n"
)

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

    "🎁 <b>Реферальная система</b>\n"
    f"├ {code('/refid ID')} — кто пригласил пользователя\n"
    f"├ {code('/refinfo ID')} — список его рефералов\n"
    f"├ {code('/refpoints ID +50')} — начислить/списать баллы\n"
    f"├ {code('/refcount ID +3')} — скорректировать счётчик рефералов\n"
    f"└ {code('/refreset ID')} — обнулить баллы и рефералов\n\n"

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
    f"└ {code('/info ID')} — информация о пользователе (включая рефералов)\n\n"

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
            [
                InlineKeyboardButton(text="✅ Отправить", callback_data=f"ad:send:{kind}"),
            ],
            [
                InlineKeyboardButton(text="❌ Закрыть", callback_data="ad:close"),
            ],
        ]
    )

def broadcast_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⛔ Остановить рассылку", callback_data="ad:bcancel")],
        ]
    )


# ================== REFERRAL / GIFT SHOP ==================
def ref_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Магазин подарков", callback_data="ref:shop")],
            [InlineKeyboardButton(text="📦 Мои заявки", callback_data="ref:myrequests")],
            [InlineKeyboardButton(text="🏆 Топ рефереров", callback_data="ref:top")],
        ]
    )


def ref_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="ref:back")]])


def gift_shop_kb(balance: int) -> InlineKeyboardMarkup:
    """Магазин подарков в /ref — каждый подарок 55⭐ (реальная оплата Stars,
    доступна всегда) или 500🎟 (списание билетиков, нужен баланс)."""
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for g in GIFTS:
        # За звёзды можно купить всегда (это настоящая оплата Telegram Stars,
        # а не виртуальный баланс) — поэтому подарки в магазине не блокируем.
        row.append(InlineKeyboardButton(text=f"{g['emoji']} {g['name']}", callback_data=f"gift:buy:{g['key']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад в /ref", callback_data="ref:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def gift_confirm_kb(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"gift:confirm:{key}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="gift:cancel"),
            ]
        ]
    )


def gift_admin_kb(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выдать", callback_data=f"admgift:ok:{req_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admgift:no:{req_id}"),
            ]
        ]
    )
