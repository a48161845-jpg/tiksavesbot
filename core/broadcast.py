"""
Рассылки: ручная (через /broadcast или admin UI) и автоматическая —
случайно, примерно раз в 50 скачиваний (не по расписанию), выбирает одно
из трёх готовых напоминаний и шлёт всем пользователям.
"""
import asyncio
import contextlib
import time
from typing import Dict, Optional

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import Message, LinkPreviewOptions

from core.config import BROADCAST_MAX_USERS, BROADCAST_DELAY_SEC
from core.helpers import html_escape, to_html_simple
from i18n import get_lang, DEFAULT_LANG
from core.storage import store
from core.admin_log_file import log_admin
from core.logging_channel import log_event, format_user_for_log
from ui.keyboards import broadcast_cancel_kb, nudge_kb

# ================== STATE ==================
pending_admin_broadcast: Dict[int, str] = {}
pending_admin_broadcast_text: Dict[int, str] = {}
pending_admin_broadcast_source: Dict[int, str] = {}
pending_admin_broadcast_cancel: Dict[int, bool] = {}

# ================== PRESET TEXTS ==================
# Тексты напоминаний и шаблоны рассылок живут в core/nudge_texts.py (на всех языках).
# Старые имена оставлены для совместимости импортов.
from core.nudge_texts import DONATE_NUDGES, SUPPORT_NUDGE, BROADCAST_PRESETS  # noqa: E402

REMINDER_MSG = SUPPORT_NUDGE["ru"]
DONATE_REMINDER_MSG = DONATE_NUDGES[0]["ru"]


def preset_ru_text(preset_id: str) -> str:
    """Русский текст шаблона рассылки (он же ключ готовых переводов)."""
    return BROADCAST_PRESETS[preset_id][1]["ru"]


async def build_lang_variants(users, raw_text: str, html_ru: str, *, already_html: bool = False) -> Dict[str, str]:
    """
    Готовит текст рассылки на языке каждого получателя: {lang: html}.
    1) есть готовый перевод в i18n (пресеты-напоминания) — берём его;
    2) иначе автоперевод (auto_translate); если переводчик недоступен — русский оригинал.
    """
    from core import globals_state
    from i18n import tr
    from i18n.auto_translate import translate_html

    langs = {get_lang(u) for u in users}
    variants: Dict[str, str] = {DEFAULT_LANG: html_ru}
    session = getattr(globals_state.g_provider, "session", None)

    async def make(lang: str) -> None:
        ready = tr(lang, raw_text)
        if ready != raw_text:
            variants[lang] = ready if already_html else to_html_simple(ready)
            return
        variants[lang] = await translate_html(html_ru, lang, session)

    await asyncio.gather(*(make(lg) for lg in langs if lg != DEFAULT_LANG))
    return variants


def _langs_line(users, variants: Dict[str, str]) -> str:
    cnt: Dict[str, int] = {}
    for u in users:
        lg = get_lang(u)
        cnt[lg] = cnt.get(lg, 0) + 1
    return ", ".join(f"{k}: {v}" for k, v in sorted(cnt.items(), key=lambda x: -x[1]))


_BLOCKED_HINTS = ("bot was blocked", "user is deactivated", "chat not found", "bot can't initiate", "forbidden")


async def _send_to_user(bot, uid: int, text: str, markup) -> str:
    """Отправка одному получателю -> 'ok' | 'blocked' | 'fail'. FloodWait Telegram пережидаем и повторяем."""
    for attempt in range(2):
        try:
            await bot.send_message(uid, text, parse_mode="HTML", reply_markup=markup,
                                   link_preview_options=LinkPreviewOptions(is_disabled=True))
            return "ok"
        except TelegramRetryAfter as e:
            await asyncio.sleep(int(getattr(e, "retry_after", 3)) + 1)
        except Exception as e:
            low = str(e).lower()
            return "blocked" if any(h in low for h in _BLOCKED_HINTS) else "fail"
    return "fail"


def _progress_bar(done: int, total: int, width: int = 12) -> str:
    filled = int(width * done / total) if total else width
    return "▓" * filled + "░" * (width - filled)


async def do_broadcast(message: Message, admin_id: int, admin_label: str, raw_text: str, *,
                       already_html: bool = False, kb_kind: Optional[str] = None) -> None:
    """
    Рассылка всем пользователям на их языках. kb_kind — вид кнопок под сообщением (ui.keyboards.nudge_kb:
    donate | premium | support | update); без него сообщение уходит без кнопок.
    Показывает прогресс, в конце — сводку: доставлено / заблокировали бота / ошибки / время.
    """
    users = store.get_all_user_ids()
    if not users:
        await message.answer("Пока нет пользователей для рассылки.", parse_mode="HTML")
        return
    if len(users) > BROADCAST_MAX_USERS:
        await message.answer(f"⚠️ Слишком много пользователей ({len(users)}). Лимит: {BROADCAST_MAX_USERS}.", parse_mode="HTML")
        return

    html = raw_text if already_html else to_html_simple(raw_text)
    variants = await build_lang_variants(users, raw_text, html, already_html=already_html)

    log_admin(admin_id, "broadcast", f"len={len(raw_text)} users={len(users)}")
    await log_event(
        message.bot,
        "broadcast",
        [
            "📣 Категория: <b>Рассылка</b>",
            "🚀 Старт",
            f"👤 Кто: <b>{format_user_for_log(admin_label, admin_id)}</b>",
            f"👥 Получателей: <b>{len(users)}</b>",
            f"🌍 Языки: <b>{_langs_line(users, variants)}</b>",
        ],
    )

    pending_admin_broadcast_cancel[admin_id] = False
    status = await message.answer(
        f"📣 <b>Рассылка запущена</b>\n{_progress_bar(0, len(users))} 0/{len(users)}",
        parse_mode="HTML",
        reply_markup=broadcast_cancel_kb(),
    )
    total, started = len(users), time.monotonic()
    counts = {"ok": 0, "blocked": 0, "fail": 0}
    done = 0
    for u in users:
        if pending_admin_broadcast_cancel.get(admin_id):
            break
        lang = get_lang(u)
        markup = nudge_kb(lang, kb_kind) if kb_kind else None
        counts[await _send_to_user(message.bot, u, variants.get(lang, html), markup)] += 1
        done += 1
        if done % 25 == 0 and done < total:  # живой прогресс, не чаще чем раз в 25 получателей
            with contextlib.suppress(Exception):
                await status.edit_text(
                    f"📣 <b>Рассылка идёт…</b>\n{_progress_bar(done, total)} {done}/{total}\n"
                    f"📬 Доставлено: {counts['ok']}",
                    parse_mode="HTML", reply_markup=broadcast_cancel_kb())
        await asyncio.sleep(BROADCAST_DELAY_SEC)

    elapsed = int(time.monotonic() - started)
    summary = (
        f"📬 Доставлено: <b>{counts['ok']}</b> из <b>{total}</b>\n"
        f"🚫 Заблокировали бота: <b>{counts['blocked']}</b>\n"
        f"⚠️ Ошибки: <b>{counts['fail']}</b>\n"
        f"⏱ Время: <b>{elapsed // 60}м {elapsed % 60}с</b>"
    )
    stopped = bool(pending_admin_broadcast_cancel.get(admin_id))
    head = "⛔ <b>Рассылка остановлена</b>" if stopped else "✅ <b>Рассылка завершена</b>"
    with contextlib.suppress(Exception):
        await status.edit_text(f"{head}\n{_progress_bar(done, total)} {done}/{total}\n\n{summary}", parse_mode="HTML")
    await log_event(
        message.bot,
        "broadcast",
        [
            "📣 Категория: <b>Рассылка</b>",
            "⛔ Остановлена" if stopped else "🏁 Завершена",
            f"👤 Кто: <b>{format_user_for_log(admin_label, admin_id)}</b>",
            f"✅ Доставлено: <b>{counts['ok']}/{total}</b> · 🚫 заблокировали: <b>{counts['blocked']}</b> · ⚠️ ошибки: <b>{counts['fail']}</b>",
        ],
    )
    pending_admin_broadcast_cancel.pop(admin_id, None)


async def do_broadcast_system(bot: Bot, kind: str, raw_text: str) -> None:
    users = store.get_all_user_ids()
    if not users:
        await log_event(
            bot,
            "broadcast",
            [
                "📣 Категория: <b>Авто-рассылка</b>",
                f"🧩 Тип: <b>{html_escape(kind)}</b>",
                "ℹ️ Пользователей нет",
            ],
        )
        return
    if len(users) > BROADCAST_MAX_USERS:
        await log_event(
            bot,
            "broadcast",
            [
                "📣 Категория: <b>Авто-рассылка</b>",
                f"🧩 Тип: <b>{html_escape(kind)}</b>",
                f"⚠️ Слишком много пользователей: <b>{len(users)}</b>",
            ],
        )
        return

    html = to_html_simple(raw_text)
    variants = await build_lang_variants(users, raw_text, html)
    await log_event(
        bot,
        "broadcast",
        [
            "📣 Категория: <b>Авто-рассылка</b>",
            f"🧩 Тип: <b>{html_escape(kind)}</b>",
            f"👥 Получателей: <b>{len(users)}</b>",
            f"🌍 Языки: <b>{_langs_line(users, variants)}</b>",
            "🚀 Старт",
        ],
    )

    sent = 0
    for u in users:
        try:
            await bot.send_message(u, variants.get(get_lang(u), html), parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True))
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(BROADCAST_DELAY_SEC)

    await log_event(
        bot,
        "broadcast",
        [
            "📣 Категория: <b>Авто-рассылка</b>",
            f"🧩 Тип: <b>{html_escape(kind)}</b>",
            f"✅ Отправлено: <b>{sent}/{len(users)}</b>",
            "🏁 Завершена",
        ],
    )



