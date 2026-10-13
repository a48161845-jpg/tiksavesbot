"""
/history — присылает человеку историю его скачиваний файлом.

  /history        — текстовый файл (.txt), новые записи сверху
  /history csv    — таблица (.csv, UTF-8 с BOM — открывается в Excel)

Данные берутся из store.get_history(uid): туда пишут inc_download/inc_audio
(см. storage.py). Хранятся последние HISTORY_MAX_PER_USER записей на человека
(по умолчанию 300, настраивается через .env).
"""
import contextlib
import csv
import io
from datetime import datetime
from typing import Any, Dict, List

from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

from globals_state import dp
from config import MSK_TZ, HISTORY_MAX_PER_USER
from storage import store
from i18n import tr
from user_label import resolve_user_label
from gates import gate_message
from logging_channel import log_event, format_user_for_log
from stats import _SOURCE_LABELS

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


def build_txt(message: Message, uid: int, label: str, history: List[Dict[str, Any]]) -> str:
    now = datetime.now(MSK_TZ).strftime("%d.%m.%Y %H:%M")
    lines = [
        f"{tr(message, 'История скачиваний')}",
        "=" * 40,
        f"{tr(message, 'Пользователь')}: {label} (id {uid})",
        f"{tr(message, 'Сформировано (МСК)')}: {now}",
        f"{tr(message, 'Записей')}: {len(history)}",
        "=" * 40,
        "",
    ]
    total = len(history)
    for i, e in enumerate(reversed(history), 1):  # новые сверху
        lines.append(f"{i}. {_fmt_ts(e.get('ts'))} · {_source_label(str(e.get('s') or ''))} · {_kind_label(message, e)}")
        if e.get("u"):
            lines.append(f"   {e['u']}")
        if e.get("t"):
            lines.append(f"   {e['t']}")
        lines.append("")
    if total == 0:
        lines.append("—")
    return "\n".join(lines)


def build_csv(message: Message, history: List[Dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date_msk", "type", "source", "items", "url", "title"])
    for e in reversed(history):
        kind = e.get("k") or "video"
        w.writerow([
            _fmt_ts(e.get("ts")),
            kind,
            _plain(_source_label(str(e.get("s") or ""))),
            int(e.get("n") or 1),
            e.get("u") or "",
            e.get("t") or "",
        ])
    return buf.getvalue().encode("utf-8-sig")


@dp.message(Command("history"))
async def history_cmd(message: Message, command: CommandObject):
    uid = message.from_user.id
    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_message(message, label):
        return
    store.register(uid)

    history = store.get_history(uid)
    if not history:
        await message.answer(tr(message, _EMPTY))
        return

    as_csv = "csv" in ((command.args or "").lower().split())
    stamp = datetime.now(MSK_TZ).strftime("%Y%m%d")
    if as_csv:
        data = build_csv(message, history)
        name = f"history_{uid}_{stamp}.csv"
    else:
        data = build_txt(message, uid, label, history).encode("utf-8")
        name = f"history_{uid}_{stamp}.txt"

    await message.answer_document(
        BufferedInputFile(data, filename=name),
        caption=tr(message, _CAPTION, n=len(history), cap=HISTORY_MAX_PER_USER),
    )

    with contextlib.suppress(Exception):
        await log_event(
            message.bot,
            "history",
            [
                "🧾 Категория: <b>История скачиваний (файл)</b>",
                f"👤 User/id: <b>{format_user_for_log(label, uid)}</b>",
                f"📄 Формат: <b>{'csv' if as_csv else 'txt'}</b>, записей: <b>{len(history)}</b>",
            ],
        )
