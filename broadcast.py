"""
Рассылки: ручная (через /broadcast или admin UI) и автоматическая —
случайно, примерно раз в 50 скачиваний (не по расписанию), выбирает одно
из трёх готовых напоминаний и шлёт всем пользователям.
"""
import asyncio
from typing import Dict

from aiogram import Bot
from aiogram.types import Message, LinkPreviewOptions

from config import BROADCAST_MAX_USERS, BROADCAST_DELAY_SEC
from helpers import html_escape, to_html_simple
from i18n import get_lang, DEFAULT_LANG
from storage import store
from admin_log_file import log_admin
from logging_channel import log_event, format_user_for_log
from keyboards import broadcast_cancel_kb

# ================== STATE ==================
pending_admin_broadcast: Dict[int, str] = {}
pending_admin_broadcast_text: Dict[int, str] = {}
pending_admin_broadcast_source: Dict[int, str] = {}
pending_admin_broadcast_cancel: Dict[int, bool] = {}

# ================== PRESET TEXTS ==================
REMINDER_MSG = (
    "📌 **Не забывай** \n\n"
    "Если что-то не работает или есть вопрос — команда **/support** покажет, куда писать.\n\n"
    "*Мы всегда на связи* 🙌"
)

DONATE_REMINDER_MSG = (
    "💛 **Нравится бот?**\n\n"
    "Если TikSaves помогает — поддержи проект через **/donate**: Telegram Stars ⭐️, крипта 💲, Donation Alerts\n\n"
    "Любая помощь идёт на хостинг и развитие бота — спасибо! 🙏"
)

# ~1 рассылка на каждые 50 скачиваний, но по-настоящему случайно (не жёсткий
# счётчик "ровно на 50-м") — проверяется на каждом успешном скачивании.
# ПРИМЕЧАНИЕ: фактическая отправка теперь идёт ТОЛЬКО тому, кто скачал
# (см. download_nudge.py:_maybe_send_nudge), а не всем — эти константы
# используются оттуда напрямую по импорту текстов.
RANDOM_REMINDER_CHANCE = 1 / 50


async def build_lang_variants(users, raw_text: str, html_ru: str, *, already_html: bool = False) -> Dict[str, str]:
    """
    Готовит текст рассылки на языке каждого получателя: {lang: html}.
    1) есть готовый перевод в i18n (пресеты-напоминания) — берём его;
    2) иначе автоперевод (auto_translate); если переводчик недоступен — русский оригинал.
    """
    import globals_state
    from i18n import tr
    from auto_translate import translate_html

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


async def do_broadcast(message: Message, admin_id: int, admin_label: str, raw_text: str, *, already_html: bool = False) -> None:
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
        f"📣 Запускаю рассылку…\nПолучателей: {len(users)}",
        parse_mode="HTML",
        reply_markup=broadcast_cancel_kb(),
    )
    sent = 0
    for u in users:
        if pending_admin_broadcast_cancel.get(admin_id):
            break
        try:
            await message.bot.send_message(u, variants.get(get_lang(u), html), parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True))
            sent += 1
        except Exception:
            pass
        await asyncio.sleep(BROADCAST_DELAY_SEC)

    if pending_admin_broadcast_cancel.get(admin_id):
        await status.edit_text(f"⛔ Рассылка остановлена: {sent}/{len(users)}", parse_mode="HTML")
        await log_event(
            message.bot,
            "broadcast",
            [
                "📣 Категория: <b>Рассылка</b>",
                "⛔ Остановлена",
                f"👤 Кто: <b>{format_user_for_log(admin_label, admin_id)}</b>",
                f"✅ Отправлено: <b>{sent}/{len(users)}</b>",
            ],
        )
        pending_admin_broadcast_cancel.pop(admin_id, None)
        return

    await status.edit_text(f"✅ Рассылка завершена: {sent}/{len(users)}")
    await log_event(
        message.bot,
        "broadcast",
        [
            "📣 Категория: <b>Рассылка</b>",
            "🏁 Завершена",
            f"👤 Кто: <b>{format_user_for_log(admin_label, admin_id)}</b>",
            f"✅ Отправлено: <b>{sent}/{len(users)}</b>",
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



