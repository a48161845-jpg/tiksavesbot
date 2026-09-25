"""
Обработчик ссылок на YouTube (обычные видео и Shorts) — качаем через yt-dlp.

Отдельно от TikTok-пайплайна (main_handler.py): у YouTube другая природа —
нет пикера фото, нет отдельного "музыка из TikTok", видео может быть куда
длиннее и тяжелее. Регистрируется РАНЬШЕ main_handler.py (см. handlers/__init__.py),
поэтому YouTube-ссылки перехватываются здесь и не долетают до TikTok-хендлера.
"""
import contextlib
from pathlib import Path
from typing import Optional

from aiogram import F
from aiogram.types import Message

from globals_state import dp
from config import (
    MSG_DL,
    YOUTUBE_MAX_DURATION_SEC,
)
from helpers import html_escape, code, clamp_reason, exc_type_name, is_youtube, extract_youtube_url, normalize_youtube_url
from storage import store
from user_label import resolve_user_label
from gates import gate_message
from limiters import lim, download_sem
from logging_channel import log_event, format_user_for_log
from strikes import add_download_strike
from youtube_provider import probe_youtube, list_qualities, ffmpeg_available
from quality_state import save_quality_pending
from quality_diagnostics import maybe_report_limited_quality
from picker_state import new_req_id
from keyboards import quality_choice_kb


async def _log_yt_err(bot, stage: str, uid: int, label: str, url: str, e: Exception) -> None:
    with contextlib.suppress(Exception):
        store.inc_error(f"youtube_{stage}", e)
    await log_event(
        bot,
        "dlerr",
        [
            "❌ Категория: <b>Ошибка скачивания (YouTube)</b>",
            f"👤 User/id: <b>{format_user_for_log(label, uid)}</b>",
            f"🧩 Стадия: <b>{html_escape(stage)}</b>",
            f"🧬 Тип: <b>{html_escape(exc_type_name(e))}</b>",
            f"🔗 Ссылка: {code(url)}",
            f"🧨 Причина: <b>{html_escape(clamp_reason(e))}</b>",
        ],
    )


def _is_youtube_message(message: Message) -> bool:
    text = (message.text or "").strip()
    return bool(text) and not text.startswith("/") and is_youtube(text)


@dp.message(F.text, _is_youtube_message)
async def youtube_handler(message: Message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_message(message, label):
        return

    store.register(uid)

    url = normalize_youtube_url(extract_youtube_url(text) or text)

    ok_dl, wait_dl = lim.dl_hit(uid)
    if not ok_dl:
        await message.answer(MSG_DL.format(n=wait_dl))
        await add_download_strike(message.bot, uid, label, "Лимит скачиваний", src=url)
        return

    status = await message.answer("⏳ Смотрю видео на YouTube…")
    tmp_path: Optional[Path] = None

    try:
        async with lim.user_dl_lock(uid), download_sem:
            try:
                info = await probe_youtube(url)
            except Exception as e:
                await _log_yt_err(message.bot, "probe", uid, label, url, e)
                with contextlib.suppress(Exception):
                    await status.edit_text("❌ Не удалось получить это видео. Проверь ссылку — может, оно приватное/удалено.")
                return

            duration = int(info.get("duration") or 0)
            if duration and duration > YOUTUBE_MAX_DURATION_SEC:
                with contextlib.suppress(Exception):
                    await status.edit_text(
                        f"❌ Видео слишком длинное ({duration // 60} мин). "
                        f"Лимит: {YOUTUBE_MAX_DURATION_SEC // 60} мин."
                    )
                return

            qualities = list_qualities(info)
            with contextlib.suppress(Exception):
                await maybe_report_limited_quality(message.bot, "youtube", url, info, qualities)
            req_id = new_req_id()
            save_quality_pending(
                req_id,
                uid=uid,
                url=url,
                platform="youtube",
                platform_name="YouTube",
                emoji="🎬",
                duration=duration,
                qualities=qualities,
            )

            with contextlib.suppress(Exception):
                note = (
                    ""
                    if ffmpeg_available()
                    else "\n\n⚠️ На сервере не найден ffmpeg — реально скачается максимум ~720p, "
                    "даже если выбрать качество выше (YouTube не отдаёт готовые файлы в высоком "
                    "качестве без склейки видео и звука)."
                )
                await status.edit_text(
                    "🎞️ <b>Выбери качество видео</b>\n\nЧем выше качество — тем дольше скачивание и больше файл."
                    + note,
                    parse_mode="HTML",
                    reply_markup=quality_choice_kb(req_id, qualities),
                )

    finally:
        if tmp_path:
            with contextlib.suppress(Exception):
                tmp_path.unlink(missing_ok=True)
