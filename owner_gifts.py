"""
Подарки владельцу бота за Telegram Stars (кнопка «🎁 Подарить подарок» в /donate).

Поток: список подарков → анонимно / от моего имени → с текстом / без → подтверждение → оплата Stars →
карточка подарка уходит владельцу (SUPPORT_ADMIN_ID).

Список подарков (эмодзи, название, цена) заполняется в config.OWNER_GIFTS.

Анонимность:
  • в карточке, которую получает владелец, имя дарителя скрыто, если он выбрал «анонимно»
    (или всегда, если OWNER_GIFT_HIDE_SENDER_ALWAYS=1);
  • настоящий отправитель ВСЕГДА пишется в лог-канал (категория ownergift) и в admin.log —
    так главный админ видит, от кого подарок.
"""
import secrets
import time
from typing import Any, Dict, List, Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, LinkPreviewOptions

import config as _cfg
from config import OWNER_GIFTS, OWNER_GIFT_TTL_SEC, SUPPORT_ADMIN_ID, log
from helpers import html_escape
from i18n import tr, get_lang

PENDING_PAYMENT_TTL_SEC = 24 * 3600
HISTORY_MAX = 500

# Мастер выбора подарка (в памяти): uid -> {"key", "anon", "text", "await_text", "ts"}
sessions: Dict[int, Dict[str, Any]] = {}

# ---------------- тексты (ключ перевода — русская строка, см. i18n_gifts.py) ----------------
S_LIST = (
    "🎁 <b>Подарок владельцу бота</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "Хочешь порадовать автора? Выбери подарок — он оплачивается звёздами ⭐ и придёт владельцу в личные сообщения.\n\n"
    "ℹ️ Администрация бота может видеть отправителя в служебных логах, даже если ты выберешь «анонимно».\n\n"
    "Выбери подарок 👇"
)
S_EMPTY = "🎁 Подарки пока не добавлены — загляни позже."
S_ANON = (
    "{emoji} <b>{name}</b> — {price} ⭐\n\n"
    "Как отправить подарок?\n\n"
    "🕶 <b>Анонимно</b> — имя не будет указано в подарке\n"
    "👤 <b>От моего имени</b> — владелец увидит, кто подарил"
)
S_TEXT = "💌 <b>Добавить сообщение к подарку?</b>"
S_ASK_TEXT = "✍️ Напиши текст к подарку одним сообщением (до {n} символов).\n\nОтмена — кнопка ниже."
S_TEXT_LONG = "❌ Слишком длинно: максимум {n} символов. Сократи и пришли ещё раз."
S_CONFIRM = (
    "🎁 <b>Проверь подарок</b>\n"
    "━━━━━━━━━━━━━━━━━━━━\n\n"
    "{emoji} <b>{name}</b> — {price} ⭐\n"
    "👤 От кого: <b>{sender}</b>\n"
    "💌 Текст: {text}\n\n"
    "Всё верно? Нажми «Оплатить»."
)
S_WHO_ANON = "🕶 анонимно"
S_WHO_NAMED = "👤 от моего имени"
S_NO_TEXT = "— без текста —"
S_CANCELLED = "❌ Отменено."
S_EXPIRED = "⌛ Выбор подарка устарел — открой /donate и начни заново."
S_PAID_OK = "✅ <b>Подарок отправлен!</b> 🎁\n\nСпасибо — владельцу будет приятно 💛"
S_PAID_LOST = "⚠️ Оплата получена, но данные подарка потерялись. Напиши в /support — разберёмся."
S_OWNER_CARD = "🎁 <b>Вам подарок!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n{emoji} <b>{name}</b> · {price} ⭐\n👤 От: {sender}"
S_OWNER_ANON = "🕶 Аноним"
S_INV_DESC = "Подарок владельцу бота"
B_ANON = "🕶 Анонимно"
B_NAMED = "👤 От моего имени"
B_ADD_TEXT = "✍️ Добавить текст"
B_NO_TEXT = "➡️ Без текста"
B_BACK = "⬅️ Назад"
B_CANCEL = "❌ Отмена"
B_PAY = "⭐ Оплатить {price}"
B_GIFT_MENU = "🎁 Подарить подарок"

ALL_TEXTS: List[str] = [
    S_LIST, S_EMPTY, S_ANON, S_TEXT, S_ASK_TEXT, S_TEXT_LONG, S_CONFIRM, S_WHO_ANON, S_WHO_NAMED, S_NO_TEXT,
    S_CANCELLED, S_EXPIRED, S_PAID_OK, S_PAID_LOST, S_OWNER_CARD, S_OWNER_ANON, S_INV_DESC,
    B_ANON, B_NAMED, B_ADD_TEXT, B_NO_TEXT, B_BACK, B_CANCEL, B_PAY, B_GIFT_MENU,
]


# ---------------- подарки ----------------
def _clean_gifts() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for g in OWNER_GIFTS or []:
        try:
            key = str(g["key"]).strip()
            price = int(g["price"])
        except Exception:
            continue
        if not key or ":" in key or key in seen or not (1 <= price <= 10000):
            log.warning("OWNER_GIFTS: пропускаю некорректный подарок %r", g)
            continue
        seen.add(key)
        out.append({
            "key": key, "emoji": str(g.get("emoji") or "🎁"), "name": str(g.get("name") or key),
            "price": price, "names": dict(g.get("names") or {}), "gift_id": str(g.get("gift_id") or "").strip(),
        })
    return out


def gifts() -> List[Dict[str, Any]]:
    return _clean_gifts()


def gift_by_key(key: str) -> Optional[Dict[str, Any]]:
    return next((g for g in gifts() if g["key"] == key), None)


def gift_name(g: Dict[str, Any], who: Any) -> str:
    lang = who if isinstance(who, str) else get_lang(who)
    return str((g.get("names") or {}).get(lang) or g["name"])


# ---------------- клавиатуры ----------------
def _kb(rows: List[List[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def list_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [[_btn(f"{g['emoji']} {gift_name(g, lang)} — {g['price']} ⭐", f"og:pick:{g['key']}")] for g in gifts()]
    rows.append([_btn(tr(lang, B_BACK), "donate:back")])
    return _kb(rows)


def anon_kb(lang: str) -> InlineKeyboardMarkup:
    return _kb([
        [_btn(tr(lang, B_ANON), "og:anon:1"), _btn(tr(lang, B_NAMED), "og:anon:0")],
        [_btn(tr(lang, B_BACK), "og:list"), _btn(tr(lang, B_CANCEL), "og:cancel")],
    ])


def text_kb(lang: str) -> InlineKeyboardMarkup:
    return _kb([
        [_btn(tr(lang, B_ADD_TEXT), "og:txt:1"), _btn(tr(lang, B_NO_TEXT), "og:txt:0")],
        [_btn(tr(lang, B_BACK), "og:back:anon"), _btn(tr(lang, B_CANCEL), "og:cancel")],
    ])


def cancel_kb(lang: str) -> InlineKeyboardMarkup:
    return _kb([[_btn(tr(lang, B_CANCEL), "og:cancel")]])


def confirm_kb(lang: str, price: int) -> InlineKeyboardMarkup:
    return _kb([
        [_btn(tr(lang, B_PAY, price=price), "og:pay")],
        [_btn(tr(lang, B_BACK), "og:back:text"), _btn(tr(lang, B_CANCEL), "og:cancel")],
    ])


# ---------------- сессии мастера ----------------
def cleanup_sessions() -> None:
    now = time.time()
    for uid in [u for u, s in sessions.items() if now - s.get("ts", 0) > OWNER_GIFT_TTL_SEC]:
        sessions.pop(uid, None)


def get_session(uid: int) -> Optional[Dict[str, Any]]:
    cleanup_sessions()
    s = sessions.get(uid)
    if s:
        s["ts"] = time.time()
    return s


def is_waiting_text(uid: int) -> bool:
    s = get_session(uid)
    return bool(s and s.get("await_text"))


def render_confirm(uid: int, s: Dict[str, Any]) -> Optional[str]:
    g = gift_by_key(s.get("key", ""))
    if not g:
        return None
    text = s.get("text") or ""
    return tr(
        uid, S_CONFIRM,
        emoji=g["emoji"], name=html_escape(gift_name(g, uid)), price=g["price"],
        sender=tr(uid, S_WHO_ANON if s.get("anon") else S_WHO_NAMED),
        text=f"<i>{html_escape(text)}</i>" if text else tr(uid, S_NO_TEXT),
    )


# ---------------- оплата ----------------
def _store():
    from storage import store
    return store


def _purge_pending() -> None:
    st = _store()
    pend = st.data.setdefault("og_pending", {})
    now = time.time()
    for tok in [t for t, v in pend.items() if now - float(v.get("ts", 0)) > PENDING_PAYMENT_TTL_SEC]:
        pend.pop(tok, None)


def create_pending(uid: int, s: Dict[str, Any]) -> Optional[str]:
    g = gift_by_key(s.get("key", ""))
    if not g:
        return None
    _purge_pending()
    token = secrets.token_urlsafe(9)
    st = _store()
    st.data.setdefault("og_pending", {})[token] = {
        "uid": uid, "key": g["key"], "anon": bool(s.get("anon")), "text": s.get("text") or "",
        "price": g["price"], "ts": time.time(),
    }
    st._mark_dirty()
    return token


def pending_exists(token: str) -> bool:
    return token in _store().data.get("og_pending", {})


def pop_pending(token: str) -> Optional[Dict[str, Any]]:
    st = _store()
    v = st.data.setdefault("og_pending", {}).pop(token, None)
    if v is not None:
        st._mark_dirty()
    return v


async def send_gift_invoice(bot: Bot, uid: int, token: str, g: Dict[str, Any]) -> None:
    title = f"{g['emoji']} {gift_name(g, uid)}"[:32]
    await bot.send_invoice(
        chat_id=uid,
        title=title,
        description=tr(uid, S_INV_DESC),
        payload=f"ogift:{token}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=gift_name(g, uid)[:32], amount=int(g["price"]))],
    )


async def deliver_gift(bot: Bot, sender_uid: int, sender_label: str, pend: Dict[str, Any], stars_paid: int,
                       charge_id: str = "") -> bool:
    """Отправляет карточку владельцу и пишет полный лог (с настоящим отправителем). True — карточка доставлена."""
    from logging_channel import log_event, format_user_for_log
    from admin_log_file import log_admin

    g = gift_by_key(pend.get("key", "")) or {"key": pend.get("key", "?"), "emoji": "🎁", "name": pend.get("key", "?"),
                                              "price": stars_paid, "names": {}}
    owner = SUPPORT_ADMIN_ID
    anon = bool(pend.get("anon"))
    text = str(pend.get("text") or "")
    shown_anon = anon or bool(getattr(_cfg, "OWNER_GIFT_HIDE_SENDER_ALWAYS", False))

    who = tr(owner, S_OWNER_ANON) if shown_anon else format_user_for_log(sender_label, sender_uid)
    card = tr(owner, S_OWNER_CARD, emoji=g["emoji"], name=html_escape(gift_name(g, owner)), price=stars_paid, sender=who)
    if text:
        card += f"\n💌 {html_escape(text)}"

    delivered = True
    try:
        await bot.send_message(owner, card, parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as e:
        delivered = False
        log.warning("owner gift: не удалось отправить карточку владельцу: %s", e)

    # настоящий подарок из каталога Telegram — бот дарит владельцу сам, со своего баланса звёзд
    real_status = ""
    gift_id = str(g.get("gift_id") or "")
    if gift_id:
        try:
            kw = {"user_id": owner, "gift_id": gift_id}
            if text:
                kw["text"] = text[:128]
            await bot.send_gift(**kw)
            real_status = "отправлен"
        except Exception as e:
            real_status = f"НЕ отправлен: {e.__class__.__name__}: {str(e)[:150]}"
            log.warning("owner gift: sendGift не удался: %s", e)

    st = _store()
    hist = st.data.setdefault("og_history", [])
    hist.append({
        "ts": int(time.time()), "from": sender_uid, "key": g["key"], "price": stars_paid, "anon": anon,
        "text": text, "charge": charge_id, "delivered": delivered, "real_gift": real_status,
    })
    del hist[:-HISTORY_MAX]
    st._mark_dirty()

    try:
        log_admin(sender_uid, "owner_gift", f"gift={g['key']} stars={stars_paid} anon={anon} charge={charge_id}")
    except Exception:
        pass
    try:
        lines = [
            "🎁 Категория: <b>Подарок владельцу</b>",
            f"👤 От кого (реально): <b>{format_user_for_log(sender_label, sender_uid)}</b>",
            f"🎀 Подарок: <b>{g['emoji']} {html_escape(g['name'])}</b> — <b>{stars_paid} ⭐</b>",
            f"🕶 Выбрал: <b>{'анонимно' if anon else 'от своего имени'}</b>"
            + (" (в карточке скрыто принудительно)" if (shown_anon and not anon) else ""),
            f"💌 Текст: {html_escape(text) if text else '—'}",
            f"📬 Карточка владельцу: <b>{'доставлена' if delivered else 'НЕ доставлена (владелец не открыл чат с ботом?)'}</b>",
        ]
        if gift_id:
            lines.append(f"🎀 Настоящий подарок Telegram: <b>{html_escape(real_status)}</b>")
        if charge_id:
            lines.append(f"🧾 charge_id: <code>{html_escape(charge_id)}</code>")
        await log_event(bot, "ownergift", lines)
    except Exception as e:
        log.warning("owner gift: лог не отправлен: %s", e)
    return delivered
