"""
Обработка callback-кнопок админ-панели (callback_data, начинающийся на "ad:").
"""
import contextlib

from aiogram import F
from aiogram.types import CallbackQuery, LinkPreviewOptions

from core.globals_state import dp
from core.helpers import is_admin, parse_stats_mode
from core.storage import store
from core.user_label import resolve_user_label
from core.gates import gate_callback
from core.logging_channel import log_admin_action_to_channel, format_user_for_log
from ui.keyboards import (
    ADMIN_HELP_TEXT,
    admin_menu_kb,
    admin_back_kb,
    admin_broadcast_menu_kb,
    admin_broadcast_confirm_kb,
)
from core.helpers import fmt_date_msk
from core.stats import (
    admin_dashboard_text,
    send_stats_message,
    send_top_message,
    _admin_banlist_text,
    _admin_errors_text,
)
from core.nudge_texts import BROADCAST_PRESETS
from core.broadcast import (
    REMINDER_MSG,
    preset_ru_text,
    do_broadcast,
    pending_admin_broadcast,
    pending_admin_broadcast_text,
    pending_admin_broadcast_source,
    pending_admin_broadcast_cancel,
)


def _menu_text_and_kb():
    """Главный экран панели: живая сводка + кнопки (с актуальным состоянием тех. режима)."""
    return admin_dashboard_text(), admin_menu_kb(store.is_maintenance())


def _broadcast_kb_kind(kind: str) -> str:
    """Какие кнопки повесить под рассылку (ui.keyboards.nudge_kb)."""
    if kind in ("reminder", "p_support"):
        return "support"
    return {"donate": "donate", "p_donate": "donate", "p_premium": "premium"}.get(kind, "donate")


def _broadcast_raw(kind: str) -> str:
    """Русский HTML-текст рассылки по её типу (он же ключ готовых переводов)."""
    if kind in ("reminder", "p_support"):
        return REMINDER_MSG
    if kind == "donate":
        return preset_ru_text("donate")
    return preset_ru_text(kind[2:])


@dp.callback_query(F.data.startswith("ad:"))
async def admin_cb(call: CallbackQuery):
    uid = call.from_user.id
    label = await resolve_user_label(call.bot, uid)
    store.set_user_label(uid, label)

    if not is_admin(uid):
        await call.answer("Нет доступа.", show_alert=True)
        return

    if not await gate_callback(call, label):
        return

    if not call.message:
        await call.answer()
        return

    parts = (call.data or "").split(":")
    cmd = parts[1] if len(parts) > 1 else ""
    arg = parts[2] if len(parts) > 2 else ""
    if cmd == "stats":
        await call.answer()
        if call.message:
            mode = parse_stats_mode(arg) if arg else "all"
            await send_stats_message(call.message, uid, label, mode, edit=True)
        return

    if cmd == "top":
        await call.answer()
        if call.message:
            mode = parse_stats_mode(arg) if arg else "all"
            await send_top_message(call.message, uid, label, mode, edit=True)
        return

    if cmd == "send":
        kind = arg
        if pending_admin_broadcast.get(uid) != kind:
            await call.answer("Нет подтверждения.", show_alert=True)
            return
        pending_admin_broadcast.pop(uid, None)
        pending_admin_broadcast_source.pop(uid, None)
        pending_admin_broadcast_cancel.pop(uid, None)
        await call.answer("Ок")
        if call.message:
            with contextlib.suppress(Exception):
                await call.message.delete()
        if not call.message:
            return
        if kind in ("reminder", "donate") or kind.startswith("p_"):
            pending_admin_broadcast_text.pop(uid, None)
            if kind.startswith("p_") and kind != "p_support" and kind[2:] not in BROADCAST_PRESETS:
                return
            await do_broadcast(call.message, uid, label, _broadcast_raw(kind), already_html=True,
                               kb_kind=_broadcast_kb_kind(kind))
            return
        if kind == "custom":
            raw = pending_admin_broadcast_text.get(uid, "")
            pending_admin_broadcast_text.pop(uid, None)
            if raw:
                await do_broadcast(call.message, uid, label, raw, already_html=True)
            return
        pending_admin_broadcast_text.pop(uid, None)
        return

    if cmd == "errors":
        await log_admin_action_to_channel(call.bot, "Ошибки (кнопка)", [f"👤 Кто: <b>{format_user_for_log(label, uid)}</b>"])
        if call.message:
            with contextlib.suppress(Exception):
                await call.message.edit_text(_admin_errors_text(), parse_mode="HTML", reply_markup=admin_back_kb())
        await call.answer("Ок")
        return

    if cmd == "banlist":
        bans = store.list_bans()
        await log_admin_action_to_channel(call.bot, "Бан-лист (кнопка)", [f"👤 Кто: <b>{format_user_for_log(label, uid)}</b>", f"🚫 Кол-во: <b>{len(bans)}</b>"])
        if call.message:
            with contextlib.suppress(Exception):
                await call.message.edit_text(_admin_banlist_text(), parse_mode="HTML", reply_markup=admin_back_kb())
        await call.answer("Ок")
        return

    if cmd == "adminlist":
        from core.config import ADMINS
        lines = ["👑 <b>Администраторы</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
        lines.append("🔒 <b>Суперадмины:</b>")
        for aid in sorted(ADMINS):
            lbl = store.get_user_label(aid)
            lines.append(f"  └ <b>{format_user_for_log(lbl, aid)}</b>")
        extra = store.get_extra_admins()
        lines.append(f"\n➕ <b>Дополнительные ({len(extra)}):</b>")
        if extra:
            for aid in sorted(extra):
                lbl = store.get_user_label(aid)
                lines.append(f"  └ <b>{format_user_for_log(lbl, aid)}</b>")
        else:
            lines.append("  <i>нет</i>")
        lines.append(f"\n<i>Управление: /adminadd ID · /admindel ID</i>")
        if call.message:
            with contextlib.suppress(Exception):
                await call.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=admin_back_kb())
        await call.answer("Ок")
        return

    if cmd == "dbfile":
        await log_admin_action_to_channel(call.bot, "Дамп БД (кнопка)", [f"👤 Кто: <b>{format_user_for_log(label, uid)}</b>"])
        await call.answer("Формирую дамп…")
        from core.db_report import send_db_json
        await send_db_json(call.bot, uid)
        return

    if cmd == "help":
        await log_admin_action_to_channel(call.bot, "Подсказка админ-панели (кнопка)", [f"👤 Кто: <b>{format_user_for_log(label, uid)}</b>"])
        if call.message:
            with contextlib.suppress(Exception):
                await call.message.edit_text(ADMIN_HELP_TEXT, parse_mode="HTML", reply_markup=admin_back_kb())
        await call.answer("Ок")
        return

    if cmd == "reminder":
        pending_admin_broadcast[uid] = "reminder"
        pending_admin_broadcast_text.pop(uid, None)
        pending_admin_broadcast_source[uid] = "panel"
        users_cnt = store.get_users_count()
        if not call.message:
            await call.answer("Ошибка: сообщение недоступно.", show_alert=True)
            return
        with contextlib.suppress(Exception):
            await call.message.delete()
        await call.message.answer(
            "📣 <b>Подтверждение рассылки</b>\n\n"
            "Тип: <b>Напоминание</b>\n"
            f"Получателей: <b>{users_cnt}</b>\n\n"
            "Отправить?",
            parse_mode="HTML",
            reply_markup=admin_broadcast_confirm_kb("reminder"),
        )
        await call.answer()
        return

    if cmd == "donate":
        pending_admin_broadcast[uid] = "donate"
        pending_admin_broadcast_text.pop(uid, None)
        pending_admin_broadcast_source[uid] = "panel"
        users_cnt = store.get_users_count()
        if not call.message:
            await call.answer("Ошибка: сообщение недоступно.", show_alert=True)
            return
        with contextlib.suppress(Exception):
            await call.message.delete()
        await call.message.answer(
            "📣 <b>Подтверждение рассылки</b>\n\n"
            "Тип: <b>Донат</b>\n"
            f"Получателей: <b>{users_cnt}</b>\n\n"
            "Отправить?",
            parse_mode="HTML",
            reply_markup=admin_broadcast_confirm_kb("donate"),
        )
        await call.answer()
        return

    if cmd == "msg":
        import time as _time
        from ui.support_state import pending_admin_msg
        from ui.keyboards import admin_msg_cancel_kb
        pending_admin_msg[uid] = {"step": "target", "uid": None, "ts": _time.time()}
        with contextlib.suppress(Exception):
            await call.message.edit_text(
                "✉️ <b>Написать пользователю</b>\nПришли <b>ID</b> или <b>@username</b> получателя.\n\n"
                "<i>Быстрее: /msg ID текст</i>", parse_mode="HTML", reply_markup=admin_msg_cancel_kb())
        await call.answer()
        return

    if cmd == "msgcancel":
        from ui.support_state import pending_admin_msg
        pending_admin_msg.pop(uid, None)
        text, kb = _menu_text_and_kb()
        with contextlib.suppress(Exception):
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await call.answer("Отменено")
        return

    if cmd == "bc":
        pending_admin_broadcast_source[uid] = "panel"
        text = (
            "📣 <b>Рассылки</b>\n"
            f"Получателей: <b>{store.get_users_count()}</b>\n\n"
            "Выбери готовый шаблон — перед отправкой покажу предпросмотр. Тексты уйдут на языке каждого получателя.\n\n"
            "✍️ <b>Свой текст:</b> <code>/broadcast текст</code> (поддерживается форматирование)"
        )
        with contextlib.suppress(Exception):
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=admin_broadcast_menu_kb())
        await call.answer()
        return

    if cmd == "bp":
        pid = arg
        if pid != "support" and pid not in BROADCAST_PRESETS:
            await call.answer("Нет такого шаблона.", show_alert=True)
            return
        kind = f"p_{pid}"
        pending_admin_broadcast[uid] = kind
        pending_admin_broadcast_text.pop(uid, None)
        pending_admin_broadcast_source[uid] = "panel"
        title = "📌 Напоминание про /support" if pid == "support" else BROADCAST_PRESETS[pid][0]
        preview = (
            "📣 <b>Предпросмотр рассылки</b>\n"
            f"Шаблон: <b>{title}</b> · получателей: <b>{store.get_users_count()}</b>\n"
            "⬇️ Так увидят русскоязычные пользователи (остальным — перевод):\n\n"
            f"{_broadcast_raw(kind)}"
        )
        with contextlib.suppress(Exception):
            await call.message.edit_text(preview, parse_mode="HTML", reply_markup=admin_broadcast_confirm_kb(kind),
                                         link_preview_options=LinkPreviewOptions(is_disabled=True))
        await call.answer()
        return

    if cmd == "prem":
        ids = store.premium_active_ids()
        rows = sorted(((store.premium_until(i), i) for i in ids), reverse=True)[:15]
        lines = ["💎 <b>Premium</b>", f"Активных подписок: <b>{len(ids)}</b>", ""]
        if rows:
            for until, i in rows:
                lines.append(f"• <b>{format_user_for_log(store.get_user_label(i), i)}</b> — до {fmt_date_msk(until)}")
            if len(ids) > len(rows):
                lines.append(f"… и ещё {len(ids) - len(rows)}")
        else:
            lines.append("<i>Пока никого.</i>")
        lines += ["", "<code>/premium ID дней</code> — выдать или продлить", "<code>/premium ID off</code> — снять"]
        with contextlib.suppress(Exception):
            await call.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=admin_back_kb())
        await call.answer()
        return

    if cmd == "tex":
        enable = not store.is_maintenance()
        store.set_maintenance(enable)
        await log_admin_action_to_channel(call.bot, "Тех. режим (кнопка)", [f"👤 Кто: <b>{format_user_for_log(label, uid)}</b>", f"🔧 Теперь: <b>{'вкл' if enable else 'выкл'}</b>"])
        text, kb = _menu_text_and_kb()
        with contextlib.suppress(Exception):
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await call.answer("Тех. режим включён — бот отвечает всем, кроме админов" if enable else "Тех. режим выключен", show_alert=enable)
        return

    if cmd == "cancel":
        pending_admin_broadcast.pop(uid, None)
        pending_admin_broadcast_text.pop(uid, None)
        pending_admin_broadcast_source.pop(uid, None)
        pending_admin_broadcast_cancel.pop(uid, None)
        if call.message:
            with contextlib.suppress(Exception):
                await call.message.delete()
        await call.answer()
        return

    if cmd == "bcancel":
        if not is_admin(uid):
            await call.answer("Нет доступа.", show_alert=True)
            return
        pending_admin_broadcast_cancel[uid] = True
        await call.answer("Останавливаю…")
        if call.message:
            with contextlib.suppress(Exception):
                await call.message.edit_reply_markup(reply_markup=None)
        return

    if cmd == "back":
        if call.message:
            text, kb = _menu_text_and_kb()
            with contextlib.suppress(Exception):
                await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await call.answer()
        return

    if cmd == "close":
        if pending_admin_broadcast_source.get(uid) == "panel":
            pending_admin_broadcast.pop(uid, None)
            pending_admin_broadcast_text.pop(uid, None)
            pending_admin_broadcast_source.pop(uid, None)
            if call.message:
                text, kb = _menu_text_and_kb()
                with contextlib.suppress(Exception):
                    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
            await call.answer()
            return
        with contextlib.suppress(Exception):
            await call.message.delete()
        await call.answer()
        return

    await call.answer()
