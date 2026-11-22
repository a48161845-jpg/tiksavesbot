"""
💎 TikSaves Premium — платная подписка за Telegram Stars.

  • premium:open       — экран с описанием и тарифами (из /donate, из кнопок под файлами и из напоминаний);
  • premium:buy:<дней> — счёт на оплату Stars (payload «premium:<дней>»);
  • оплату обрабатывает handlers/donate_callbacks.py (pre_checkout + successful_payment);
  • /paysupport        — обязательная для ботов с платежами команда: куда писать, если оплата не прошла.
Что даёт Premium: лимиты ×PREMIUM_LIMIT_MULT (core/limiters.py), нет напоминаний о донате (core/download_nudge.py),
значок 💎 в /me.
"""
from aiogram import F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, LinkPreviewOptions, Message

from core.config import PREMIUM_LIMIT_MULT, PREMIUM_PLANS
from core.donate import safe_edit
from core.gates import gate_callback
from core.globals_state import dp
from core.helpers import fmt_date_msk as fmt_date
from core.storage import store
from core.user_label import resolve_user_label
from i18n import get_lang, tr
from ui.keyboards import PREMIUM_TEXT, premium_kb

PAYSUPPORT_TEXT = "💳 <b>Вопросы по оплате</b>\nЕсли платёж не прошёл или нужен возврат — напиши в /support и укажи сумму и время платежа."

def plan_price(days: int):
    """Цена тарифа в ⭐ или None, если такого тарифа нет."""
    return next((st for d, st in PREMIUM_PLANS if d == days), None)


def premium_screen(uid: int) -> str:
    text = tr(uid, PREMIUM_TEXT, m=PREMIUM_LIMIT_MULT)
    if store.is_premium(uid):
        text = tr(uid, "💎 Premium активен до {date}", date=fmt_date(store.premium_until(uid))) + "\n\n" + text
    return text


@dp.callback_query(F.data.startswith("premium:"))
async def premium_cb(call: CallbackQuery):
    uid = call.from_user.id
    label = await resolve_user_label(call.bot, uid)
    store.set_user_label(uid, label)
    if not await gate_callback(call, label):
        return

    parts = (call.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "open":
        text, kb = premium_screen(uid), premium_kb(get_lang(uid))
        if call.message and call.message.text:  # из текстового меню — редактируем на месте
            await safe_edit(call, text, kb)
        elif call.message:  # из кнопок под фото/видео редактировать нельзя — новое сообщение
            await call.message.answer(text, parse_mode="HTML", reply_markup=kb,
                                      link_preview_options=LinkPreviewOptions(is_disabled=True))
        await call.answer()
        return

    if action == "buy":
        try:
            days = int(parts[2])
        except (IndexError, ValueError):
            days = 0
        stars = plan_price(days)
        if stars is None:
            await call.answer(tr(uid, "❌ Ошибка суммы"), show_alert=True)
            return
        await call.answer()
        lang = get_lang(uid)
        await call.bot.send_invoice(
            chat_id=uid,
            title=tr(lang, "💎 TikSaves Premium"),
            description=tr(lang, "Premium на {days} дн.: лимиты ×{m}, без напоминаний о донате, значок 💎", days=days, m=PREMIUM_LIMIT_MULT),
            payload=f"premium:{days}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=tr(lang, "Premium"), amount=stars)],
        )
        return

    await call.answer()


@dp.message(Command("paysupport"))
async def paysupport_cmd(message: Message):
    await message.answer(tr(message, PAYSUPPORT_TEXT), parse_mode="HTML")
