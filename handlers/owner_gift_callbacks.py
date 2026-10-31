"""
Мастер «🎁 Подарить подарок владельцу бота»: кнопки og:* и ввод текста к подарку.
Оплата (successful_payment с payload «ogift:…») обрабатывается в donate_callbacks.payment_ok.
"""
import contextlib
import time

from aiogram import F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import owner_gifts as og
from config import OWNER_GIFT_TEXT_MAX
from donate import safe_edit
from gates import gate_callback, gate_message
from globals_state import dp
from helpers import html_escape, is_admin
from i18n import tr, get_lang
from storage import store
from user_label import resolve_user_label


async def show_list(call: CallbackQuery) -> None:
    """Экран со списком подарков (вызывается и из donate:gifts)."""
    uid = call.from_user.id
    if not og.gifts():
        await call.answer(tr(uid, og.S_EMPTY), show_alert=True)
        return
    og.sessions.pop(uid, None)
    await safe_edit(call, tr(uid, og.S_LIST), og.list_kb(get_lang(uid)))
    await call.answer()


async def _show_confirm(uid: int, s: dict, *, call: CallbackQuery = None, message: Message = None) -> None:
    g = og.gift_by_key(s.get("key", ""))
    body = og.render_confirm(uid, s)
    if not g or not body:
        txt = tr(uid, og.S_EXPIRED)
        if call:
            await safe_edit(call, txt, og.cancel_kb(get_lang(uid)))
        elif message:
            await message.answer(txt)
        return
    kb = og.confirm_kb(get_lang(uid), g["price"])
    if call:
        await safe_edit(call, body, kb)
    elif message:
        await message.answer(body, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("og:"))
async def og_cb(call: CallbackQuery):
    uid = call.from_user.id
    label = await resolve_user_label(call.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_callback(call, label):
        return

    parts = (call.data or "").split(":")
    act = parts[1] if len(parts) > 1 else ""
    arg = parts[2] if len(parts) > 2 else ""
    lang = get_lang(uid)

    if act == "list":
        await show_list(call)
        return

    if act == "cancel":
        og.sessions.pop(uid, None)
        await safe_edit(call, tr(uid, og.S_CANCELLED), og.list_kb(lang) if og.gifts() else og.cancel_kb(lang))
        await call.answer()
        return

    if act == "pick":
        g = og.gift_by_key(arg)
        if not g:
            await call.answer(tr(uid, og.S_EXPIRED), show_alert=True)
            return
        og.sessions[uid] = {"key": g["key"], "anon": True, "text": "", "await_text": False, "ts": time.time()}
        await safe_edit(
            call,
            tr(uid, og.S_ANON, emoji=g["emoji"], name=html_escape(og.gift_name(g, uid)), price=g["price"]),
            og.anon_kb(lang),
        )
        await call.answer()
        return

    s = og.get_session(uid)
    if not s:
        await call.answer(tr(uid, og.S_EXPIRED), show_alert=True)
        return
    s["await_text"] = False

    if act == "anon":
        s["anon"] = arg == "1"
        await safe_edit(call, tr(uid, og.S_TEXT), og.text_kb(lang))
        await call.answer()
        return

    if act == "back":
        g = og.gift_by_key(s.get("key", ""))
        if arg == "anon" and g:
            await safe_edit(
                call,
                tr(uid, og.S_ANON, emoji=g["emoji"], name=html_escape(og.gift_name(g, uid)), price=g["price"]),
                og.anon_kb(lang),
            )
        else:
            await safe_edit(call, tr(uid, og.S_TEXT), og.text_kb(lang))
        await call.answer()
        return

    if act == "txt":
        if arg == "1":
            s["await_text"] = True
            await safe_edit(call, tr(uid, og.S_ASK_TEXT, n=OWNER_GIFT_TEXT_MAX), og.cancel_kb(lang))
            await call.answer()
            return
        s["text"] = ""
        await _show_confirm(uid, s, call=call)
        await call.answer()
        return

    if act == "pay":
        g = og.gift_by_key(s.get("key", ""))
        if not g:
            await call.answer(tr(uid, og.S_EXPIRED), show_alert=True)
            return
        token = og.create_pending(uid, s)
        if not token:
            await call.answer(tr(uid, og.S_EXPIRED), show_alert=True)
            return
        await call.answer()
        try:
            await og.send_gift_invoice(call.bot, uid, token, g)
        except Exception:
            og.pop_pending(token)
            with contextlib.suppress(Exception):
                await call.message.answer(tr(uid, "❌ Не получилось открыть оплату. Попробуй позже."))
        return

    await call.answer()


def _waiting_gift_text(message: Message) -> bool:
    if not message.from_user or not message.text or message.text.startswith("/"):
        return False
    return og.is_waiting_text(message.from_user.id)


@dp.message(F.text, _waiting_gift_text)
async def og_text(message: Message):
    uid = message.from_user.id
    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_message(message, label):
        og.sessions.pop(uid, None)
        return

    s = og.get_session(uid)
    if not s or not s.get("await_text"):
        return

    text = (message.text or "").strip()
    if len(text) > OWNER_GIFT_TEXT_MAX:
        await message.answer(tr(uid, og.S_TEXT_LONG, n=OWNER_GIFT_TEXT_MAX))
        return

    s["text"] = text
    s["await_text"] = False
    with contextlib.suppress(Exception):
        await _show_confirm(uid, s, message=message)


@dp.message(Command("giftids"))
async def giftids_cmd(message: Message):
    """Админ-команда: список подарков каталога Telegram с id — чтобы вписать gift_id в config.OWNER_GIFTS."""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    try:
        res = await message.bot.get_available_gifts()
    except Exception as e:
        await message.answer(f"❌ Не получилось получить каталог: {html_escape(str(e)[:200])}")
        return
    rows = []
    for g in res.gifts:
        emoji = getattr(getattr(g, "sticker", None), "emoji", "") or "🎁"
        rows.append(f"{emoji} {g.star_count} ⭐ — <code>{g.id}</code>")
    if not rows:
        await message.answer("Каталог пуст.")
        return
    head = "🎁 <b>Подарки Telegram</b> (цена · gift_id):\n\n"
    chunk = head
    for r in rows:
        if len(chunk) + len(r) > 3800:
            await message.answer(chunk)
            chunk = ""
        chunk += r + "\n"
    if chunk.strip():
        await message.answer(chunk)
