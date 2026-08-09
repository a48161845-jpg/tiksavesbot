"""
TikTok через yt-dlp.

Используется вместо TikWM для скачивания TikTok-видео.
yt-dlp сам определяет TikTok по URL.
"""

import contextlib
from pathlib import Path
from typing import Optional

from aiogram import F
from aiogram.types import Message

from globals_state import dp
from config import MSG_DL, MAX_VIDEO_BYTES, MAX_VIDEO_MB, CAPTION_VIDEO
from helpers import (
    html_escape,
    code,
    clamp_reason,
    exc_type_name,
    extract_tiktok_url,
    normalize_tiktok_url,
)
from storage import store
from user_label import resolve_user_label
from gates import gate_message
from limiters import lim, download_sem
from logging_channel import log_event, format_user_for_log
from strikes import add_download_strike
from youtube_provider import probe_media, download_media
from send_helpers import send_video_smart
from picker_state import new_req_id
from keyboards import under_video_kb
from referral import after_download_hooks


async def _log_error(
    bot,
    uid: int,
    label: str,
    url: str,
    stage: str,
    e: Exception,
):
    with contextlib.suppress(Exception):
        store.inc_error(f"tiktok_ytdlp_{stage}", e)

    await log_event(
        bot,
        "dlerr",
        [
            "❌ Категория: <b>Ошибка скачивания TikTok через yt-dlp</b>",
            f"👤 User/id: <b>{format_user_for_log(label, uid)}</b>",
            f"🧩 Стадия: <b>{html_escape(stage)}</b>",
            f"🧬 Тип: <b>{html_escape(exc_type_name(e))}</b>",
            f"🔗 Ссылка: {code(url)}",
            f"🧨 Причина: <b>{html_escape(clamp_reason(e))}</b>",
        ],
    )


def _is_tiktok_message(message: Message) -> bool:
    text = (message.text or "").strip()

    if not text or text.startswith("/"):
        return False

    return bool(extract_tiktok_url(text))


@dp.message(F.text, _is_tiktok_message)
async def tiktok_ytdlp_handler(message: Message):
    uid = message.from_user.id
    text = (message.text or "").strip()

    label = await resolve_user_label(message.bot, uid)
    store.set_user_label(uid, label)

    if not await gate_message(message, label):
        return

    store.register(uid)

    url = extract_tiktok_url(text)
    if not url:
        return

    url = normalize_tiktok_url(url)

    ok_dl, wait_dl = lim.dl_hit(uid)
    if not ok_dl:
        await message.answer(MSG_DL.format(n=wait_dl))
        await add_download_strike(
            message.bot,
            uid,
            label,
            "Лимит скачиваний",
            src=url,
        )
        return

    status = await message.answer("⏳ Скачиваю TikTok…")
    tmp_path: Optional[Path] = None

    try:
        async with download_sem:

            # Получаем информацию о видео
            try:
                info = await probe_media(url)
            except Exception as e:
                await _log_error(
                    message.bot,
                    uid,
                    label,
                    url,
                    "probe",
                    e,
                )

                with contextlib.suppress(Exception):
                    await status.edit_text(
                        "❌ Не удалось получить информацию о TikTok-видео. "
                        "Попробуй другую ссылку."
                    )
                return

            # Скачивание
            with contextlib.suppress(Exception):
                await status.edit_text("⬇️ Скачиваю TikTok-видео…")

            try:
                tmp_path, dl_info = await download_media(
                    url,
                    Path("."),
                )
            except Exception as e:
                await _log_error(
                    message.bot,
                    uid,
                    label,
                    url,
                    "download",
                    e,
                )

                with contextlib.suppress(Exception):
                    await status.edit_text(
                        "❌ Не получилось скачать TikTok-видео.\n"
                        "Попробуй ещё раз или отправь другую ссылку."
                    )
                return

            # Проверка файла
            if not tmp_path.exists():
                raise RuntimeError(
                    "yt-dlp: скачанный файл не найден"
                )

            size = tmp_path.stat().st_size

            if size <= 0:
                raise RuntimeError(
                    "yt-dlp: скачанный файл пустой"
                )

            if size > MAX_VIDEO_BYTES:
                with contextlib.suppress(Exception):
                    await status.edit_text(
                        f"❌ Файл больше лимита ({MAX_VIDEO_MB} МБ)."
                    )
                return

            with contextlib.suppress(Exception):
                await status.edit_text("📤 Отправляю…")

            # yt-dlp уже скачал готовый файл.
            # Provider для send_video_smart здесь не нужен,
            # поэтому передаём None.
            try:
                await send_video_smart(
                    message,
                    None,
                    str(tmp_path),
                    CAPTION_VIDEO,
                    status_msg=status,
                    reply_markup=under_video_kb(
                        has_music=False,
                        has_description=False,
                        req_id=new_req_id(),
                    ),
                )
            except Exception as e:
                await _log_error(
                    message.bot,
                    uid,
                    label,
                    url,
                    "send",
                    e,
                )

                with contextlib.suppress(Exception):
                    await status.edit_text(
                        "❌ Не удалось отправить видео в Telegram."
                    )
                return

            store.inc_download(
                uid,
                "video",
                items=1,
                source="tiktok",
            )

            await after_download_hooks(
                message.bot,
                uid,
                label,
            )

            with contextlib.suppress(Exception):
                await status.delete()

            await log_event(
                message.bot,
                "videodl",
                [
                    "🎬 Категория: <b>Скачивание TikTok через yt-dlp</b>",
                    f"👤 User/id: <b>{format_user_for_log(label, uid)}</b>",
                    f"🔗 Ссылка: {code(url)}",
                ],
            )

    except Exception as e:
        await _log_error(
            message.bot,
            uid,
            label,
            url,
            "handler",
            e,
        )

        with contextlib.suppress(Exception):
            await status.edit_text(
                "❌ Не удалось скачать видео. Попробуй позже."
            )

    finally:
        if tmp_path:
            with contextlib.suppress(Exception):
                tmp_path.unlink(missing_ok=True)
