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
from aiogram.types import CallbackQuery, Message, LinkPreviewOptions

from core.globals_state import dp
from i18n import tr, get_lang
from core.config import SUPPORT_ADMIN_ID, SUPPORT_WAIT_TTL_SEC
from core.helpers import is_admin
from core.storage import store
from core.user_label import resolve_user_label
from core.gates import gate_message
from core.logging_channel import log_event, format_user_for_log
from ui.keyboards import SUPPORT_TEXT, SUPPORT_SENT_TEXT, support_kb
from ui.support_state import waiting_support_message, support_tickets, cleanup


async def open_support(target: Message, uid: int, label: str) -> None:
    """Открывает обращение: ждём следующее сообщение пользователя. Под экраном есть «❌ Отмена»."""
    cleanup()
    waiting_support_message[uid] = time.time()
    await target.answer(tr(uid, SUPPORT_TEXT), parse_mode="HTML", reply_markup=support_kb(get_lang(uid)),
                        link_preview_options=LinkPreviewOptions(is_disabled=True))
    await log_event(
        target.bot,
        "support",
        [
            "🆘 Категория: <b>Открыта поддержка</b>",
            f"👤 User/id: <b>{format_user_for_log(label, uid)}</b>",
        ],
    )


@dp.message(Command("support"))
async def support_cmd(message: Message):
    uid = message.from_user.id
    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)
    if not await gate_message(message, label):
        return
    await open_support(message, uid, label)


@dp.message(Command("cancel"))
async def cancel_cmd(message: Message):
    """/cancel — отменить открытую поддержку."""
    from ui.support_state import pending_admin_msg
    uid = message.from_user.id
    if pending_admin_msg.pop(uid, None) is not None:
        await message.answer("✖️ Отправка пользователю отменена.")
    elif waiting_support_message.pop(uid, None) is not None:
        await message.answer(tr(message, "✖️ Обращение отменено. Если понадобится помощь — /support."), parse_mode="HTML")
    else:
        raise SkipHandler


@dp.callback_query(F.data.startswith("support:"))
async def support_cb(call: CallbackQuery):
    uid = call.from_user.id
    action = (call.data or "").split(":")[1] if ":" in (call.data or "") else ""

    if action == "cancel":
        was_waiting = waiting_support_message.pop(uid, None) is not None
        with contextlib.suppress(Exception):
            await call.message.delete()  # экран поддержки убираем совсем, чтобы не висел в чате
        await call.answer(tr(uid, "✖️ Обращение отменено. Если понадобится помощь — /support.") if was_waiting else None)
        return

    if action == "open":  # кнопка «Ответить» под сообщением от администрации
        label = await resolve_user_label(call.bot, uid)
        store.set_user_label(uid, label)
        await call.answer()
        if call.message:
            await open_support(call.message, uid, label)
        return

    await call.answer()


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
    await message.answer(tr(message, SUPPORT_SENT_TEXT), parse_mode="HTML")


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
    await message.answer(tr(message, SUPPORT_SENT_TEXT), parse_mode="HTML")
