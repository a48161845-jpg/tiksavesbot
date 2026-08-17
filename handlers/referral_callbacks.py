"""
Callback-обработчики реферальной системы и магазина подарков:
- ref:*     — навигация по меню /ref (магазин, рефералы, заявки, топ, помощь, назад);
- gift:*    — выбор/подтверждение/отмена покупки подарка;
- admgift:* — админ выдал/отклонил заявку (кнопки под сообщением в лог-канале).
"""
import contextlib

from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.exceptions import TelegramBadRequest

from globals_state import dp
from config import REFERRAL_LOG_CHANNEL_ID, SUPPORT_USERNAME, log
from helpers import is_admin, code, now_msk_str, html_escape
from storage import store
from user_label import resolve_user_label
from gates import gate_callback
from logging_channel import format_user_for_log
from gift_states import GiftBuyStates
from referral import (
    pending_gift_purchase,
    ref_menu_text,
    gift_shop_text,
    gift_by_key,
    gift_confirm_text,
    gift_created_text,
    my_requests_text,
    top_referrers_text,
    HOW_IT_WORKS_TEXT,
    send_gift_stars_invoice,
)
from keyboards import (
    ref_menu_kb,
    ref_back_kb,
    gift_shop_kb,
    gift_confirm_kb,
    gift_admin_kb,
)


async def _safe_edit(call: CallbackQuery, text: str, kb) -> None:
    if not call.message:
        return
    with contextlib.suppress(Exception):
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query(F.data.startswith("ref:"))
async def ref_cb(call: CallbackQuery):
    uid = call.from_user.id
    label = await resolve_user_label(call.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_callback(call, label):
        return

    action = (call.data or "").split(":", 1)[-1]

    if action == "back":
        await _safe_edit(call, ref_menu_text(uid), ref_menu_kb())
        await call.answer()
        return

    if action == "shop":
        rs = store.get_ref_stats(uid)
        await _safe_edit(call, gift_shop_text(uid), gift_shop_kb(rs["ref_points"]))
        await call.answer()
        return

    if action == "myrequests":
        await _safe_edit(call, my_requests_text(uid), ref_back_kb())
        await call.answer()
        return

    if action == "top":
        await _safe_edit(call, top_referrers_text(uid), ref_back_kb())
        await call.answer()
        return

    if action == "howitworks":
        await _safe_edit(call, HOW_IT_WORKS_TEXT, ref_back_kb())
        await call.answer()
        return

    await call.answer()


@dp.callback_query(F.data.startswith("gift:"))
async def gift_cb(call: CallbackQuery):
    uid = call.from_user.id
    label = await resolve_user_label(call.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_callback(call, label):
        return

    parts = (call.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""

    # gift:buy:KEY — выбор подарка, теперь показываем выбор: звёзды или билеты
    if action == "buy":
        key = parts[2] if len(parts) > 2 else ""
        gift = gift_by_key(key)
        if not gift:
            await call.answer("❌ Такого подарка нет.", show_alert=True)
            return
        
        # Сохраняем выбранный подарок
        pending_gift_purchase[uid] = {"key": key, "stage": "choose_currency"}
        
        # Показываем выбор: звёзды (на себя или другому) или билеты (только себе)
        text = (
            f"🎁 <b>{gift['emoji']} {gift['name']}</b>\n\n"
            f"<b>Выбери способ покупки:</b>\n\n"
            f"⭐ <b>За звёзды ({gift['price']}⭐)</b>\n"
            f"   → Можешь подарить себе или другому\n\n"
            f"🎟 <b>За билеты ({gift['price'] * 10}🎟)</b>\n"
            f"   → Только себе (приятного пользования!)"
        )
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ За звёзды", callback_data=f"gift:pay_stars:{key}"),
                InlineKeyboardButton(text="🎟 За билеты", callback_data=f"gift:pay_tickets:{key}"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="gift:cancel")],
        ])
        await _safe_edit(call, text, kb)
        await call.answer()
        return

    # gift:pay_stars:KEY — выбор звёзды (реальная оплата Telegram Stars,
    # как в /donate) — спрашиваем кому дарить
    if action == "pay_stars":
        key = parts[2] if len(parts) > 2 else ""
        gift = gift_by_key(key)
        if not gift:
            await call.answer("❌ Такого подарка нет.", show_alert=True)
            return

        # Оплата звёздами — это НАСТОЯЩИЙ платёж через Telegram Stars,
        # а не списание виртуального баланса, поэтому баланс не проверяем.

        # Спрашиваем кому дарить
        text = (
            f"🎁 <b>{gift['emoji']} {gift['name']}</b>\n\n"
            f"<b>Кому подарить?</b>\n\n"
            f"⭐ Стоимость: {gift['price']} звёзд"
        )
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🙋 Себе", callback_data=f"gift:stars_self:{key}"),
                InlineKeyboardButton(text="👥 Другому", callback_data=f"gift:stars_other:{key}"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"gift:buy:{key}")],
        ])
        pending_gift_purchase[uid] = {"key": key, "type": "stars", "stage": "choose_recipient"}
        await _safe_edit(call, text, kb)
        await call.answer()
        return

    # gift:pay_tickets:KEY — билеты, только себе
    if action == "pay_tickets":
        key = parts[2] if len(parts) > 2 else ""
        gift = gift_by_key(key)
        if not gift:
            await call.answer("❌ Такого подарка нет.", show_alert=True)
            return
        
        rs = store.get_ref_stats(uid)
        ticket_price = gift["price"] * 10
        if rs["ref_points"] < ticket_price:
            await call.answer(
                f"❌ Недостаточно билетиков: нужно {ticket_price} 🎟, у тебя {rs['ref_points']} 🎟",
                show_alert=True,
            )
            return
        
        # Подтверждение для билетов (только себе)
        text = (
            f"🎁 <b>{gift['emoji']} {gift['name']}</b>\n\n"
            f"<b>Подтверждение покупки</b>\n\n"
            f"🎟 Стоимость: {ticket_price} билетиков\n"
            f"👤 Получатель: Ты\n"
            f"💬 Текст: <i>Приятного пользования ботом! ❤️</i>"
        )
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"gift:confirm_tickets:{key}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"gift:buy:{key}"),
            ],
        ])
        pending_gift_purchase[uid] = {"key": key, "type": "tickets", "stage": "confirm"}
        await _safe_edit(call, text, kb)
        await call.answer()
        return

    # gift:stars_self:KEY — звёзды, себе
    if action == "stars_self":
        key = parts[2] if len(parts) > 2 else ""
        gift = gift_by_key(key)
        if not gift:
            await call.answer("❌ Такого подарка нет.", show_alert=True)
            return
        
        text = (
            f"🎁 <b>{gift['emoji']} {gift['name']}</b>\n\n"
            f"<b>Подтверждение покупки</b>\n\n"
            f"⭐ Стоимость: {gift['price']} звёзд (оплата Telegram Stars)\n"
            f"👤 Получатель: Ты\n"
            f"💬 Текст: <i>Спасибо за использование @tiksavesbot</i>"
        )
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Оплатить звёздами", callback_data=f"gift:confirm_stars_self:{key}"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"gift:pay_stars:{key}"),
            ],
        ])
        pending_gift_purchase[uid] = {"key": key, "type": "stars", "to": uid, "comment": "", "stage": "confirm"}
        await _safe_edit(call, text, kb)
        await call.answer()
        return

    # gift:stars_other:KEY — звёзды, другому, запрашиваем ID/username и текст через FSM
    if action == "stars_other":
        key = parts[2] if len(parts) > 2 else ""
        gift = gift_by_key(key)
        if not gift:
            await call.answer("❌ Такого подарка нет.", show_alert=True)
            return

        # Оплата звёздами — реальный платёж, баланс билетиков тут не при чём.

        # Инициируем FSM для ввода получателя. ВАЖНО: ключ хранилища FSM должен
        # быть настоящим StorageKey (bot_id/chat_id/user_id) — именно такой
        # ключ дальше строит aiogram при обработке следующего текстового
        # сообщения от пользователя. Раньше здесь передавалась обычная строка
        # f"user:{uid}", которая не совпадала с реальным ключом диспетчера,
        # поэтому состояние никогда не находилось и бот не реагировал на
        # введённый ID/username получателя.
        chat_id = call.message.chat.id if call.message else uid
        state = FSMContext(
            storage=dp.storage,
            key=StorageKey(bot_id=call.bot.id, chat_id=chat_id, user_id=uid),
        )
        await state.update_data(gift_key=key)
        await state.set_state(GiftBuyStates.enter_recipient)
        
        text = (
            "👥 <b>Введи ID или username получателя</b>\n\n"
            "Напиши в чате:\n"
            "• <code>ID</code> (например: 123456789)\n"
            "• <code>@username</code> (например: @user123)"
        )
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"gift:pay_stars:{key}")],
        ])
        await _safe_edit(call, text, kb)
        await call.answer()
        return

    if action == "cancel":
        pending_gift_purchase.pop(uid, None)
        await _safe_edit(call, ref_menu_text(uid), ref_menu_kb())
        await call.answer("Отменено.")
        return

    # gift:confirm_stars_self:KEY — подтверждение покупки себе за звёзды:
    # открываем НАСТОЯЩИЙ инвойс Telegram Stars (как в /donate). Заявка
    # создаётся только после реальной оплаты — см.
    # referral.finalize_gift_stars_purchase, вызывается из successful_payment.
    if action == "confirm_stars_self":
        key = parts[2] if len(parts) > 2 else ""
        pend = pending_gift_purchase.get(uid, {})
        gift = gift_by_key(key)
        if pend.get("key") != key or not gift:
            await call.answer("⏱️ Запрос устарел, начни заново.", show_alert=True)
            return

        pending_gift_purchase[uid] = {"key": key, "type": "stars", "to": uid, "comment": "", "stage": "await_payment"}
        await call.answer()
        await send_gift_stars_invoice(call.bot, uid, gift)
        return

    # gift:confirm_tickets:KEY — подтверждение билетов себе
    if action == "confirm_tickets":
        key = parts[2] if len(parts) > 2 else ""
        pend = pending_gift_purchase.get(uid, {})
        gift = gift_by_key(key)
        if pend.get("key") != key or not gift:
            await call.answer("⏱️ Запрос устарел.", show_alert=True)
            return
        
        ticket_price = gift["price"] * 10
        rs = store.get_ref_stats(uid)
        if rs["ref_points"] < ticket_price:
            await call.answer("❌ Недостаточно билетиков.", show_alert=True)
            pending_gift_purchase.pop(uid, None)
            return
        
        pending_gift_purchase.pop(uid, None)
        store.add_ref_points_delta(uid, -ticket_price)
        req_id = store.new_gift_request(uid, gift["key"], gift["name"], ticket_price, payment_type="tickets", recipient_id=uid)

        await _safe_edit(call, gift_created_text(gift), ref_back_kb())
        await call.answer("✅ Заявка создана!")

        # Отправляем админу на одобрение
        admin_text = (
            "🎁 <b>Новая заявка на подарок (билеты)</b>\n\n"
            f"👤 От: {format_user_for_log(label, uid)}\n"
            f"👤 Кому: Себе\n"
            f"🎁 Подарок: {gift['emoji']} {gift['name']}\n"
            f"🎟 Стоимость: {ticket_price} билетиков\n"
            f"📅 {now_msk_str()}"
        )
        with contextlib.suppress(Exception):
            await call.bot.send_message(
                REFERRAL_LOG_CHANNEL_ID,
                admin_text,
                parse_mode="HTML",
                reply_markup=gift_admin_kb(req_id),
            )
        return

    await call.answer()


@dp.callback_query(F.data.startswith("admgift:"))
async def admin_gift_cb(call: CallbackQuery):
    admin_id = call.from_user.id
    admin_label = await resolve_user_label(call.bot, admin_id)
    store.set_user_label(admin_id, admin_label)

    if not is_admin(admin_id):
        await call.answer("Только для администрации.", show_alert=True)
        return

    parts = (call.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""
    req_id_str = parts[2] if len(parts) > 2 else ""
    if not req_id_str.isdigit():
        await call.answer("❌ Ошибка заявки.", show_alert=True)
        return
    req_id = int(req_id_str)

    req = store.get_gift_request(req_id)
    if not req:
        await call.answer("❌ Заявка не найдена.", show_alert=True)
        return
    if req.get("status") != "pending":
        await call.answer("Заявка уже обработана.", show_alert=True)
        return

    target_uid = int(req["user_id"])
    gift = gift_by_key(req.get("gift_key", "")) or {"emoji": "🎁", "name": req.get("gift_name", "?")}
    target_label = store.get_user_label(target_uid)
    base_text = (call.message.html_text or call.message.text or "") if call.message else ""

    if action == "ok":
        recipient_id = int(req.get("recipient_id", target_uid))
        payment_type = req.get("payment_type", "tickets")
        gift_comment = req.get("gift_comment", "")
        gift_tg_id = gift.get("tg_id")

        # Автоматическая выдача: бот сам отправляет настоящий Telegram-подарок
        # получателю, списывая звёзды со своего собственного баланса —
        # админ не должен вручную покупать/дарить подарок из клиента.
        delivered = False
        deliver_error = None
        if gift_tg_id:
            try:
                gift_text = None
                if gift_comment:
                    gift_text = gift_comment[:120]
                await call.bot.send_gift(
                    user_id=recipient_id,
                    gift_id=gift_tg_id,
                    text=gift_text,
                    pay_for_upgrade=False,
                )
                delivered = True
            except TelegramBadRequest as e:
                deliver_error = str(e)
            except Exception as e:
                deliver_error = str(e)

        if gift_tg_id and not delivered:
            # Не смогли выдать автоматически (например, не хватает звёзд на
            # балансе бота) — заявку НЕ закрываем, чтобы админ мог пополнить
            # баланс бота и нажать «✅ Выдать» ещё раз.
            log.error("send_gift failed for req_id=%s uid=%s: %s", req_id, recipient_id, deliver_error)
            await call.answer(f"❌ Не удалось выдать автоматически: {deliver_error or 'ошибка API'}", show_alert=True)
            with contextlib.suppress(Exception):
                await call.bot.send_message(
                    REFERRAL_LOG_CHANNEL_ID,
                    "⚠️ <b>Не удалось автоматически выдать подарок</b>\n\n"
                    f"🎁 {gift['emoji']} {gift['name']}\n"
                    f"👤 Кому: {format_user_for_log(store.get_user_label(recipient_id), recipient_id)}\n"
                    f"❗ Ошибка: <code>{html_escape(deliver_error or '')}</code>\n\n"
                    "Пополните баланс звёзд бота и нажмите «✅ Выдать» ещё раз — заявка осталась в ожидании.",
                    parse_mode="HTML",
                )
            return

        store.set_gift_request_status(req_id, "completed")

        # Формируем текст в зависимости от типа платежа и получателя
        if recipient_id == target_uid:
            # Покупатель дарит себе
            if payment_type == "tickets":
                send_text = (
                    f"🎉 <b>Подарок выдан!</b>\n\n"
                    f"🎁 {gift['emoji']} {gift['name']}\n\n"
                    f"<i>Приятного пользования ботом! ❤️</i>"
                )
            else:  # stars
                send_text = (
                    f"🎉 <b>Подарок выдан!</b>\n\n"
                    f"🎁 {gift['emoji']} {gift['name']}\n\n"
                    f"<i>Спасибо за использование @tiksavesbot</i>"
                )
        else:
            # Покупатель дарит другому
            send_text = (
                f"🎁 <b>Тебе подарили подарок!</b>\n\n"
                f"🎁 {gift['emoji']} {gift['name']}\n\n"
                f"👤 От: {format_user_for_log(target_label, target_uid)}"
            )
            if gift_comment:
                send_text += f"\n💬 Сообщение:\n<i>{html_escape(gift_comment)}</i>"
            send_text += f"\n\n💡 <i>Пиши /start в боте, если ещё не начинал(а) с ним общение</i>"

        # Если настоящий Telegram-подарок уже отправлен через send_gift выше,
        # получатель и так увидит его в чате с ботом — это сообщение просто
        # добавляет контекст (от кого, комментарий и т.п.), не дублируя выдачу.
        with contextlib.suppress(Exception):
            await call.bot.send_message(recipient_id, send_text, parse_mode="HTML")
        
        with contextlib.suppress(Exception):
            if call.message:
                await call.message.edit_text(base_text + "\n\n✅ <b>ВЫДАНО АВТОМАТИЧЕСКИ</b>", parse_mode="HTML", reply_markup=None)
        await call.answer("✅ Подарок выдан автоматически.")

        log_text = (
            "✅ <b>Подарок выдан автоматически</b>\n\n"
            f"👤 От: {format_user_for_log(target_label, target_uid)}\n"
            f"👤 Кому: {format_user_for_log(store.get_user_label(recipient_id), recipient_id)}\n"
            f"🎁 {gift['emoji']} {gift['name']}\n\n"
            f"👑 Одобрил(а):\n{format_user_for_log(admin_label, admin_id)}"
        )
        with contextlib.suppress(Exception):
            await call.bot.send_message(REFERRAL_LOG_CHANNEL_ID, log_text, parse_mode="HTML")
        return

    if action == "no":
        store.set_gift_request_status(req_id, "rejected")
        price = int(req.get("gift_price", 0))
        payment_type = req.get("payment_type", "tickets")  # По умолчанию билеты

        if payment_type == "stars":
            # Реальная оплата Stars — делаем настоящий возврат через Bot API,
            # а не зачисление виртуального баланса.
            charge_id = req.get("telegram_payment_charge_id") or ""
            refunded = False
            if charge_id:
                try:
                    await call.bot.refund_star_payment(user_id=target_uid, telegram_payment_charge_id=charge_id)
                    refunded = True
                except Exception as e:
                    log.error("refund_star_payment failed req_id=%s uid=%s: %s", req_id, target_uid, e)

            if refunded:
                user_text = (
                    "❌ <b>Заявка отклонена</b>\n\n"
                    "К сожалению, ваша заявка была отклонена.\n\n"
                    f"🎁 Подарок:\n{gift['emoji']} {gift['name']}\n\n"
                    f"⭐ Возвращено: +{price} звёзд (возврат Telegram Stars)"
                )
                answer_text = "❌ Заявка отклонена, звёзды возвращены."
                log_refund_line = f"⭐ Возвращено: {price} звёзд (реальный возврат)"
            else:
                user_text = (
                    "❌ <b>Заявка отклонена</b>\n\n"
                    "К сожалению, ваша заявка была отклонена.\n\n"
                    f"🎁 Подарок:\n{gift['emoji']} {gift['name']}\n\n"
                    f"⚠️ Не удалось автоматически вернуть {price} ⭐ — "
                    f"напишите в поддержку {SUPPORT_USERNAME}, звёзды будут возвращены вручную."
                )
                answer_text = "⚠️ Заявка отклонена, но авто-возврат звёзд не удался — см. лог."
                log_refund_line = f"⚠️ Возврат {price} ⭐ НЕ выполнен автоматически — нужен ручной возврат"

            with contextlib.suppress(Exception):
                await call.bot.send_message(target_uid, user_text, parse_mode="HTML")
            with contextlib.suppress(Exception):
                if call.message:
                    await call.message.edit_text(base_text + "\n\n❌ <b>ОТКЛОНЕНО</b>", parse_mode="HTML", reply_markup=None)
            await call.answer(answer_text)

            log_text = (
                "❌ <b>Заявка отклонена</b>\n\n"
                f"👤 {format_user_for_log(target_label, target_uid)}\n\n"
                f"🎁 {gift['emoji']} {gift['name']}\n\n"
                f"{log_refund_line}"
            )
            with contextlib.suppress(Exception):
                await call.bot.send_message(REFERRAL_LOG_CHANNEL_ID, log_text, parse_mode="HTML")
            return

        # payment_type == "tickets" — виртуальный баланс, как и раньше
        new_balance = store.add_ref_points_delta(target_uid, price)
        with contextlib.suppress(Exception):
            await call.bot.send_message(
                target_uid,
                "❌ <b>Заявка отменена</b>\n\n"
                "К сожалению, ваша заявка была отклонена.\n\n"
                f"🎁 Подарок:\n{gift['emoji']} {gift['name']}\n\n"
                f"🎟 Возвращено:\n+{price} билетиков\n\n"
                f"Текущий баланс:\n{new_balance} 🎟",
                parse_mode="HTML",
            )
        with contextlib.suppress(Exception):
            if call.message:
                await call.message.edit_text(base_text + "\n\n❌ <b>ОТКЛОНЕНО</b>", parse_mode="HTML", reply_markup=None)
        await call.answer("❌ Заявка отклонена, билетики возвращены.")

        log_text = (
            "❌ <b>Заявка отклонена</b>\n\n"
            f"👤 {format_user_for_log(target_label, target_uid)}\n\n"
            f"🎁 {gift['emoji']} {gift['name']}\n\n"
            f"Возвращено:\n{price} 🎟"
        )
        with contextlib.suppress(Exception):
            await call.bot.send_message(REFERRAL_LOG_CHANNEL_ID, log_text, parse_mode="HTML")
        return

    await call.answer()
