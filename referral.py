"""
Реферальная система + магазин подарков за баллы.

Логика формирования текстов и временное состояние (ожидание подтверждения
покупки) — здесь. Хендлеры команд/колбэков — в handlers/referral_commands.py
и handlers/referral_callbacks.py. Подарки выдаются вручную администрацией —
бот только ведёт учёт баллов, рефералов и заявок.
"""
import contextlib
import time
from typing import Dict, List, Optional

from config import (
    BOT_USERNAME,
    GIFTS,
    GIFTS_BY_KEY,
    REF_POINTS_PER_REFERRAL,
    REF_TOP_LIMIT,
    REFERRAL_LOG_CHANNEL_ID,
)
from helpers import html_escape, now_msk_str
from storage import store

# uid -> {"key": gift_key, "type": "stars"/"tickets", "to": recipient_id, "comment": str, "stage": str}
# Также используется как временное хранилище данных о покупке подарка за
# звёзды, пока пользователь не оплатит настоящий инвойс Telegram Stars —
# см. send_gift_stars_invoice / finalize_gift_stars_purchase ниже.
pending_gift_purchase: Dict[int, dict] = {}
PENDING_GIFT_TTL_SEC = 300

DIVIDER = "━━━━━━━━━━━━━━━━━━━━"


def ref_link(uid: int) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={uid}"


def gift_by_key(key: str) -> Optional[dict]:
    return GIFTS_BY_KEY.get(key)


def ref_menu_text(uid: int) -> str:
    rs = store.get_ref_stats(uid)
    return (
        "👥 <b>Реферальная система TikSaves</b>\n"
        f"{DIVIDER}\n\n"
        f"🎯 <b>Твой прогресс</b>\n"
        f"├ 👥 Приглашено друзей: <b>{rs['referrals_count']}</b>\n"
        f"└ 🎟 Баланс билетиков: <b>{rs['ref_points']}</b>\n\n"
        f"💡 <b>Как это работает?</b>\n"
        f"├ 1️⃣ Поделись своей ссылкой\n"
        f"├ 2️⃣ Друг установит бота и скачает видео\n"
        f"├ 3️⃣ Ты получишь <b>+{REF_POINTS_PER_REFERRAL} 🎟</b>\n"
        f"└ 4️⃣ Меняй баллы на подарки в магазине 🎁\n\n"
        f"🔗 <b>Твоя реф.ссылка (копируй и отправляй):</b>\n"
        f"<code>t.me/{BOT_USERNAME}?start={uid}</code>"
    )


def _gifts_grouped_by_price() -> List[tuple]:
    """Группирует каталог подарков по цене, сохраняя порядок появления."""
    order: List[int] = []
    groups: Dict[int, List[dict]] = {}
    for g in GIFTS:
        price = g["price"]
        groups.setdefault(price, []).append(g)
        if price not in order:
            order.append(price)
    return [(price, groups[price]) for price in order]


def gift_shop_text(uid: int) -> str:
    rs = store.get_ref_stats(uid)
    lines = [
        "🎁 <b>Магазин подарков</b>\n"
        f"{DIVIDER}\n",
        f"🎟 <b>Твой баланс:</b> <b>{rs['ref_points']}</b> билетиков\n",
        "Выбери подарок из списка ниже 👇\n",
        f"<b>💝 Цена каждого подарка:</b> <b>60⭐</b> или <b>500🎟</b>\n",
    ]
    lines.append(f"{DIVIDER}\n")
    names = "  •  ".join(f"{g['emoji']} {html_escape(g['name'])}" for g in GIFTS)
    lines.append(f"<b>Доступные подарки:</b>\n{names}")
    return "\n".join(lines)


def gift_confirm_text(gift: dict) -> str:
    return (
        "✨ <b>Подтверждение покупки подарка</b>\n"
        f"{DIVIDER}\n\n"
        f"🎁 Выбранный подарок:\n"
        f"   {gift['emoji']} <b>{html_escape(gift['name'])}</b>\n\n"
        f"💎 Стоимость: <b>{gift['price']} ⭐</b>\n"
        f"   или <b>{gift['price'] * 10}🎟</b> (билетиков)\n\n"
        "❗ <i>После подтверждения баллы/билетики спишутся!</i>\n"
        "Администрация обработает заявку вручную.\n\n"
        "✅ Готов(а) к покупке?"
    )


def gift_created_text(gift: dict) -> str:
    return (
        "🎉 <b>Заявка успешно создана!</b>\n"
        f"{DIVIDER}\n\n"
        f"🎁 Подарок: {gift['emoji']} <b>{html_escape(gift['name'])}</b>\n"
        f"💳 Списано: <b>{gift['price']}</b> баллов\n"
        f"📊 Статус: <b>⏳ Ожидает выдачи</b>\n\n"
        "👑 Администратор скоро обработает твою заявку.\n"
        "Спасибо за поддержку TikSaves! ❤️"
    )


_STATUS_LABELS = {
    "pending": "⏳ Ожидает выдачи",
    "completed": "✅ Выдан",
    "rejected": "❌ Отклонён",
}


def my_requests_text(uid: int) -> str:
    reqs = store.user_gift_requests(uid)
    if not reqs:
        return (
            "📦 <b>История заявок</b>\n"
            f"{DIVIDER}\n\n"
            "Пока пусто — загляни в 🎁 Магазин подарков и выбери что-нибудь!"
        )
    lines = ["📦 <b>История заявок</b>", f"{DIVIDER}\n"]
    for i, r in enumerate(reqs, start=1):
        g = gift_by_key(r.get("gift_key", "")) or {}
        emoji = g.get("emoji", "🎁")
        name = r.get("gift_name") or g.get("name", "?")
        status = _STATUS_LABELS.get(r.get("status", ""), str(r.get("status", "?")))
        lines.append(f"<b>{i}.</b> {emoji} {html_escape(name)} — {status}")
    return "\n".join(lines)


def top_referrers_text(uid: Optional[int] = None, *, limit: Optional[int] = None) -> str:
    top = store.top_referrers(limit or REF_TOP_LIMIT)
    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 <b>Топ рефереров TikSaves</b>", f"{DIVIDER}\n"]
    if not top:
        lines.append("Пока никто не пригласил ни одного друга — стань первым! 🚀")
    for i, (ref_uid, cnt) in enumerate(top):
        medal = medals[i] if i < 3 else f"<b>{i + 1}.</b>"
        label = store.get_user_label(ref_uid)
        lines.append(f"{medal} {html_escape(label)} — 👥 <b>{cnt}</b>")

    if uid is None:
        return "\n".join(lines).rstrip()

    rank = store.ref_rank(uid)
    rs = store.get_ref_stats(uid)
    lines.append("")
    if rank:
        lines.append(f"📍 <b>Твоё место:</b> #{rank} — 👥 {rs['referrals_count']} рефералов")
    else:
        lines.append(f"📍 <b>Твоё место:</b> пока нет рефералов (у тебя {rs['referrals_count']})")
    return "\n".join(lines)


HOW_IT_WORKS_TEXT = (
    "📖 <b>Как работает реферальная система</b>\n"
    f"{DIVIDER}\n\n"
    "1️⃣ Забери свою ссылку в /ref\n"
    "2️⃣ Отправь её друзьям\n"
    "3️⃣ Как только друг скачает первое видео — тебе:\n"
    f"    💎 <b>+{REF_POINTS_PER_REFERRAL} 🎟</b>\n"
    "4️⃣ Копи баллы и меняй их на подарки в магазине 🎁\n\n"
    "✋ Подарки выдаются вручную администрацией — обычно быстро."
)


def new_referral_notify_text(new_user_label: str, rs: Dict[str, int]) -> str:
    return (
        "🎉 <b>Новый реферал!</b>\n"
        f"{DIVIDER}\n\n"
        f"👤 {html_escape(new_user_label)} перешёл по твоей ссылке и скачал своё первое видео!\n\n"
        f"💎 Начислено: <b>+{REF_POINTS_PER_REFERRAL} 🎟</b>\n\n"
        f"👥 Всего рефералов: <b>{rs['referrals_count']}</b>\n"
        f"🎟 Баланс: <b>{rs['ref_points']}</b>"
    )


async def reward_referral_if_first_download(bot, uid: int, label: str) -> None:
    """
    Начисляет баллы пригласившему — только один раз, при первом успешном
    скачивании uid (не при простом /start). Общая логика для всех источников
    (TikTok/YouTube/Instagram/VK/Pinterest) — раньше дублировалась в каждом
    хендлере отдельно.
    """
    reward = store.try_reward_referral(uid, REF_POINTS_PER_REFERRAL)
    if not reward:
        return
    with contextlib.suppress(Exception):
        await bot.send_message(
            reward["referrer_id"],
            new_referral_notify_text(
                label, {"referrals_count": reward["referrals_count"], "ref_points": reward["ref_points"]}
            ),
            parse_mode="HTML",
        )


NUDGE_EVERY = 5  # раз в сколько скачиваний может сработать напоминание


async def _maybe_send_nudge(bot, uid: int) -> None:
    """
    Раз в NUDGE_EVERY любых скачиваний — ненавязчивое напоминание САМОМУ
    СКАЧАВШЕМУ (не рассылка всем!). Тип сообщения выбирается случайно из
    трёх: про рефералку, про донат, обычное общее — чтобы не заваливать
    только одной темой (раньше реферальное напоминание было отдельным и
    срабатывало в 10 раз чаще остальных двух).
    """
    import random
    from broadcast import REMINDER_MSG, DONATE_REMINDER_MSG, REFERRAL_REMINDER_MSG
    from helpers import to_html_simple

    total = store.bump_download_counter(uid)
    if total % NUDGE_EVERY != 0:
        return
    text = random.choice([REMINDER_MSG, DONATE_REMINDER_MSG, REFERRAL_REMINDER_MSG])
    with contextlib.suppress(Exception):
        await bot.send_message(uid, to_html_simple(text), parse_mode="HTML")


def _gift_invoice_payload(uid: int) -> str:
    """Уникальный payload инвойса покупки подарка звёздами — по префиксу
    'gift_buy_' successful_payment-хендлер отличает его от обычного доната."""
    return f"gift_buy_{uid}_{int(time.time() * 1000)}"


async def send_gift_stars_invoice(bot, uid: int, gift: dict) -> None:
    """Открывает НАСТОЯЩЕЕ окно оплаты Telegram Stars за подарок (как в
    /donate) — реальный инвойс на gift['price'] звёзд, а не списание
    виртуального баланса."""
    from aiogram.types import LabeledPrice

    await bot.send_invoice(
        chat_id=uid,
        title=f"{gift['emoji']} {gift['name']}",
        description=f"Покупка подарка «{gift['name']}» за {gift['price']} ⭐ в TikSaves",
        payload=_gift_invoice_payload(uid),
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=gift["name"], amount=int(gift["price"]))],
    )


async def finalize_gift_stars_purchase(message, buyer_uid: int, label: str) -> None:
    """Вызывается из хендлера successful_payment, когда payload инвойса
    начинается с 'gift_buy_' (см. _gift_invoice_payload) — то есть только что
    прошла реальная оплата Stars за подарок. Берёт отложенные данные о
    подарке/получателе/комментарии из pending_gift_purchase, создаёт заявку
    админу и сохраняет telegram_payment_charge_id — он нужен, чтобы можно
    было по-настоящему вернуть звёзды, если админ отклонит заявку.
    """
    from keyboards import gift_admin_kb

    from logging_channel import format_user_for_log

    charge_id = message.successful_payment.telegram_payment_charge_id
    stars = int(message.successful_payment.total_amount)
    pend = pending_gift_purchase.pop(buyer_uid, None)

    async def _refund() -> None:
        with contextlib.suppress(Exception):
            await message.bot.refund_star_payment(user_id=buyer_uid, telegram_payment_charge_id=charge_id)

    if not pend:
        # Не должны сюда попадать в норме, но звёзды платно списаны —
        # молча терять оплату нельзя, возвращаем их и сообщаем пользователю.
        await _refund()
        await message.answer(
            "⚠️ Не удалось определить, какой подарок вы покупали (истекло время ожидания).\n"
            "Звёзды автоматически возвращены. Оформите покупку заново в /ref.",
            parse_mode="HTML",
        )
        return

    gift = gift_by_key(pend.get("key", ""))
    if not gift:
        await _refund()
        await message.answer("⚠️ Этот подарок больше недоступен. Звёзды возвращены.", parse_mode="HTML")
        return

    recipient_id = int(pend.get("to") or buyer_uid)
    comment = (pend.get("comment") or "").strip()

    req_id = store.new_gift_request(
        buyer_uid,
        gift["key"],
        gift["name"],
        stars,
        payment_type="stars",
        recipient_id=recipient_id,
        gift_comment=comment,
        telegram_payment_charge_id=charge_id,
    )

    recipient_label = store.get_user_label(recipient_id)
    if recipient_id == buyer_uid:
        await message.answer(gift_created_text(gift), parse_mode="HTML")
    else:
        await message.answer(
            "✅ <b>Оплата прошла, заявка создана!</b>\n\n"
            f"🎁 Подарок: {gift['emoji']} {gift['name']}\n"
            f"⭐ Оплачено: {stars} звёзд\n"
            f"👤 Кому: {format_user_for_log(recipient_label, recipient_id)}\n"
            f"📊 Статус: <b>⏳ Ожидает выдачи</b>\n\n"
            "👑 Администратор скоро обработает заявку.",
            parse_mode="HTML",
        )

    admin_text = (
        "🎁 <b>Новая заявка на подарок (звёзды"
        + (", другому)</b>\n\n" if recipient_id != buyer_uid else ")</b>\n\n")
        + f"👤 От: {format_user_for_log(label, buyer_uid)}\n"
        + f"👤 Кому: {'Себе' if recipient_id == buyer_uid else format_user_for_log(recipient_label, recipient_id)}\n"
        + f"🎁 Подарок: {gift['emoji']} {gift['name']}\n"
        + f"⭐ Оплачено: {stars} звёзд (реальная оплата, автовыдача при одобрении)\n"
    )
    if comment:
        admin_text += f"💬 Комментарий: <i>{html_escape(comment)}</i>\n"
    admin_text += f"📅 {now_msk_str()}"

    with contextlib.suppress(Exception):
        await message.bot.send_message(
            REFERRAL_LOG_CHANNEL_ID,
            admin_text,
            parse_mode="HTML",
            reply_markup=gift_admin_kb(req_id),
        )


async def after_download_hooks(bot, uid: int, label: str) -> None:
    """
    Общие действия после ЛЮБОГО успешного скачивания (видео/фото, любой
    источник): начисление баллов рефереру (если это первое скачивание
    приглашённого) + периодическое персональное напоминание (раз в
    NUDGE_EVERY скачиваний, случайный выбор из трёх типов) — только тому,
    кто только что скачал, не рассылка всем.
    """
    await reward_referral_if_first_download(bot, uid, label)
    await _maybe_send_nudge(bot, uid)
