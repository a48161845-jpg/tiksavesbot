"""
/settings и /language: выбор языка интерфейса. Показывается также новым
пользователям при первом /start (callback lang:xx:start).
"""
import contextlib

from aiogram import F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from globals_state import dp
from keyboards import START_TEXT
from i18n import LANGUAGES, get_lang, set_lang, tr
from storage import store
from user_label import resolve_user_label
from gates import gate_message, gate_callback

# Тексты экрана настроек — на всех языках сразу (сам экран про выбор языка).
_SETTINGS = {
    "ru": "⚙️ <b>Настройки</b>\n━━━━━━━━━━━━━━━━━━━━\n\n🌐 Язык: <b>{lang}</b>\n\nВыбери язык ниже 👇",
    "en": "⚙️ <b>Settings</b>\n━━━━━━━━━━━━━━━━━━━━\n\n🌐 Language: <b>{lang}</b>\n\nChoose a language below 👇",
    "uk": "⚙️ <b>Налаштування</b>\n━━━━━━━━━━━━━━━━━━━━\n\n🌐 Мова: <b>{lang}</b>\n\nОбери мову нижче 👇",
}
_CHANGED = {
    "ru": "✅ Язык изменён: {lang}",
    "en": "✅ Language changed: {lang}",
    "uk": "✅ Мову змінено: {lang}",
}
# Приветствие при первом входе — двуязычное, пока язык ещё не выбран.
LANG_PROMPT = "🌐 <b>Выберите язык / Choose your language / Обери мову</b>"


def lang_kb(current: str = "", first: bool = False) -> InlineKeyboardMarkup:
    suffix = ":start" if first else ""
    rows = [
        [InlineKeyboardButton(text=("✅ " if code == current else "") + name, callback_data=f"lang:{code}{suffix}")]
        for code, name in LANGUAGES.items()
    ]
    if not first:
        rows.append([InlineKeyboardButton(text=tr(current or "ru", "❌ Закрыть"), callback_data="lang:close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_text(lang: str) -> str:
    return _SETTINGS.get(lang, _SETTINGS["ru"]).format(lang=LANGUAGES.get(lang, lang))


async def send_language_prompt(message: Message) -> None:
    await message.answer(LANG_PROMPT, parse_mode="HTML", reply_markup=lang_kb(first=True))


@dp.message(Command("settings", "language", "lang"))
async def settings_cmd(message: Message):
    uid = message.from_user.id
    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)
    if not await gate_message(message, label):
        return
    store.register(uid)
    lang = get_lang(uid)
    await message.answer(settings_text(lang), parse_mode="HTML", reply_markup=lang_kb(lang))


@dp.callback_query(F.data.startswith("lang:"))
async def lang_cb(call: CallbackQuery):
    uid = call.from_user.id
    label = await resolve_user_label(call.bot, uid)
    if not await gate_callback(call, label):
        return

    parts = (call.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    first = len(parts) > 2 and parts[2] == "start"

    if action == "close":
        with contextlib.suppress(Exception):
            if call.message:
                await call.message.delete()
        await call.answer()
        return

    if action not in LANGUAGES:
        await call.answer()
        return

    store.register(uid)
    set_lang(uid, action)
    await call.answer(_CHANGED[action].format(lang=LANGUAGES[action]))

    if not call.message:
        return
    if first:
        # Первый вход: заменяем выбор языка приветствием на выбранном языке.
        with contextlib.suppress(Exception):
            await call.message.delete()
        await call.message.answer(tr(action, START_TEXT), parse_mode="HTML")
        return
    with contextlib.suppress(Exception):
        await call.message.edit_text(settings_text(action), parse_mode="HTML", reply_markup=lang_kb(action))
