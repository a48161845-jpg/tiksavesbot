"""
Callback-обработчик кнопок раздела помощи (callback_data, начинающийся на "help:").
"""
import contextlib

from aiogram import F
from aiogram.types import CallbackQuery

from globals_state import dp
from keyboards import HELP_TEXT, HELP_SECTIONS, help_kb, help_section_kb
from donate import safe_edit
from i18n import tr, get_lang


@dp.callback_query(F.data.startswith("help:"))
async def help_cb(call: CallbackQuery):
    uid = call.from_user.id
    lang = get_lang(uid)
    action = (call.data or "").split(":", 1)[-1]
    if action == "close":
        with contextlib.suppress(Exception):
            if call.message:
                await call.message.delete()
        await call.answer()
        return
    if action == "back":
        if call.message:
            await safe_edit(call, tr(lang, HELP_TEXT), help_kb(lang))
        await call.answer()
        return
    text = HELP_SECTIONS.get(action)
    if text and call.message:
        await safe_edit(call, tr(lang, text), help_section_kb(lang))
        await call.answer()
        return
    await call.answer()
