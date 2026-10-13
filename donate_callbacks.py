"""
Callback-обработчики, связанные с донатами и музыкой под уже отправленным видео:
- dl:* — "Музыка" под видео;
- donate:* — открытие меню донатов;
- stars:* — выбор суммы Stars и кастомная сумма;
- pre_checkout / successful_payment — оплата Telegram Stars.
"""
import time
import contextlib

from aiogram import F
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, LinkPreviewOptions

from globals_state import dp
from i18n import tr, get_lang
import globals_state
from config import STARS_MIN, STARS_MAX
from storage import store
from user_label import resolve_user_label
from gates import gate_callback, gate_message
from logging_channel import log_event, format_user_for_log
from send_helpers import send_music_if_any, send_external_audio, send_description_if_any
from picker_state import video_extras
from keyboards import (
    DONATE_TEXT,
    STARS_MENU_TEXT,
    SUPPORT_TEXT,
    donate_main_kb,
    stars_kb,
    under_video_kb,
)
from donate import stars_valid, safe_edit, send_stars_invoice, waiting_stars_amount


@dp.callback_query(F.data.startswith("dl:"))
async def dl_cb(call: CallbackQuery):
    uid = call.from_user.id
    label = await resolve_user_label(call.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_callback(call, label):
        return

    parts = (call.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    req_id = parts[2] if len(parts) > 2 else ""
    extra = video_extras.get(req_id)

    if action == "audio":
        url = extra.get("music") if extra else None
        if not url:
            await call.answer(tr(uid, "Нет звука для этого видео."), show_alert=True)
            return
        extra["music"] = None
        await call.answer(tr(uid, "Отправляю звук…"))
        if extra.get("music_mode") == "ytdlp_external":
            await send_external_audio(call.message, url, uid=uid, label=label)
        else:
            await send_music_if_any(call.message, globals_state.g_provider, url, uid=uid, label=label, src=extra.get("src"))
        with contextlib.suppress(Exception):
            if call.message:
                await call.message.edit_reply_markup(
                    reply_markup=under_video_kb(has_music=False, has_description=bool(extra.get("description")), req_id=req_id, lang=get_lang(uid))
                )
        if not extra.get("music") and not extra.get("description"):
            video_extras.pop(req_id, None)
        return

    if action == "desc":
        desc = extra.get("description") if extra else None
        if not desc:
            await call.answer(tr(uid, "Нет описания для этого видео."), show_alert=True)
            return
        extra["description"] = None
        await call.answer(tr(uid, "Отправляю описание…"))
        if call.message:
            await send_description_if_any(call.message, desc)
            store.inc_description(uid)
        with contextlib.suppress(Exception):
            if call.message:
                await call.message.edit_reply_markup(
                    reply_markup=under_video_kb(has_music=bool(extra.get("music")), has_description=False, req_id=req_id, lang=get_lang(uid))
                )
        if not extra.get("music") and not extra.get("description"):
            video_extras.pop(req_id, None)
        return

    await call.answer()


@dp.callback_query(F.data.startswith("donate:"))
async def donate_cb(call: CallbackQuery):
    uid = call.from_user.id
    label = await resolve_user_label(call.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_callback(call, label):
        return

    action = (call.data or "").split(":", 1)[-1]
    if action == "open":
        if call.message:
            await call.message.answer(tr(uid, DONATE_TEXT), parse_mode="HTML", reply_markup=donate_main_kb(get_lang(uid)), link_preview_options=LinkPreviewOptions(is_disabled=True))
        await call.answer()
        return

    if action == "stars":
        await safe_edit(call, tr(uid, STARS_MENU_TEXT, a=STARS_MIN, b=STARS_MAX), stars_kb(get_lang(uid)))
        await call.answer()
        return

    if action == "back":
        await safe_edit(call, tr(uid, DONATE_TEXT), donate_main_kb(get_lang(uid)))
        await call.answer()
        return

    if action == "support":
        await call.answer()
        if call.message:
            await call.message.answer(tr(uid, SUPPORT_TEXT), parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True))
        return

    await call.answer()


@dp.callback_query(F.data.startswith("stars:"))
async def stars_cb(call: CallbackQuery):
    uid = call.from_user.id
    label = await resolve_user_label(call.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_callback(call, label):
        return

    action = (call.data or "").split(":", 1)[-1]
    if action == "custom":
        waiting_stars_amount[uid] = time.time()
        await call.answer()
        if call.message:
            await call.message.answer(tr(uid, "✍️ Введи сумму доната {a}–{b} ⭐ одним числом:", a=STARS_MIN, b=STARS_MAX), parse_mode="HTML")
        return

    try:
        stars = int(action)
    except ValueError:
        await call.answer(tr(uid, "❌ Ошибка суммы"), show_alert=True)
        return

    if not stars_valid(stars):
        await call.answer(tr(uid, "❌ Сумма должна быть {a}–{b} ⭐", a=STARS_MIN, b=STARS_MAX), show_alert=True)
        return

    await call.answer()
    await send_stars_invoice(call.bot, uid, stars, get_lang(uid))


@dp.pre_checkout_query()
async def pre_checkout(pre: PreCheckoutQuery):
    await pre.answer(ok=True)


@dp.message(F.successful_payment)
async def payment_ok(message: Message):
    uid = message.from_user.id
    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_message(message, label):
        return

    stars = int(message.successful_payment.total_amount)
    store.add_stars(uid, stars)

    await message.answer(
        tr(message, "✅ <b>Оплата прошла!</b>\nПолучено: <b>{stars} ⭐</b>\n\nСпасибо за поддержку 🙌", stars=stars),
        parse_mode="HTML",
    )

    await log_event(
        message.bot,
        "stars",
        [
            "⭐ Категория: <b>Пополнение Stars</b>",
            f"👤 User/id: <b>{format_user_for_log(label, uid)}</b>",
            f"💫 Сумма: <b>{stars} ⭐</b>",
        ],
    )
