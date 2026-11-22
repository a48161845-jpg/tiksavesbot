"""
Команда /ref — главное меню реферальной системы и магазина подарков.
Команда /buy — быстрый доступ к магазину мишек за звёзды.
"""
from aiogram.filters import Command
from aiogram.types import Message

from core.globals_state import dp
from core.storage import store
from core.user_label import resolve_user_label
from core.gates import gate_message
from legacy.referral import ref_menu_text, gift_shop_text
from ui.keyboards import ref_menu_kb, gift_shop_kb


@dp.message(Command("ref"))
async def ref_cmd(message: Message):
    uid = message.from_user.id
    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_message(message, label):
        return

    await message.answer(ref_menu_text(uid), parse_mode="HTML", reply_markup=ref_menu_kb())


@dp.message(Command("buy"))
async def buy_cmd(message: Message):
    """Быстрый доступ к магазину мишек за звёзды."""
    uid = message.from_user.id
    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_message(message, label):
        return

    rs = store.get_ref_stats(uid)
    await message.answer(gift_shop_text(uid), parse_mode="HTML", reply_markup=gift_shop_kb(rs["ref_points"]))
