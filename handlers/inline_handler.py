"""
Inline-режим: @tiksavesbot <ссылка> прямо в любом чате.

Важно про архитектуру: изначально это было сделано через плейсхолдер +
chosen_inline_result (Telegram даёт inline_message_id, которым можно
отредактировать уже отправленное сообщение). НО chosen_inline_result
на практике ненадёжен: Telegram присылает эти апдейты только если явно
включить "Inline Feedback" через @BotFather (/setinlinefeedback), и даже
тогда — не гарантированно на каждый выбор, а с какой-то вероятностью.
Из-за этого плейсхолдер "⏳ Скачиваю..." мог просто никогда не замениться
на видео. Поэтому теперь всё качается СРАЗУ, синхронно, внутри самого
inline_query, с жёстким таймаутом — если не успели, аккуратно сообщаем
об этом вместо того, чтобы врать зависшим "загружаю".

Оптимизация: если ссылка уже когда-то скачивалась через инлайн — результат
подставляется МГНОВЕННО через кэш file_id (Telegram file_id у бота не
протухают), без повторного скачивания вообще — именно это и делает инлайн
режим практичным при не-мгновенном скачивании новых ссылок.

⚠️ Чтобы инлайн-режим вообще заработал, нужно один раз включить его для бота
через @BotFather → /setinline (это ручная настройка бота, не делается кодом).
"""
import asyncio
import contextlib
import hashlib
import uuid
from pathlib import Path
from typing import Optional

from aiogram.types import (
    InlineQuery,
    InlineQueryResultCachedVideo,
    InlineQueryResultArticle,
    InputTextMessageContent,
    FSInputFile,
)

from globals_state import dp
import globals_state
import os
from config import INLINE_CACHE_CHANNEL_ID, MAX_VIDEO_BYTES, CAPTION_VIDEO, YOUTUBE_MAX_DURATION_SEC, DOWNLOAD_HARD_CAP_BYTES, COMPRESS_OVER_LIMIT
from helpers import (
    is_tiktok, extract_tiktok_url, normalize_tiktok_url,
    is_youtube, extract_youtube_url, normalize_youtube_url,
    is_instagram, is_vk, is_pinterest, extract_other_source_url,
)
from storage import store
from user_label import resolve_user_label
from limiters import lim
from youtube_provider import probe_media, download_media
from download_nudge import after_download_hooks
from logging_channel import log_event, format_user_for_log
from helpers import html_escape, code, clamp_reason, exc_type_name
from send_helpers import fit_video_to_limit
from youtube_provider import ffmpeg_available

# Сколько максимум ждём скачивание НОВОЙ (некэшированной) ссылки внутри
# самого inline-запроса, пока Telegram-клиент ждёт ответа.
# Telegram даёт на ответ ~10 сек, поэтому ждём чуть меньше. Само скачивание при
# этом НЕ отменяется (раньше wait_for убивал его, и видео не появлялось никогда):
# оно доделывается в фоне, кладёт file_id в кэш, и повторный запрос отвечает мгновенно.
INLINE_TIMEOUT_SEC = float(os.getenv("INLINE_TIMEOUT_SEC", "7"))

# Фоновые скачивания: ключ кэша -> Task (дедупликация — одна ссылка не качается дважды).
_inflight: dict = {}
# Ошибки последних фоновых скачиваний: ключ -> короткий текст для пользователя.
_failed: dict = {}


def _cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:24]


def _detect(text: str):
    """Возвращает (platform, normalized_url) или (None, None)."""
    if is_tiktok(text):
        u = extract_tiktok_url(text)
        if u:
            return "tiktok", normalize_tiktok_url(u)
    if is_youtube(text):
        u = extract_youtube_url(text)
        if u:
            return "youtube", normalize_youtube_url(u)
    if is_instagram(text) or is_vk(text) or is_pinterest(text):
        u = extract_other_source_url(text)
        if u:
            platform = "instagram" if is_instagram(u) else ("vk" if is_vk(u) else "pinterest")
            return platform, u
    return None, None


async def _resolve_and_download(platform: str, url: str, out_dir: Path) -> Path:
    """Возвращает путь к скачанному видео. Бросает исключение при неудаче."""
    if platform == "tiktok":
        switcher = globals_state.g_switcher
        if not switcher:
            raise RuntimeError("provider switcher не инициализирован")
        media, provider = await switcher.get_media(url, raw_url=url)
        # Важно: проверяем именно media.photos, а не только media.video —
        # у tikwm для фото-постов (нет отдельного видео) поле "play"/"wmplay"
        # иногда оказывается заполнено ссылкой на МУЗЫКУ поста (это баг их
        # API, не наш) — раньше это приводило к тому, что инлайн вместо
        # видео "скачивал" и присылал музыку под видом видео.
        if media.photos or not media.video:
            raise RuntimeError("Это фото-слайдшоу — инлайн поддерживает только видео")
        tmp_path = out_dir / f"inline_{uuid.uuid4().hex[:10]}.mp4"
        can_compress = COMPRESS_OVER_LIMIT and ffmpeg_available()
        await provider.download_to_file(
            media.video, tmp_path,
            max(MAX_VIDEO_BYTES, DOWNLOAD_HARD_CAP_BYTES) if can_compress else MAX_VIDEO_BYTES,
            stage="inline_video",
        )
        return tmp_path

    info = await probe_media(url)
    duration = int(info.get("duration") or 0)
    if duration and duration > YOUTUBE_MAX_DURATION_SEC:
        raise RuntimeError(f"Видео длиннее {YOUTUBE_MAX_DURATION_SEC // 60} мин — не поддерживается в инлайне")
    # В инлайне важна скорость — берём до 720p (дальше бот всё равно сожмёт под лимит).
    path, _dl_info = await download_media(url, out_dir, quality_height=720)
    return path


async def _download_and_cache(platform: str, url: str, uid: int) -> str:
    """Качает видео, кладёт в ТЕХНИЧЕСКИЙ канал (не логи!) чтобы получить file_id, и кэширует. Возвращает file_id."""
    if not INLINE_CACHE_CHANNEL_ID:
        raise RuntimeError(
            "Инлайн-режим не настроен: не задан INLINE_CACHE_CHANNEL_ID "
            "(отдельный технический канал, НЕ канал логов — см. .env)"
        )

    tmp_path: Optional[Path] = None
    try:
        tmp_path = await _resolve_and_download(platform, url, Path("."))

        size = tmp_path.stat().st_size if tmp_path.exists() else 0
        if size <= 0:
            raise RuntimeError("Скачанный файл пустой")
        if size > MAX_VIDEO_BYTES:
            fitted = await fit_video_to_limit(tmp_path)
            if fitted != tmp_path:
                with contextlib.suppress(Exception):
                    tmp_path.unlink(missing_ok=True)
                tmp_path = fitted

        bot = globals_state.g_provider.bot if globals_state.g_provider else None
        if not bot:
            raise RuntimeError("bot недоступен")

        # Кладём в ОТДЕЛЬНЫЙ технический канал (не в лог-канал!), чтобы
        # получить постоянный file_id — его же используем и для ответа
        # сейчас, и для кэша на будущее (повторные запросы этой ссылки
        # больше не будут качать заново). В админ-логи это НЕ попадает.
        cache_msg = await bot.send_video(INLINE_CACHE_CHANNEL_ID, FSInputFile(tmp_path))
        file_id = cache_msg.video.file_id
        store.set_inline_cache(_cache_key(url), file_id, kind="video")

        label = await resolve_user_label(bot, uid)
        store.set_user_label(uid, label)
        store.inc_download(uid, "video", items=1, source=platform)
        with contextlib.suppress(Exception):
            await after_download_hooks(bot, uid, label)

        return file_id
    finally:
        if tmp_path:
            with contextlib.suppress(Exception):
                tmp_path.unlink(missing_ok=True)


@dp.inline_query()
async def inline_handler(inline_query: InlineQuery):
    uid = inline_query.from_user.id
    query = (inline_query.query or "").strip()

    ban = store.get_ban(uid)
    if ban:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    if not query:
        hint = InlineQueryResultArticle(
            id="hint",
            title="Вставь ссылку на TikTok / YouTube / Instagram / VK / Pinterest",
            description="Начни печатать — бот покажет результат прямо тут",
            input_message_content=InputTextMessageContent(
                message_text="📎 Пришли мне ссылку на TikTok, YouTube, Instagram, VK или Pinterest — скачаю видео."
            ),
        )
        await inline_query.answer([hint], cache_time=1, is_personal=True)
        return

    platform, url = _detect(query)
    if not url:
        not_found = InlineQueryResultArticle(
            id="notfound",
            title="Ссылка не распознана",
            description="Поддерживаются TikTok, YouTube, Instagram, VK, Pinterest",
            input_message_content=InputTextMessageContent(message_text="❌ Не нашёл поддерживаемую ссылку в запросе."),
        )
        await inline_query.answer([not_found], cache_time=1, is_personal=True)
        return

    key = _cache_key(url)
    cached = store.get_inline_cache(key)
    if cached and cached.get("file_id"):
        result = InlineQueryResultCachedVideo(
            id=f"c:{key}",
            video_file_id=cached["file_id"],
            title="✅ Готово — отправить видео",
            caption=CAPTION_VIDEO,
            parse_mode="HTML",
        )
        await inline_query.answer([result], cache_time=300, is_personal=False)
        return

    # Уже качается (этим или другим пользователем) — просто подключаемся к задаче.
    task = _inflight.get(key)
    if task is None:
        ok_dl, _wait = lim.dl_hit(uid)
        if not ok_dl:
            limited = InlineQueryResultArticle(
                id="ratelimited",
                title="⏳ Слишком много запросов подряд",
                description="Попробуй через минуту",
                input_message_content=InputTextMessageContent(message_text="⏳ Слишком много запросов подряд — попробуй через минуту."),
            )
            await inline_query.answer([limited], cache_time=1, is_personal=True)
            return

        _failed.pop(key, None)
        task = asyncio.create_task(_background_download(key, platform, url, uid, inline_query.bot))
        task.add_done_callback(lambda t: t.cancelled() or t.exception())
        _inflight[key] = task

    try:
        # shield: таймаут ожидания НЕ отменяет само скачивание.
        file_id = await asyncio.wait_for(asyncio.shield(task), timeout=INLINE_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        slow = InlineQueryResultArticle(
            id=f"slow:{key}",
            title="⏳ Видео скачивается…",
            description="Подожди ~10 сек и поменяй запрос (добавь/убери пробел) — видео будет готово мгновенно",
            input_message_content=InputTextMessageContent(
                message_text="⏳ Видео ещё скачивается. Повтори запрос через несколько секунд — "
                "оно уже будет в кэше и отправится мгновенно. Или пришли ссылку боту в чат."
            ),
        )
        await inline_query.answer([slow], cache_time=1, is_personal=True)
        return
    except Exception:
        reason = _failed.get(key) or "Не получилось скачать это видео"
        failed = InlineQueryResultArticle(
            id=f"failed:{key}",
            title="❌ Не получилось скачать это видео",
            description=reason[:100],
            input_message_content=InputTextMessageContent(
                message_text=f"❌ {reason}. Попробуй прислать ссылку боту напрямую в чат."
            ),
        )
        await inline_query.answer([failed], cache_time=1, is_personal=True)
        return

    result = InlineQueryResultCachedVideo(
        id=f"n:{key}",
        video_file_id=file_id,
        title="✅ Готово — отправить видео",
        caption=CAPTION_VIDEO,
        parse_mode="HTML",
    )
    await inline_query.answer([result], cache_time=300, is_personal=False)


async def _background_download(key: str, platform: str, url: str, uid: int, bot) -> str:
    """Скачивание, переживающее таймаут inline-запроса. Ошибки логируются (раньше глотались молча)."""
    try:
        return await _download_and_cache(platform, url, uid)
    except Exception as e:
        low = str(e).lower()
        if "file too large" in low or "файл больше" in low:
            _failed[key] = "Видео слишком тяжёлое для инлайна"
        elif "слайдшоу" in low:
            _failed[key] = "Это фото-слайдшоу — в инлайне только видео"
        elif "не настроен" in low:
            _failed[key] = "Инлайн-режим не настроен (INLINE_CACHE_CHANNEL_ID)"
        else:
            _failed[key] = "Не удалось скачать (приватное/недоступное видео?)"
        with contextlib.suppress(Exception):
            await log_event(
                bot,
                "dlerr",
                [
                    f"❌ Категория: <b>Ошибка инлайн-режима ({html_escape(platform)})</b>",
                    f"👤 User/id: <b>{format_user_for_log(str(uid), uid)}</b>",
                    f"🧬 Тип: <b>{html_escape(exc_type_name(e))}</b>",
                    f"🔗 Ссылка: {code(url)}",
                    f"🧨 Причина: <b>{html_escape(clamp_reason(e))}</b>",
                ],
            )
        raise
    finally:
        _inflight.pop(key, None)
        # чтобы _failed не рос бесконечно
        if len(_failed) > 500:
            _failed.clear()
