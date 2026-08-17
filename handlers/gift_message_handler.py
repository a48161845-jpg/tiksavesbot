"""
Обработчик сообщений при покупке подарка за звёзды другому пользователю.
- Получение ID/username получателя
- Получение опционального комментария
"""
from aiogram import F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from globals_state import dp
from gift_states import GiftBuyStates
from storage import store
from user_label import resolve_user_label
from gates import gate_message
from referral import gift_by_key, pending_gift_purchase, send_gift_stars_invoice
from logging_channel import format_user_for_log


@dp.message(GiftBuyStates.enter_recipient)
async def gift_enter_recipient(message: Message, state: FSMContext):
    """Получаем ID или username получателя подарка."""
    uid = message.from_user.id
    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_message(message, label):
        await state.clear()
        return

    data = await state.get_data()
    gift_key = data.get("gift_key")
    gift = gift_by_key(gift_key)
    if not gift:
        await message.answer("❌ Подарок больше недоступен.")
        await state.clear()
        return

    recipient_arg = (message.text or "").strip()
    recipient_id = None

    # Парсим ID или @username
    if recipient_arg.isdigit():
        recipient_id = int(recipient_arg)
    elif recipient_arg.startswith("@"):
        # Ищем по username
        username_clean = recipient_arg[1:]
        # Ищем в хранилище пользователей
        users_map = store.data.get("users_info", {})
        for uid_str, info in users_map.items():
            if (info or {}).get("username", "").lower() == username_clean.lower():
                recipient_id = int(uid_str)
                break

    if not recipient_id:
        await message.answer(
            "❌ Пользователь не найден.\n\n"
            "Попробуй:\n"
            "• Ввести ID (например: 123456789)\n"
            "• Ввести username с @ (например: @username)"
        )
        return

    # Проверяем, что пользователь существует в боте. get_user_label() тут не
    # годится — она всегда возвращает непустую строку (с фолбэком на сам id),
    # поэтому раньше эта проверка никогда не срабатывала.
    if not store.user_exists(recipient_id):
        await message.answer(
            "❌ Этот пользователь не использовал бота.\n\n"
            "Получатель должен хотя бы раз написать /start в боте."
        )
        return

    recipient_label = store.get_user_label(recipient_id)

    # Сохраняем recipient_id и переходим к ввод комментария
    await state.update_data(recipient_id=recipient_id)
    await state.set_state(GiftBuyStates.enter_comment)

    await message.answer(
        f"✅ Получатель: {format_user_for_log(recipient_label, recipient_id)}\n\n"
        f"📝 <b>Напиши комментарий</b> (или пиши \"без\" чтобы без комментария):\n\n"
        f"<i>Например: \"Привет, это подарок от меня! 🎉\"</i>",
        parse_mode="HTML",
    )


@dp.message(GiftBuyStates.enter_comment)
async def gift_enter_comment(message: Message, state: FSMContext):
    """Получаем комментарий и открываем оплату звёздами."""
    uid = message.from_user.id
    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_message(message, label):
        await state.clear()
        return

    data = await state.get_data()
    gift_key = data.get("gift_key")
    recipient_id = data.get("recipient_id")
    gift = gift_by_key(gift_key)

    if not gift or not recipient_id:
        await message.answer("❌ Запрос устарел. Попробуй заново.")
        await state.clear()
        return

    comment = (message.text or "").strip()
    if comment.lower() == "без":
        comment = ""

    # Дарение другому — тоже реальная оплата Telegram Stars, а не списание
    # виртуального баланса. Заявка создаётся только после успешной оплаты —
    # см. referral.finalize_gift_stars_purchase (вызывается из
    # handlers/donate_callbacks.py::payment_ok при payload "gift_buy_").
    pending_gift_purchase[uid] = {
        "key": gift["key"],
        "type": "stars",
        "to": int(recipient_id),
        "comment": comment,
        "stage": "await_payment",
    }
    await state.clear()

    recipient_label = store.get_user_label(recipient_id)
    await message.answer(
        f"✅ Получатель: {format_user_for_log(recipient_label, recipient_id)}\n\n"
        f"⭐ Осталось оплатить {gift['price']} звёзд — открываю оплату…",
        parse_mode="HTML",
    )
    await send_gift_stars_invoice(message.bot, uid, gift)
