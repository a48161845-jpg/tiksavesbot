"""
Обработка нажатий на кнопки выбора качества (см. quality_state.py,
keyboards.quality_choice_kb) — второй шаг скачивания для YouTube/
Instagram/VK/Pinterest: сначала пробуем видео и показываем доступные
разрешения, тут уже качаем то, что выбрал пользователь.

callback_data: "q:<kind>:<height>:<req_id>", где kind:
  v — видео (height=0 значит "лучшее качество без ограничения");
  a — только звук (MP3);
  x — отмена.
"""
import contextlib
from pathlib import Path
from typing import Optional

from aiogram import F
from aiogram.types import CallbackQuery

from globals_state import dp
from config import YOUTUBE_MAX_VIDEO_BYTES, YOUTUBE_MAX_VIDEO_MB
from send_helpers import fit_video_to_limit
from helpers import html_escape, code, clamp_reason, exc_type_name
from storage import store
from i18n import tr
from user_label import resolve_user_label
from gates import gate_callback
from limiters import download_sem
from logging_channel import log_event, format_user_for_log
from quality_state import quality_pending, cleanup_quality_pending
from youtube_provider import download_media, download_audio_only
from external_send import send_external_video
from config import CAPTION_AUDIO
from aiogram.types import FSInputFile


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


@dp.callback_query(F.data.startswith("q:"))
async def quality_choice_callback(call: CallbackQuery):
    uid = call.from_user.id
    label = await resolve_user_label(call.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_callback(call, label):
        return

    data = call.data or ""
    parts = data.split(":", 3)
    if len(parts) != 4:
        await call.answer(tr(uid, "Что-то пошло не так."), show_alert=True)
        return
    _, kind, height_str, req_id = parts

    cleanup_quality_pending()
    st = quality_pending.get(req_id)
    if not st:
        await call.answer()
        with contextlib.suppress(Exception):
            await call.message.edit_text(tr(uid, "⌛ Время выбора качества истекло. Пришли ссылку ещё раз."))
        return

    if st["uid"] != uid:
        await call.answer(tr(uid, "Это не твой запрос."), show_alert=True)
        return

    quality_pending.pop(req_id, None)
    await call.answer()

    url = st["url"]
    platform = st["platform"]
    platform_name = st["platform_name"]
    emoji = st["emoji"]

    if kind == "x":
        with contextlib.suppress(Exception):
            await call.message.edit_text(tr(uid, "❌ Скачивание отменено."))
        return

    tmp_path: Optional[Path] = None
    status = call.message

    try:
        async with download_sem:
            if kind == "a":
                with contextlib.suppress(Exception):
                    await status.edit_text(tr(uid, "⬇️ Скачиваю звук…"))
                try:
                    tmp_path = await download_audio_only(url, Path("."))
                except Exception as e:
                    await _log_err(call.bot, platform, "audio_download", uid, label, url, e)
                    with contextlib.suppress(Exception):
                        await status.edit_text(tr(uid, "❌ Не получилось скачать звук с {p}.", p=platform_name))
                    return

                size = tmp_path.stat().st_size if tmp_path.exists() else 0
                if size <= 0:
                    with contextlib.suppress(Exception):
                        await status.edit_text(tr(uid, "❌ Скачанный файл пустой. Попробуй ещё раз."))
                    return

                with contextlib.suppress(Exception):
                    await status.edit_text(tr(uid, "📤 Отправляю…"))
                try:
                    await call.message.answer_audio(FSInputFile(tmp_path), caption=tr(uid, CAPTION_AUDIO), parse_mode="HTML")
                except Exception as e:
                    await _log_err(call.bot, platform, "audio_send", uid, label, url, e)
                    with contextlib.suppress(Exception):
                        await status.edit_text(tr(uid, "❌ Не удалось отправить звук."))
                    return

                store.inc_audio(uid, 1)
                with contextlib.suppress(Exception):
                    await status.delete()
                return

            # kind == "v"
            height = int(height_str) if height_str.isdigit() else 0
            quality_height = height if height > 0 else None
            quality_label = f"{height}p" if height > 0 else tr(uid, "лучшем доступном")

            with contextlib.suppress(Exception):
                await status.edit_text(tr(uid, "⬇️ Скачиваю в {q} качестве…", q=quality_label))

            try:
                tmp_path, dl_info = await download_media(url, Path("."), quality_height=quality_height)
            except Exception as e:
                await _log_err(call.bot, platform, "download", uid, label, url, e)
                with contextlib.suppress(Exception):
                    await status.edit_text(
                        tr(uid, "❌ Не получилось скачать в этом качестве с {p}. Попробуй другое качество или другую ссылку.", p=platform_name)
                    )
                return

            size = tmp_path.stat().st_size if tmp_path.exists() else 0
            if size <= 0:
                with contextlib.suppress(Exception):
                    await status.edit_text(tr(uid, "❌ Скачанный файл пустой. Попробуй ещё раз."))
                return
            if size > YOUTUBE_MAX_VIDEO_BYTES:
                with contextlib.suppress(Exception):
                    await status.edit_text(tr(uid, "🗜 Видео тяжёлое — сжимаю, чтобы влезло в Telegram…"))
                try:
                    fitted = await fit_video_to_limit(tmp_path)
                except Exception:
                    with contextlib.suppress(Exception):
                        await status.edit_text(
                            tr(uid, "❌ Файл в этом качестве больше лимита ({mb} МБ), а сжать его не получилось. Попробуй качество пониже.", mb=YOUTUBE_MAX_VIDEO_MB)
                        )
                    return
                with contextlib.suppress(Exception):
                    tmp_path.unlink(missing_ok=True)
                tmp_path = fitted

            with contextlib.suppress(Exception):
                await status.edit_text(tr(uid, "📤 Отправляю…"))

            try:
                await send_external_video(
                    call.message, uid, label, tmp_path, dl_info, dl_info, emoji=emoji, source=platform
                )
            except Exception as e:
                await _log_err(call.bot, platform, "send", uid, label, url, e)
                with contextlib.suppress(Exception):
                    await status.edit_text(
                        tr(uid, "❌ Telegram отклонил файл — скорее всего, он слишком большой для отправки ботом (лимит: {mb} МБ на файл).", mb=YOUTUBE_MAX_VIDEO_MB)
                    )
                return

            with contextlib.suppress(Exception):
                await status.delete()

    finally:
        if tmp_path:
            with contextlib.suppress(Exception):
                tmp_path.unlink(missing_ok=True)
