"""
Обработчик ссылок на Instagram (Reels/посты), VK (видео/клипы), Pinterest
(видео-пины), X (Twitter), Rutube и Reddit — через тот же движок, что и YouTube (yt-dlp, см.
youtube_provider.py). Регистрируется раньше main_handler.py (см.
handlers/__init__.py), поэтому такие ссылки перехватываются здесь и не
долетают до TikTok-хендлера.

Важная честная оговорка: все три площадки отдают только ПУБЛИЧНЫЙ контент
без входа в аккаунт — закрытые профили, приватные посты и некоторые Reels
могут не скачаться. Это ограничение самих площадок, а не бота. Pinterest
вообще в основном картинки — видео-пины скачаются, обычные фото-пины нет
(это не видео, yt-dlp их не обрабатывает).
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
from helpers import (
    html_escape,
    code,
    clamp_reason,
    exc_type_name,
    detect_other_platform,
    resolve_generic_redirect,
    extract_other_source_url,
)
from storage import store
from i18n import tr, get_lang
from user_label import resolve_user_label
from gates import gate_message
from limiters import lim, download_sem
from logging_channel import log_event, format_user_for_log
from strikes import add_download_strike
from youtube_provider import probe_media, list_qualities, ffmpeg_available
from quality_state import save_quality_pending
from quality_diagnostics import maybe_report_limited_quality
from picker_state import new_req_id
from keyboards import quality_choice_kb

PLATFORM_LABELS = {
    "instagram": ("📸", "Instagram"),
    "vk": ("🔵", "VK"),
    "pinterest": ("📌", "Pinterest"),
    "twitter": ("🐦", "X (Twitter)"),
    "rutube": ("🟣", "Rutube"),
    "reddit": ("👽", "Reddit"),
}


async def _log_err(bot, platform: str, stage: str, uid: int, label: str, url: str, e: Exception) -> None:
    with contextlib.suppress(Exception):
        store.inc_error(f"{platform}_{stage}", e)
    await log_event(
        bot,
        "dlerr",
        [
            f"❌ Категория: <b>Ошибка скачивания ({platform})</b>",
            f"👤 User/id: <b>{format_user_for_log(label, uid)}</b>",
            f"🧩 Стадия: <b>{html_escape(stage)}</b>",
            f"🧬 Тип: <b>{html_escape(exc_type_name(e))}</b>",
            f"🔗 Ссылка: {code(url)}",
            f"🧨 Причина: <b>{html_escape(clamp_reason(e))}</b>",
        ],
    )


def _detect_platform(text: str) -> Optional[str]:
    return detect_other_platform(text)


def _is_other_source_message(message: Message) -> bool:
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return False
    return _detect_platform(text) is not None


@dp.message(F.text, _is_other_source_message)
async def other_sources_handler(message: Message):
    uid = message.from_user.id
    text = (message.text or "").strip()
    platform = _detect_platform(text) or "other"
    emoji, platform_name = PLATFORM_LABELS.get(platform, ("📎", "источника"))

    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_message(message, label):
        return

    store.register(uid)

    url = extract_other_source_url(text) or text

    ok_dl, wait_dl = lim.dl_hit(uid)
    if not ok_dl:
        await message.answer(tr(message, MSG_DL, n=wait_dl))
        await add_download_strike(message.bot, uid, label, "Лимит скачиваний", src=url)
        return

    status = await message.answer(tr(message, "⏳ Смотрю {p}…", p=platform_name))
    tmp_path: Optional[Path] = None

    try:
        async with lim.user_dl_lock(uid), download_sem:
            try:
                info = await probe_media(url)
            except Exception as e:
                await _log_err(message.bot, platform, "probe", uid, label, url, e)
                with contextlib.suppress(Exception):
                    from error_explain import explain_user
                    await status.edit_text(tr(message, explain_user(clamp_reason(e), platform, url)))
                return

            duration = int(info.get("duration") or 0)
            if duration and duration > YOUTUBE_MAX_DURATION_SEC:
                with contextlib.suppress(Exception):
                    await status.edit_text(
                        tr(message, "❌ Видео слишком длинное ({m} мин). Лимит: {l} мин.",
                           m=duration // 60, l=YOUTUBE_MAX_DURATION_SEC // 60)
                    )
                return

            qualities = list_qualities(info)
            with contextlib.suppress(Exception):
                await maybe_report_limited_quality(message.bot, platform, url, info, qualities)
            req_id = new_req_id()
            save_quality_pending(
                req_id,
                uid=uid,
                url=url,
                platform=platform,
                platform_name=platform_name,
                emoji=emoji,
                duration=duration,
                qualities=qualities,
            )

            with contextlib.suppress(Exception):
                note = (
                    ""
                    if ffmpeg_available()
                    else tr(message, "\n\n⚠️ На сервере не найден ffmpeg — реально скачается максимум ~720p, даже если выбрать качество выше.")
                )
                await status.edit_text(
                    tr(message, "🎞️ <b>Выбери качество видео</b>\n\nЧем выше качество — тем дольше скачивание и больше файл.")
                    + note,
                    parse_mode="HTML",
                    reply_markup=quality_choice_kb(req_id, qualities, get_lang(uid)),
                )

    finally:
        if tmp_path:
            with contextlib.suppress(Exception):
                tmp_path.unlink(missing_ok=True)
