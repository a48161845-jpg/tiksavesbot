"""
Поддержка (/support) — без внешнего аккаунта, всё внутри бота:

1. Пользователь пишет /support -> бот просит одним сообщением описать вопрос
   и ждёт его следующее сообщение (SUPPORT_WAIT_TTL_SEC секунд).
2. Это сообщение (любого типа — текст, фото, документ и т.д.) пересылается
   главному администратору (SUPPORT_ADMIN_ID) в личку боту.
3. Администратор отвечает Reply прямо на пересланное сообщение в этом же
   чате с ботом — ответ уходит обратно тому пользователю, который написал
   заявку.

Состояние (кто чего ждёт, какое пересланное сообщение к какому пользователю
относится) хранится в памяти — см. support_state.py.
"""
import contextlib
import time

from aiogram import F
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import Message, LinkPreviewOptions

from globals_state import dp
from config import SUPPORT_ADMIN_ID, SUPPORT_WAIT_TTL_SEC
from helpers import is_admin
from storage import store
from user_label import resolve_user_label
from gates import gate_message
from logging_channel import log_event, format_user_for_log
from keyboards import SUPPORT_TEXT, SUPPORT_SENT_TEXT
from support_state import waiting_support_message, support_tickets, cleanup


@dp.message(Command("support"))
async def support_cmd(message: Message):
    uid = message.from_user.id
    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)
    if not await gate_message(message, label):
        return

    cleanup()
    waiting_support_message[uid] = time.time()
    await message.answer(SUPPORT_TEXT, parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True))
    await log_event(
        message.bot,
        "support",
        [
            "🆘 Категория: <b>Открыта поддержка</b>",
            f"👤 User/id: <b>{format_user_for_log(label, uid)}</b>",
        ],
    )


async def _deliver_to_admin(message: Message, uid: int, label: str) -> None:
    """Пересылает заявку админу и запоминает, кому нужно доставить ответ."""
    header = (
        "🆘 <b>Новая заявка в поддержку</b>\n"
        f"👤 От: {format_user_for_log(label, uid)}\n\n"
        "<i>Ответь на следующее сообщение (Reply) — ответ уйдёт пользователю.</i>"
    )
    with contextlib.suppress(Exception):
        await message.bot.send_message(SUPPORT_ADMIN_ID, header, parse_mode="HTML")

    forwarded = None
    with contextlib.suppress(Exception):
        forwarded = await message.copy_to(SUPPORT_ADMIN_ID)

    if forwarded is not None:
        support_tickets[forwarded.message_id] = {"uid": uid, "label": label, "ts": time.time()}


# ------- ответ администратора: Reply на пересланное сообщение -------
@dp.message(F.reply_to_message)
async def support_admin_reply(message: Message):
    admin_id = message.from_user.id
    if not is_admin(admin_id):
        raise SkipHandler

    reply_to = message.reply_to_message
    cleanup()
    ticket = support_tickets.pop(reply_to.message_id, None) if reply_to else None
    if ticket is None:
        raise SkipHandler

    target_uid = int(ticket["uid"])
    target_label = ticket.get("label", "")

    delivered = False
    with contextlib.suppress(Exception):
        await message.copy_to(target_uid)
        delivered = True

    if delivered:
        await message.reply(
            f"✅ Ответ отправлен: <b>{format_user_for_log(target_label, target_uid)}</b>",
            parse_mode="HTML",
        )
        await log_event(
            message.bot,
            "support_reply",
            [
                "💬 Категория: <b>Ответ поддержки</b>",
                f"👤 Кому: <b>{format_user_for_log(target_label, target_uid)}</b>",
            ],
        )
    else:
        await message.reply(
            "⚠️ Не удалось доставить ответ (пользователь мог заблокировать бота).",
            parse_mode="HTML",
        )


# ------- сообщение пользователя, которое мы ждём после /support -------
@dp.message(F.text)
async def support_text_capture(message: Message):
    uid = message.from_user.id
    text = (message.text or "").strip()
    if text.startswith("/"):
        raise SkipHandler

    ts = waiting_support_message.get(uid)
    if not ts or time.time() - ts > SUPPORT_WAIT_TTL_SEC:
        waiting_support_message.pop(uid, None)
        raise SkipHandler
    waiting_support_message.pop(uid, None)

    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)
    if not await gate_message(message, label):
        return

    await _deliver_to_admin(message, uid, label)
    await message.answer(SUPPORT_SENT_TEXT, parse_mode="HTML")


@dp.message(F.content_type != "text")
async def support_media_capture(message: Message):
    uid = message.from_user.id
    ts = waiting_support_message.get(uid)
    if not ts or time.time() - ts > SUPPORT_WAIT_TTL_SEC:
        waiting_support_message.pop(uid, None)
        raise SkipHandler
    waiting_support_message.pop(uid, None)

    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)
    if not await gate_message(message, label):
        return

    await _deliver_to_admin(message, uid, label)
    await message.answer(SUPPORT_SENT_TEXT, parse_mode="HTML")
