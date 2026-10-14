"""
/history — история скачиваний файлом. ТОЛЬКО ДЛЯ АДМИНОВ (обычным пользователям бот не отвечает,
как и на остальные админ-команды; описание — в админ-справке, keyboards.ADMIN_HELP_TEXT).

  /history                 — своя история (.txt, новые записи сверху)
  /history 123456789       или  /history @username   — история конкретного человека
  /history all             — последние скачивания ВСЕХ пользователей (до HISTORY_ALL_LIMIT строк)
  к любому варианту можно добавить csv (таблица .csv, UTF-8 с BOM — открывается в Excel):
  /history all csv

Данные берутся из store.get_history(uid): туда пишут inc_download/inc_audio
(см. storage.py). Хранятся последние HISTORY_MAX_PER_USER записей на человека
(по умолчанию 300, настраивается через .env).
"""
import contextlib
import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

from globals_state import dp
from config import MSK_TZ, HISTORY_MAX_PER_USER, log
from storage import store
from i18n import tr
from user_label import resolve_user_label, resolve_uid_from_arg
from gates import gate_message
from helpers import is_admin
from logging_channel import log_event, format_user_for_log
from stats import _SOURCE_LABELS

HISTORY_ALL_LIMIT = 3000  # сколько строк максимум в /history all

_EMPTY = "📭 История скачиваний пока пуста. Пришли ссылку — и она появится здесь."
_CAPTION = "🧾 История скачиваний: {n} шт. (хранятся последние {cap})."


def _source_label(src: str) -> str:
    if not src:
        return "—"
    if src in _SOURCE_LABELS:
        return _SOURCE_LABELS[src]
    if src.startswith("tiktok"):  # tiktok_ytdlp_fallback и т.п.
        return _SOURCE_LABELS.get("tiktok", "TikTok")
    return src


def _plain(label: str) -> str:
    """'🎵 TikTok' -> 'TikTok' (для CSV)."""
    parts = label.split(" ", 1)
    return parts[1] if len(parts) == 2 and not parts[0].isalnum() else label


def _kind_label(message: Message, e: Dict[str, Any]) -> str:
    kind = e.get("k")
    n = int(e.get("n") or 1)
    if kind == "photo":
        base = tr(message, "фото")
        return f"{base} ×{n}" if n > 1 else base
    if kind == "audio":
        return tr(message, "звук")
    return tr(message, "видео")


def _fmt_ts(ts: Any) -> str:
    try:
        return datetime.fromtimestamp(int(ts), MSK_TZ).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return "?"


def _entry_user(e: Dict[str, Any]) -> str:
    """Для сводной истории админа: «метка (id)»."""
    uid = e.get("_uid")
    if uid is None:
        return ""
    label = e.get("_label") or ""
    return f"{label} ({uid})" if label and label != str(uid) else str(uid)


def build_txt(message: Message, uid: Optional[int], label: str, history: List[Dict[str, Any]],
              title: Optional[str] = None) -> str:
    """history — в хронологическом порядке (старые первыми); в файл идёт новыми сверху."""
    now = datetime.now(MSK_TZ).strftime("%d.%m.%Y %H:%M")
    lines = [
        title or f"{tr(message, 'История скачиваний')}",
        "=" * 40,
    ]
    if uid is not None:
        lines.append(f"{tr(message, 'Пользователь')}: {label} (id {uid})")
    lines += [
        f"{tr(message, 'Сформировано (МСК)')}: {now}",
        f"{tr(message, 'Записей')}: {len(history)}",
        "=" * 40,
        "",
    ]
    for i, e in enumerate(reversed(history), 1):  # новые сверху
        who = _entry_user(e)
        head = f"{i}. {_fmt_ts(e.get('ts'))} · "
        if who:
            head += f"{who} · "
        head += f"{_source_label(str(e.get('s') or ''))} · {_kind_label(message, e)}"
        lines.append(head)
        if e.get("u"):
            lines.append(f"   {e['u']}")
        if e.get("t"):
            lines.append(f"   {e['t']}")
        lines.append("")
    if not history:
        lines.append("—")
    return "\n".join(lines)


def build_csv(message: Message, history: List[Dict[str, Any]], with_user: bool = False) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    head = ["date_msk", "type", "source", "items", "url", "title"]
    if with_user:
        head = ["user_id", "user"] + head
    w.writerow(head)
    for e in reversed(history):
        row = [
            _fmt_ts(e.get("ts")),
            e.get("k") or "video",
            _plain(_source_label(str(e.get("s") or ""))),
            int(e.get("n") or 1),
            e.get("u") or "",
            e.get("t") or "",
        ]
        if with_user:
            row = [e.get("_uid", ""), e.get("_label", "")] + row
        w.writerow(row)
    return buf.getvalue().encode("utf-8-sig")


def _all_users_history() -> List[Dict[str, Any]]:
    """Сводная история всех пользователей: последние HISTORY_ALL_LIMIT записей, старые первыми."""
    merged: List[Dict[str, Any]] = []
    for uid_str, entries in (store.data.get("history", {}) or {}).items():
        try:
            uid = int(uid_str)
        except ValueError:
            continue
        label = store.get_user_label(uid)
        for e in entries or []:
            d = dict(e)
            d["_uid"] = uid
            d["_label"] = label
            merged.append(d)
    merged.sort(key=lambda x: int(x.get("ts") or 0))
    return merged[-HISTORY_ALL_LIMIT:]


async def _send(message: Message, data: bytes, name: str, caption: str) -> None:
    await message.answer_document(BufferedInputFile(data, filename=name), caption=caption)


@dp.message(Command("history"))
async def history_cmd(message: Message, command: CommandObject):
    uid = message.from_user.id
    try:
        label = await resolve_user_label(message.bot, uid)
        store.set_user_label(uid, label)

        if not is_admin(uid):  # не админ — молча игнорируем, как остальные админ-команды
            return
        if not await gate_message(message, label):
            return

        tokens = (command.args or "").split()
        as_csv = any(t.lower() == "csv" for t in tokens)
        rest = [t for t in tokens if t.lower() != "csv"]
        admin = True
        stamp = datetime.now(MSK_TZ).strftime("%Y%m%d")
        ext = "csv" if as_csv else "txt"

        # ---------- админ: сводная история всех ----------
        if admin and rest and rest[0].lower() == "all":
            hist = _all_users_history()
            if not hist:
                await message.answer("📭 Истории пока нет ни у кого.")
                return
            if as_csv:
                data = build_csv(message, hist, with_user=True)
            else:
                data = build_txt(message, None, "", hist, title="История скачиваний — все пользователи").encode("utf-8")
            await _send(message, data, f"history_all_{stamp}.{ext}",
                        f"🧾 Все пользователи: последние {len(hist)} скачиваний.")
            target_desc = f"все (записей: {len(hist)})"

        # ---------- админ: история конкретного человека ----------
        elif admin and rest:
            target = await resolve_uid_from_arg(message.bot, rest[0])
            if target is None:
                await message.answer("❌ Пользователь не найден. Проверь ID или username.")
                return
            t_label = await resolve_user_label(message.bot, target)
            store.set_user_label(target, t_label)
            hist = store.get_history(target)
            if not hist:
                await message.answer(f"📭 У {t_label} пока нет записей истории (до обновления ссылки не сохранялись).")
                return
            if as_csv:
                data = build_csv(message, hist)
            else:
                data = build_txt(message, target, t_label, hist).encode("utf-8")
            await _send(message, data, f"history_{target}_{stamp}.{ext}",
                        f"🧾 {t_label}: {len(hist)} шт. (хранятся последние {HISTORY_MAX_PER_USER}).")
            target_desc = f"{t_label} (записей: {len(hist)})"

        # ---------- своя история ----------
        else:
            hist = store.get_history(uid)
            if not hist:
                await message.answer(tr(message, _EMPTY))
                return
            if as_csv:
                data = build_csv(message, hist)
            else:
                data = build_txt(message, uid, label, hist).encode("utf-8")
            await _send(message, data, f"history_{uid}_{stamp}.{ext}",
                        tr(message, _CAPTION, n=len(hist), cap=HISTORY_MAX_PER_USER))
            target_desc = f"своя (записей: {len(hist)})"

        with contextlib.suppress(Exception):
            await log_event(
                message.bot,
                "history",
                [
                    "🧾 Категория: <b>История скачиваний (файл)</b>",
                    f"👤 User/id: <b>{format_user_for_log(label, uid)}</b>",
                    f"📄 Формат: <b>{ext}</b>, история: <b>{target_desc}</b>",
                ],
            )
    except Exception as e:
        log.exception("/history failed for uid=%s: %s", uid, e)
        with contextlib.suppress(Exception):
            await message.answer("❌ Не удалось собрать историю. Попробуй ещё раз чуть позже.")
