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

from core.globals_state import dp
from i18n import tr, get_lang
from core import globals_state
from core.config import STARS_MIN, STARS_MAX
from core.storage import store
from core.user_label import resolve_user_label
from core.gates import gate_callback, gate_message
from core.logging_channel import log_event, format_user_for_log
from ui.send_helpers import send_music_if_any, send_external_audio, send_description_if_any
from ui.picker_state import video_extras
from ui.keyboards import (
    DONATE_TEXT,
    STARS_MENU_TEXT,
    SUPPORT_TEXT,
    RUB_DONATE_TEXT,
    donate_main_kb,
    song_kb,
    rub_donate_kb,
    stars_kb,
    under_video_kb,
)
from core.donate import stars_valid, safe_edit, send_stars_invoice, waiting_stars_amount


def song_card_text(uid: int, song: dict) -> str:
    """Карточка песни: название/автор или пометка «оригинальный звук»."""
    import html as _html
    title, author = _html.escape(song.get("title", "")), _html.escape(song.get("author", ""))
    if song.get("original"):
        return tr(uid, "🎤 <b>Оригинальный звук</b>\nАвтор: <b>{author}</b>\n\nЭто звук самого автора видео — в музыкальных сервисах его, скорее всего, нет. Можно скачать как аудио 👇",
                  author=author or "—")
    return tr(uid, "🎵 <b>Песня из видео</b>\n<b>{title}</b>\n{author}\n\nНайди её в любимом сервисе или скачай звук 👇",
              title=title or "—", author=author)


def _drop_extras_if_empty(req_id: str, extra: dict) -> None:
    """Данные видео держим, пока есть что показать: звук, описание или карточка песни."""
    if not extra.get("music") and not extra.get("description") and not extra.get("song"):
        video_extras.pop(req_id, None)


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
            await send_music_if_any(call.message, globals_state.g_provider, url, uid=uid, label=label, src=extra.get("src"),
                                    song=extra.get("song"))
        with contextlib.suppress(Exception):
            if call.message:
                await call.message.edit_reply_markup(
                    reply_markup=under_video_kb(has_music=False, has_description=bool(extra.get("description")), req_id=req_id,
                                                lang=get_lang(uid), has_song=bool(extra.get("song")))
                )
        _drop_extras_if_empty(req_id, extra)
        return

    if action == "song":
        song = extra.get("song") if extra else None
        if not song:
            await call.answer(tr(uid, "Нет данных о песне для этого видео."), show_alert=True)
            return
        await call.answer()
        if call.message:
            await call.message.answer(
                song_card_text(uid, song), parse_mode="HTML",
                reply_markup=song_kb(get_lang(uid), song, req_id=req_id, can_download=bool(extra.get("music"))),
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
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
                    reply_markup=under_video_kb(has_music=bool(extra.get("music")), has_description=False, req_id=req_id,
                                                lang=get_lang(uid), has_song=bool(extra.get("song")))
                )
        _drop_extras_if_empty(req_id, extra)
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

    if action == "rub":
        await safe_edit(call, tr(uid, RUB_DONATE_TEXT), rub_donate_kb(get_lang(uid)))
        await call.answer()
        return

    if action == "back":
        await safe_edit(call, tr(uid, DONATE_TEXT), donate_main_kb(get_lang(uid)))
        await call.answer()
        return

    if action == "gifts":
        from handlers.owner_gift_callbacks import show_list
        await show_list(call)
        return

    if action == "support":
        await call.answer()
        if call.message:
            from handlers.support_handler import open_support  # раньше тут только показывался текст, а обращение не открывалось
            await open_support(call.message, uid, label)
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
    payload = pre.invoice_payload or ""
    if payload.startswith("premium:"):
        # тариф должен существовать, а сумма — совпадать с его ценой
        from handlers.premium import plan_price
        try:
            ok = plan_price(int(payload.split(":", 1)[1])) == int(pre.total_amount)
        except ValueError:
            ok = False
        if not ok:
            await pre.answer(ok=False, error_message=tr(pre.from_user.id, "❌ Ошибка суммы"))
            return
    if payload.startswith("ogift:"):
        from core import owner_gifts as og
        if not og.pending_exists(payload.split(":", 1)[1]):
            await pre.answer(ok=False, error_message=tr(pre.from_user.id, og.S_EXPIRED))
            return
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

    payload = message.successful_payment.invoice_payload or ""
    if payload.startswith("ogift:"):
        from core import owner_gifts as og
        pend = og.pop_pending(payload.split(":", 1)[1])
        charge_id = getattr(message.successful_payment, "telegram_payment_charge_id", "") or ""
        if not pend:
            await message.answer(tr(message, og.S_PAID_LOST), parse_mode="HTML")
            await log_event(
                message.bot, "ownergift",
                [
                    "🎁 Категория: <b>Подарок владельцу</b>",
                    "⚠️ Оплата прошла, но данные подарка потерялись (рестарт/истёк срок)",
                    f"👤 От кого (реально): <b>{format_user_for_log(label, uid)}</b>",
                    f"💫 Сумма: <b>{stars} ⭐</b>",
                    f"🧾 charge_id: <code>{charge_id}</code>",
                ],
            )
            return
        og.sessions.pop(uid, None)
        await og.deliver_gift(message.bot, uid, label, pend, stars, charge_id)
        await message.answer(tr(message, og.S_PAID_OK), parse_mode="HTML")
        return

    if payload.startswith("premium:"):
        from handlers.premium import fmt_date, plan_price
        from ui.keyboards import PREMIUM_OK_TEXT
        try:
            days = int(payload.split(":", 1)[1])
        except ValueError:
            days = 0
        if plan_price(days) is not None:
            until = store.grant_premium(uid, days)
            await message.answer(tr(message, PREMIUM_OK_TEXT, date=fmt_date(until)), parse_mode="HTML")
            await log_event(
                message.bot,
                "stars",
                [
                    "💎 Категория: <b>Premium куплен</b>",
                    f"👤 User/id: <b>{format_user_for_log(label, uid)}</b>",
                    f"💫 Сумма: <b>{stars} ⭐</b>",
                    f"📅 Тариф: <b>{days} дн.</b> · до {fmt_date(until)}",
                ],
            )
            return

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
