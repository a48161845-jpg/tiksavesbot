"""
Реферальная система + магазин подарков за баллы.

Логика формирования текстов и временное состояние
(ожидание подтверждения покупки) — здесь.
Хендлеры команд/колбэков — в handlers/referral_commands.py
и handlers/referral_callbacks.py.

Подарки выдаются вручную администрацией —
бот только ведёт учёт баллов, рефералов и заявок.
"""

import contextlib
from typing import Dict, List, Optional

from aiogram.types import MessageEntity

from config import (
    BOT_USERNAME,
    GIFTS,
    GIFTS_BY_KEY,
    REF_POINTS_PER_REFERRAL,
    REF_TOP_LIMIT,
)
from helpers import html_escape
from storage import store


# uid -> gift_key: ждём подтверждения покупки этого подарка
pending_gift_purchase: Dict[int, str] = {}

PENDING_GIFT_TTL_SEC = 300

DIVIDER = "━━━━━━━━━━━━━━━━━━━━"


def ref_link(uid: int) -> str:
    return f"https://t.me/{BOT_USERNAME}?start={uid}"


def gift_by_key(key: str) -> Optional[dict]:
    return GIFTS_BY_KEY.get(key)


def ref_menu_text(uid: int) -> str:
    rs = store.get_ref_stats(uid)

    return (
        "🎁 <b>Реферальная система TikSaves</b>\n"
        f"{DIVIDER}\n\n"
        f"👥 Приглашено друзей: <b>{rs['referrals_count']}</b>\n"
        f"🎟 Баланс: <b>{rs['ref_points']}</b> баллов\n\n"
        "Зови друзей и копи баллы на подарки — просто скидывай свою ссылку 👇\n\n"
        f"💎 За каждого активного друга: <b>+{REF_POINTS_PER_REFERRAL} 🎟</b>\n"
        "<i>(баллы начисляются, как только друг скачает своё первое видео)</i>\n\n"
        "🔗 <b>Твоя ссылка:</b>\n"
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


def gift_shop_text(uid: int) -> tuple[str, list[MessageEntity]]:
    """
    Формирует текст магазина и entities для Premium Custom Emoji.
    """

    rs = store.get_ref_stats(uid)

    lines = [
        "🎁 <b>Магазин подарков</b>",
        f"{DIVIDER}\n",
        f"🎟 Твой баланс: <b>{rs['ref_points']}</b>\n",
        "Выбирай подарок — жми кнопку ниже 👇\n",
    ]

    text = "\n".join(lines) + "\n"

    entities: list[MessageEntity] = []

    for price, gifts in _gifts_grouped_by_price():

        text += f"<b>{price} 🎟</b>\n"

        for index, gift in enumerate(gifts):

            emoji = gift.get("emoji", "")
            name = html_escape(gift.get("name", "?"))

            # Позиция emoji в UTF-16
            offset = len(text.encode("utf-16-le")) // 2

            text += f"{emoji} {name}"

            emoji_length = len(emoji.encode("utf-16-le")) // 2

            custom_emoji_id = gift.get("custom_emoji_id")

            if custom_emoji_id:
                entities.append(
                    MessageEntity(
                        type="custom_emoji",
                        offset=offset,
                        length=emoji_length,
                        custom_emoji_id=str(custom_emoji_id),
                    )
                )

            if index < len(gifts) - 1:
                text += "  •  "

        text += "\n\n"

    return text.rstrip(), entities


def gift_confirm_text(
    gift: dict,
) -> tuple[str, list[MessageEntity]]:
    """
    Текст подтверждения покупки + Premium Custom Emoji.
    """

    emoji = gift.get("emoji", "")
    name = html_escape(gift.get("name", "?"))

    text = (
        "🧾 <b>Подтверждение покупки</b>\n"
        f"{DIVIDER}\n\n"
        f"🎁 Подарок: {emoji} <b>{name}</b>\n"
        f"🎟 Стоимость: <b>{gift['price']}</b> баллов\n\n"
        "После подтверждения баллы спишутся, а заявку обработает "
        "администрация вручную.\n\n"
        "Продолжаем? 👇"
    )

    entities = []

    # Ищем emoji именно после "Подарок: "
    marker = "🎁 Подарок: "
    pos = text.find(marker)

    if pos != -1:
        emoji_offset = pos + len(marker)

        offset = len(text[:emoji_offset].encode("utf-16-le"))
        length = len(emoji.encode("utf-16-le")) // 2

        custom_emoji_id = gift.get("custom_emoji_id")

        if custom_emoji_id:
            entities.append(
                MessageEntity(
                    type="custom_emoji",
                    offset=offset,
                    length=length,
                    custom_emoji_id=str(custom_emoji_id),
                )
            )

    return text, entities


def gift_created_text(
    gift: dict,
) -> tuple[str, list[MessageEntity]]:
    """
    Текст после создания заявки + Premium Custom Emoji.
    """

    emoji = gift.get("emoji", "")
    name = html_escape(gift.get("name", "?"))

    text = (
        "✅ <b>Заявка создана!</b>\n"
        f"{DIVIDER}\n\n"
        f"🎁 Подарок: {emoji} <b>{name}</b>\n"
        f"🎟 Списано: <b>{gift['price']}</b> баллов\n"
        "📌 Статус: <b>⏳ ожидает выдачи</b>\n\n"
        "Администратор скоро обработает заявку.\n"
        "Спасибо, что помогаешь развивать TikSaves ❤️"
    )

    entities = []

    marker = "🎁 Подарок: "
    pos = text.find(marker)

    if pos != -1:
        emoji_offset = pos + len(marker)

        offset = len(text[:emoji_offset].encode("utf-16-le"))
        length = len(emoji.encode("utf-16-le")) // 2

        custom_emoji_id = gift.get("custom_emoji_id")

        if custom_emoji_id:
            entities.append(
                MessageEntity(
                    type="custom_emoji",
                    offset=offset,
                    length=length,
                    custom_emoji_id=str(custom_emoji_id),
                )
            )

    return text, entities


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

    lines = [
        "📦 <b>История заявок</b>",
        f"{DIVIDER}\n",
    ]

    for i, r in enumerate(reqs, start=1):
        g = gift_by_key(r.get("gift_key", "")) or {}

        emoji = g.get("emoji", "🎁")
        name = r.get("gift_name") or g.get("name", "?")
        status = _STATUS_LABELS.get(
            r.get("status", ""),
            str(r.get("status", "?")),
        )

        lines.append(
            f"<b>{i}.</b> {emoji} {html_escape(name)} — {status}"
        )

    return "\n".join(lines)


def top_referrers_text(
    uid: Optional[int] = None,
    *,
    limit: Optional[int] = None,
) -> str:

    top = store.top_referrers(limit or REF_TOP_LIMIT)

    medals = ["🥇", "🥈", "🥉"]

    lines = [
        "🏆 <b>Топ рефереров TikSaves</b>",
        f"{DIVIDER}\n",
    ]

    if not top:
        lines.append(
            "Пока никто не пригласил ни одного друга — стань первым! 🚀"
        )

    for i, (ref_uid, cnt) in enumerate(top):

        medal = medals[i] if i < 3 else f"<b>{i + 1}.</b>"

        label = store.get_user_label(ref_uid)

        lines.append(
            f"{medal} {html_escape(label)} — 👥 <b>{cnt}</b>"
        )

    if uid is None:
        return "\n".join(lines).rstrip()

    rank = store.ref_rank(uid)
    rs = store.get_ref_stats(uid)

    lines.append("")

    if rank:
        lines.append(
            f"📍 <b>Твоё место:</b> #{rank} — "
            f"👥 {rs['referrals_count']} рефералов"
        )
    else:
        lines.append(
            f"📍 <b>Твоё место:</b> пока нет рефералов "
            f"(у тебя {rs['referrals_count']})"
        )

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


def new_referral_notify_text(
    new_user_label: str,
    rs: Dict[str, int],
) -> str:

    return (
        "🎉 <b>Новый реферал!</b>\n"
        f"{DIVIDER}\n\n"
        f"👤 {html_escape(new_user_label)} "
        "перешёл по твоей ссылке и скачал своё первое видео!\n\n"
        f"💎 Начислено: <b>+{REF_POINTS_PER_REFERRAL} 🎟</b>\n\n"
        f"👥 Всего рефералов: <b>{rs['referrals_count']}</b>\n"
        f"🎟 Баланс: <b>{rs['ref_points']}</b>"
    )


async def reward_referral_if_first_download(
    bot,
    uid: int,
    label: str,
) -> None:

    reward = store.try_reward_referral(
        uid,
        REF_POINTS_PER_REFERRAL,
    )

    if not reward:
        return

    with contextlib.suppress(Exception):
        await bot.send_message(
            reward["referrer_id"],
            new_referral_notify_text(
                label,
                {
                    "referrals_count": reward["referrals_count"],
                    "ref_points": reward["ref_points"],
                },
            ),
            parse_mode="HTML",
        )


NUDGE_EVERY = 5


async def _maybe_send_nudge(
    bot,
    uid: int,
) -> None:

    import random

    from broadcast import (
        REMINDER_MSG,
        DONATE_REMINDER_MSG,
        REFERRAL_REMINDER_MSG,
    )

    from helpers import to_html_simple

    total = store.bump_download_counter(uid)

    if total % NUDGE_EVERY != 0:
        return

    text = random.choice(
        [
            REMINDER_MSG,
            DONATE_REMINDER_MSG,
            REFERRAL_REMINDER_MSG,
        ]
    )

    with contextlib.suppress(Exception):
        await bot.send_message(
            uid,
            to_html_simple(text),
            parse_mode="HTML",
        )


async def after_download_hooks(
    bot,
    uid: int,
    label: str,
) -> None:

    await reward_referral_if_first_download(
        bot,
        uid,
        label,
    )

    await _maybe_send_nudge(
        bot,
        uid,
    )
