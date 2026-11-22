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
import re
import uuid
from pathlib import Path
from typing import Optional

from aiogram.types import (
    InlineQuery,
    InlineQueryResultCachedVideo,
    InlineQueryResultCachedPhoto,
    InlineQueryResultArticle,
    InputTextMessageContent,
    FSInputFile,
)

from core.globals_state import dp
from core import globals_state
import os
from core.config import INLINE_CACHE_CHANNEL_ID, MAX_VIDEO_BYTES, CAPTION_VIDEO, CAPTION_PHOTO, YOUTUBE_MAX_DURATION_SEC, DOWNLOAD_HARD_CAP_BYTES, COMPRESS_OVER_LIMIT
from core.helpers import (
    is_tiktok, extract_tiktok_url, normalize_tiktok_url,
    is_youtube, extract_youtube_url, normalize_youtube_url,
    detect_other_platform, extract_other_source_url,
)
from core.storage import store
from i18n import tr
from core.user_label import resolve_user_label
from core.limiters import lim
from downloaders.youtube_provider import probe_media, download_media
from core.download_nudge import after_download_hooks
from core.logging_channel import log_event, format_user_for_log
from core.helpers import html_escape, code, clamp_reason, exc_type_name
from ui.send_helpers import fit_video_to_limit
from downloaders.video_meta import prepare_video_kwargs, cleanup_video_kwargs, telegram_kwargs
from downloaders.youtube_provider import ffmpeg_available
from downloaders.photo_crop import RATIO_TITLES, normalize_ratio, crop_image

# Сколько максимум ждём скачивание НОВОЙ (некэшированной) ссылки внутри
# самого inline-запроса, пока Telegram-клиент ждёт ответа.
# Telegram даёт на ответ ~10 сек, поэтому ждём чуть меньше. Само скачивание при
# этом НЕ отменяется (раньше wait_for убивал его, и видео не появлялось никогда):
# оно доделывается в фоне, кладёт file_id в кэш, и повторный запрос отвечает мгновенно.
INLINE_TIMEOUT_SEC = float(os.getenv("INLINE_TIMEOUT_SEC", "7"))

# Сколько кадров фото-поста отдаём в inline (Telegram разрешает до 50 результатов, но каждый кадр — это
# скачивание + загрузка в технический канал, поэтому по умолчанию 10).
INLINE_PHOTO_LIMIT = max(1, min(50, int(os.getenv("INLINE_PHOTO_LIMIT", "10"))))
_PHOTO_MAX_BYTES = 15 * 1024 * 1024

# Фоновые скачивания: ключ кэша -> Task (дедупликация — одна ссылка не качается дважды).
_inflight: dict = {}
# Ошибки последних фоновых скачиваний: ключ -> короткий текст для пользователя.
_failed: dict = {}


def _cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:24]


def _photo_key(url: str, ratio: str = "orig") -> str:
    """Ключ кэша кадров фото-поста: у каждого формата (1:1, 4:3, ...) свой набор file_id."""
    return f"{_cache_key(url)}-{normalize_ratio(ratio)}-p"


_FORMAT_RE = re.compile(r"(?:^|\s)(1[:x]1|4[:x]3|3[:x]4|16[:x]9|9[:x]16)\s*$", re.I)


def split_format(query: str) -> tuple:
    """'ссылка 4:3' -> ('ссылка', '4x3'); без формата -> (query, 'orig')."""
    m = _FORMAT_RE.search(query or "")
    if not m:
        return (query or "").strip(), "orig"
    code = m.group(1).lower().replace(":", "x")
    return query[: m.start()].strip(), normalize_ratio(code)


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
    u = extract_other_source_url(text)
    if u:
        platform = detect_other_platform(u)
        if platform:
            return platform, u
    return None, None


async def _resolve_and_download(platform: str, url: str, out_dir: Path, pre=None) -> Path:
    """Возвращает путь к скачанному видео. Бросает исключение при неудаче. pre — уже полученные (media, provider)."""
    if platform == "tiktok":
        if pre is None:
            switcher = globals_state.g_switcher
            if not switcher:
                raise RuntimeError("provider switcher не инициализирован")
            pre = await switcher.get_media(url, raw_url=url)
        media, provider = pre
        # Фото-посты сюда не попадают (их обрабатывает _cache_photos). Проверяем именно media.photos,
        # а не только media.video: у tikwm для фото-постов поле "play" бывает заполнено ссылкой на МУЗЫКУ.
        if media.photos or not media.video:
            raise RuntimeError("В посте нет видео")
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
    # В инлайне важна скорость — берём до ~720p для вертикальных Shorts (height 1280) и до 1080p для горизонтальных; тяжёлое бот сожмёт под лимит.
    path, _dl_info = await download_media(url, out_dir, quality_height=1280)
    return path


_cache_warned = False


def _warn_cache_channel_once(e: Exception) -> None:
    global _cache_warned
    if not _cache_warned:
        _cache_warned = True
        import logging
        logging.getLogger(__name__).warning(
            "INLINE_CACHE_CHANNEL_ID=%s недоступен (%s). Проверь ID (формат -100...) и что бот — админ канала. "
            "Пока кэшируем через личный чат пользователя.", INLINE_CACHE_CHANNEL_ID, e,
        )


async def _upload_photo_for_file_id(bot, uid: int, path: Path) -> str:
    """Заливает фото в технический канал (или в личку с мгновенным удалением) и возвращает постоянный file_id."""
    try:
        if not INLINE_CACHE_CHANNEL_ID:
            raise RuntimeError("chat not found: INLINE_CACHE_CHANNEL_ID не задан")
        msg = await bot.send_photo(INLINE_CACHE_CHANNEL_ID, FSInputFile(path))
    except Exception as ce:
        low = str(ce).lower()
        if not any(x in low for x in ("chat not found", "forbidden", "not enough rights", "have no rights", "kicked")):
            raise
        msg = await bot.send_photo(uid, FSInputFile(path), disable_notification=True)
        with contextlib.suppress(Exception):
            await bot.delete_message(uid, msg.message_id)
        _warn_cache_channel_once(ce)
    return msg.photo[-1].file_id


async def _cache_photos(media, provider, url: str, uid: int, ratio: str, bot) -> list:
    """Качает кадры фото-поста (до INLINE_PHOTO_LIMIT), при необходимости обрезает под формат и кэширует file_id."""
    photos = list(media.photos)[:INLINE_PHOTO_LIMIT]
    sem = asyncio.Semaphore(3)

    async def one(i: int, purl: str) -> Optional[str]:
        raw = Path(f"inline_{uuid.uuid4().hex[:10]}_{i}.jpg")
        cropped: Optional[Path] = None
        async with sem:
            try:
                await provider.download_to_file(purl, raw, _PHOTO_MAX_BYTES, stage="inline_photo")
                send_path = raw
                if ratio != "orig":
                    cropped = raw.with_name(raw.stem + f"_{ratio}.jpg")
                    try:
                        send_path = await crop_image(raw, cropped, ratio)
                    except Exception:
                        send_path = raw  # не обрезалось — отдаём оригинал, а не теряем кадр
                return await _upload_photo_for_file_id(bot, uid, send_path)
            except Exception:
                return None
            finally:
                for f in (raw, cropped):
                    if f:
                        with contextlib.suppress(Exception):
                            f.unlink(missing_ok=True)

    got = await asyncio.gather(*(one(i, u) for i, u in enumerate(photos)))
    return [fid for fid in got if fid]


async def _download_and_cache(platform: str, url: str, uid: int, ratio: str = "orig") -> tuple:
    """
    Качает ссылку и кладёт в ТЕХНИЧЕСКИЙ канал (не логи!), чтобы получить file_id, и кэширует.
    Возвращает ("video", [file_id]) или ("photos", [file_id, ...]).
    """
    tmp_path: Optional[Path] = None
    try:
        pre = None
        if platform == "tiktok":
            switcher = globals_state.g_switcher
            if not switcher:
                raise RuntimeError("provider switcher не инициализирован")
            pre = await switcher.get_media(url, raw_url=url)
            media, provider = pre
            if media.photos:
                bot = globals_state.g_provider.bot if globals_state.g_provider else None
                if not bot:
                    raise RuntimeError("bot недоступен")
                ids = await _cache_photos(media, provider, url, uid, ratio, bot)
                if not ids:
                    raise RuntimeError("Не удалось скачать фото")
                store.set_inline_cache(_photo_key(url, ratio), ids[0], kind="photos", ids=ids)
                label = await resolve_user_label(bot, uid)
                store.set_user_label(uid, label)
                store.inc_download(uid, "photo", items=len(ids), source=platform, url=url)
                with contextlib.suppress(Exception):
                    await after_download_hooks(bot, uid, label)
                return "photos", ids

        tmp_path = await _resolve_and_download(platform, url, Path("."), pre=pre)

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
        meta = await prepare_video_kwargs(tmp_path)
        try:
            cache_msg = None
            kw = telegram_kwargs(meta)
            try:
                if not INLINE_CACHE_CHANNEL_ID:
                    raise RuntimeError("chat not found: INLINE_CACHE_CHANNEL_ID не задан")
                cache_msg = await bot.send_video(INLINE_CACHE_CHANNEL_ID, FSInputFile(tmp_path), **kw)
            except Exception as ce:
                low = str(ce).lower()
                if not any(x in low for x in ("chat not found", "forbidden", "not enough rights", "have no rights", "kicked")):
                    raise
                # Технический канал недоступен (неверный ID / бот не админ канала) —
                # получаем file_id через личный чат с пользователем и тут же удаляем сообщение.
                cache_msg = await bot.send_video(uid, FSInputFile(tmp_path), disable_notification=True, **kw)
                with contextlib.suppress(Exception):
                    await bot.delete_message(uid, cache_msg.message_id)
                _warn_cache_channel_once(ce)
        finally:
            cleanup_video_kwargs(meta)
        file_id = cache_msg.video.file_id
        store.set_inline_cache(_cache_key(url), file_id, kind="video")

        label = await resolve_user_label(bot, uid)
        store.set_user_label(uid, label)
        store.inc_download(uid, "video", items=1, source=platform, url=url)
        with contextlib.suppress(Exception):
            await after_download_hooks(bot, uid, label)

        return "video", [file_id]
    finally:
        if tmp_path:
            with contextlib.suppress(Exception):
                tmp_path.unlink(missing_ok=True)


def _video_result(uid: int, rid: str, file_id: str) -> InlineQueryResultCachedVideo:
    return InlineQueryResultCachedVideo(
        id=rid,
        video_file_id=file_id,
        title=tr(uid, "✅ Готово — отправить видео"),
        caption=tr(uid, CAPTION_VIDEO),
        parse_mode="HTML",
    )


def _photo_results(uid: int, pkey: str, ids: list, ratio: str) -> list:
    """По результату на каждый кадр: inline не умеет альбомы — пользователь выбирает кадры по одному."""
    n = len(ids)
    suffix = f" · {RATIO_TITLES[ratio]}" if ratio in RATIO_TITLES else ""
    return [
        InlineQueryResultCachedPhoto(
            id=f"p:{pkey}:{i}",
            photo_file_id=fid,
            title=tr(uid, "🖼 Фото {i} из {n}", i=i + 1, n=n) + suffix,
            description=tr(uid, "Нажми — кадр отправится в чат"),
            caption=tr(uid, CAPTION_PHOTO),
            parse_mode="HTML",
        )
        for i, fid in enumerate(ids)
    ]


def _results_for(uid: int, key: str, pkey: str, kind: str, ids: list, ratio: str) -> list:
    if kind == "photos":
        return _photo_results(uid, pkey, ids, ratio)
    return [_video_result(uid, f"c:{key}", ids[0])]


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
            title=tr(uid, "🔗 Вставь ссылку на видео или фото"),
            description=tr(uid, "TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube, Reddit. Для фото добавь формат: 1:1, 4:3, 3:4, 16:9, 9:16"),
            input_message_content=InputTextMessageContent(
                message_text=tr(uid, "📎 Пришли мне ссылку на TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube или Reddit — скачаю видео и фото без водяных знаков.\n\nВ inline-режиме: @tiksavesbot ссылка. Для фото можно добавить формат кадра: 1:1, 4:3, 3:4, 16:9 или 9:16.")
            ),
        )
        await inline_query.answer([hint], cache_time=1, is_personal=True)
        return

    query, ratio = split_format(query)
    platform, url = _detect(query)
    if not url:
        not_found = InlineQueryResultArticle(
            id="notfound",
            title=tr(uid, "Ссылка не распознана"),
            description=tr(uid, "Поддерживаются TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube, Reddit"),
            input_message_content=InputTextMessageContent(message_text=tr(uid, "❌ Не нашёл поддерживаемую ссылку в запросе.")),
        )
        await inline_query.answer([not_found], cache_time=1, is_personal=True)
        return

    if platform != "tiktok":
        ratio = "orig"  # формат кадра имеет смысл только для фото TikTok
    key = _cache_key(url)
    pkey = _photo_key(url, ratio)

    # Кэш: видео (по ссылке) или кадры фото-поста (по ссылке и формату)
    cached = store.get_inline_cache(key)
    if cached and cached.get("file_id"):
        await inline_query.answer(_results_for(uid, key, pkey, "video", [cached["file_id"]], ratio), cache_time=300, is_personal=False)
        return
    cached_p = store.get_inline_cache(pkey)
    if cached_p and cached_p.get("ids"):
        await inline_query.answer(_results_for(uid, key, pkey, "photos", cached_p["ids"], ratio), cache_time=300, is_personal=False)
        return

    # Уже качается (этим или другим пользователем) — просто подключаемся к задаче.
    tkey = f"{key}|{ratio}"
    task = _inflight.get(tkey)
    if task is None:
        ok_dl, _wait = lim.dl_hit(uid)
        if not ok_dl:
            limited = InlineQueryResultArticle(
                id="ratelimited",
                title=tr(uid, "⏳ Слишком много запросов подряд"),
                description=tr(uid, "Попробуй через минуту"),
                input_message_content=InputTextMessageContent(message_text=tr(uid, "⏳ Слишком много запросов подряд — попробуй через минуту.")),
            )
            await inline_query.answer([limited], cache_time=1, is_personal=True)
            return

        _failed.pop(tkey, None)
        task = asyncio.create_task(_background_download(tkey, platform, url, uid, inline_query.bot, ratio))
        task.add_done_callback(lambda t: t.cancelled() or t.exception())
        _inflight[tkey] = task

    try:
        # shield: таймаут ожидания НЕ отменяет само скачивание.
        kind, ids = await asyncio.wait_for(asyncio.shield(task), timeout=INLINE_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        slow = InlineQueryResultArticle(
            id=f"slow:{key}",
            title=tr(uid, "⏳ Скачиваю…"),
            description=tr(uid, "Подожди ~10 сек и поменяй запрос (добавь/убери пробел) — всё будет готово мгновенно"),
            input_message_content=InputTextMessageContent(
                message_text=tr(uid, "⏳ Ещё скачивается. Повтори запрос через несколько секунд — результат уже будет в кэше и отправится мгновенно. Или пришли ссылку боту в чат.")
            ),
        )
        await inline_query.answer([slow], cache_time=1, is_personal=True)
        return
    except Exception:
        reason = tr(uid, _failed.get(tkey) or "Не удалось скачать (приватный или недоступный пост?)")
        failed = InlineQueryResultArticle(
            id=f"failed:{key}",
            title=tr(uid, "❌ Не получилось скачать"),
            description=reason[:100],
            input_message_content=InputTextMessageContent(
                message_text=tr(uid, "❌ {reason}. Попробуй прислать ссылку боту напрямую в чат.", reason=reason)
            ),
        )
        await inline_query.answer([failed], cache_time=1, is_personal=True)
        return

    await inline_query.answer(_results_for(uid, key, pkey, kind, ids, ratio), cache_time=300, is_personal=False)


async def _background_download(tkey: str, platform: str, url: str, uid: int, bot, ratio: str = "orig") -> tuple:
    """Скачивание, переживающее таймаут inline-запроса. Ошибки логируются (раньше глотались молча)."""
    try:
        return await _download_and_cache(platform, url, uid, ratio)
    except Exception as e:
        low = str(e).lower()
        if "file too large" in low or "файл больше" in low:
            _failed[tkey] = "Видео слишком тяжёлое для инлайна"
        elif "не удалось скачать фото" in low:
            _failed[tkey] = "Не удалось скачать фото"
        elif "нет видео" in low:
            _failed[tkey] = "В посте нет видео"
        elif "chat not found" in low or "bot was blocked" in low or "forbidden" in low:
            _failed[tkey] = "Открой бота @tiksavesbot и нажми /start, затем повтори"
        else:
            _failed[tkey] = "Не удалось скачать (приватный или недоступный пост?)"
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
        _inflight.pop(tkey, None)
        # чтобы _failed не рос бесконечно
        if len(_failed) > 500:
            _failed.clear()
