"""
Хелперы отправки контента пользователю: альбомы фото, видео
(со скачиванием файлом, если прямая ссылка не сработала), музыка.
"""
import time
import random
import asyncio
import contextlib
from pathlib import Path
from typing import Callable, Optional, List

from aiogram.types import Message, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo, FSInputFile
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest

from core.config import (
    CAPTION_PHOTO,
    CAPTION_AUDIO,
    MEDIA_GROUP_LIMIT,
    ALBUM_PAUSE_MIN,
    ALBUM_PAUSE_MAX,
    MAX_VIDEO_BYTES,
    MAX_AUDIO_BYTES,
    DESCRIPTION_TG_LIMIT,
    COMPRESS_OVER_LIMIT,
    DOWNLOAD_HARD_CAP_BYTES,
)
from core.helpers import html_escape, code, clamp_reason, exc_type_name
from core.storage import store
from core import globals_state
from downloaders.providers import BaseProvider
from i18n import tr, get_lang
from downloaders.video_compress import compress_to_limit, CompressError
from downloaders.video_meta import prepare_video_kwargs, cleanup_video_kwargs, telegram_kwargs
from downloaders.youtube_provider import ffmpeg_available
from core.logging_channel import log_event, format_user_for_log


def chunk(items: List[str], size: int) -> List[List[str]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


async def _download_media_files(urls: List[str], kinds: List[str], bot=None, chat_id: Optional[int] = None) -> List[Optional[Path]]:
    """Скачивает файлы сами (с обходом 403 tiktokcdn) — запасной путь, когда Telegram не смог взять URL."""
    from downloaders.media_fetch import download_url
    session = getattr(globals_state.g_provider, "session", None)
    out: List[Optional[Path]] = []
    stamp = int(time.time() * 1000)
    for i, (u, kind) in enumerate(zip(urls, kinds)):
        ext = ".mp4" if kind == "video" else ".jpg"
        dest = Path(f"tmp_media_{stamp}_{i}{ext}")
        try:
            if not session:
                raise RuntimeError("no session")
            await download_url(session, u, dest, kind=kind, bot=bot, chat_id=chat_id)
            out.append(dest)
        except Exception:
            dest.unlink(missing_ok=True)
            out.append(None)
    return out


async def _answer_group(message: Message, media: List) -> None:
    try:
        await message.answer_media_group(media)
    except TelegramRetryAfter as e:
        await asyncio.sleep(int(getattr(e, "retry_after", 2)) + 1)
        await message.answer_media_group(media)


async def _cropped_sources(items: List, ratio: str, message: Message) -> tuple:
    """
    Для формата ratio (1:1, 4:3, ...) скачивает фото, обрезает по центру и возвращает (источники, временные файлы).
    Видео (live-клипы) идут как есть. Не получилось скачать/обрезать кадр — отправится оригинал по ссылке.
    """
    from downloaders.photo_crop import crop_image
    sources: List = []
    tmp: List[Path] = []
    for u, kind in items:
        if kind != "photo":
            sources.append(u)
            continue
        got = (await _download_media_files([u], ["photo"], message.bot, message.chat.id))[0]
        if got is None:
            sources.append(u)
            continue
        tmp.append(got)
        try:
            out = await crop_image(got, got.with_name(got.stem + f"_{ratio}.jpg"), ratio)
            tmp.append(out)
            sources.append(FSInputFile(out))
        except Exception:
            sources.append(u)
    return sources, tmp


def _media_group(kinds: List[str], sources: List, caption_html: Optional[str]) -> List:
    media: List = []
    for i, (kind, src) in enumerate(zip(kinds, sources)):
        kw = {"caption": caption_html, "parse_mode": "HTML"} if (caption_html and i == len(kinds) - 1) else {}
        media.append((InputMediaVideo if kind == "video" else InputMediaPhoto)(media=src, **kw))
    return media


async def _send_one(message: Message, kind: str, src, caption_html: Optional[str], markup) -> None:
    """Одно фото/видео (альбом из одного элемента Telegram не принимает). Здесь же можно повесить кнопки."""
    kw: dict = {}
    if caption_html:
        kw.update(caption=caption_html, parse_mode="HTML")
    if markup is not None:
        kw["reply_markup"] = markup
    method = message.answer_video if kind == "video" else message.answer_photo
    try:
        await method(src, **kw)
    except TelegramRetryAfter as e:
        await asyncio.sleep(int(getattr(e, "retry_after", 2)) + 1)
        await method(src, **kw)


async def _deliver(message: Message, items: List, stills: List[str], ratio_key: str,
                   caption_html: Optional[str], markup=None) -> None:
    """
    Отправляет items = [(url, kind)]: один элемент — отдельным сообщением (с подписью и кнопками), несколько —
    альбомом. Подпись получает ПОСЛЕДНИЙ элемент. stills — обычные фото кадров (если live-клип не скачался).
    Telegram не взял URL — качаем сами и загружаем файлами; формат кадра (ratio_key) применяется и там.
    """
    if not items:
        return
    kinds = [k for _u, k in items]
    tmp_files: List[Path] = []

    async def go(sources: List, kinds_: List[str]) -> None:
        if len(sources) == 1:
            await _send_one(message, kinds_[0], sources[0], caption_html, markup)
        else:
            await _answer_group(message, _media_group(kinds_, sources, caption_html))

    try:
        if ratio_key != "orig":
            sources, tmp_files = await _cropped_sources(items, ratio_key, message)
        else:
            sources = [u for u, _k in items]
        await go(sources, kinds)
    except TelegramBadRequest:
        files = await _download_media_files([u for u, _k in items], kinds, message.bot, message.chat.id)
        items = list(items)
        for idx, f in enumerate(files):  # не скачался клип — пробуем обычное фото этого кадра
            if f is None and items[idx][1] == "video":
                got = (await _download_media_files([stills[idx]], ["photo"], message.bot, message.chat.id))[0]
                files[idx] = got
                items[idx] = (stills[idx], "photo")
        if ratio_key != "orig":  # запасной путь тоже отдаёт выбранный формат, а не оригинал
            from downloaders.photo_crop import crop_image
            for idx, f in enumerate(files):
                if f is not None and items[idx][1] == "photo":
                    try:
                        cropped = await crop_image(f, f.with_name(f.stem + f"_{ratio_key}.jpg"), ratio_key)
                        f.unlink(missing_ok=True)
                        files[idx] = cropped
                    except Exception:
                        pass
        ok = [(it, f) for it, f in zip(items, files) if f is not None]
        try:
            if not ok:
                raise
            await go([FSInputFile(f) for _it, f in ok], [it[1] for it, _f in ok])
        finally:
            for f in files:
                if f:
                    f.unlink(missing_ok=True)
    finally:
        for f in tmp_files:
            f.unlink(missing_ok=True)


async def send_photos(message: Message, urls: List[str], caption_html: str = CAPTION_PHOTO,
                      live: Optional[dict] = None, ratio: str = "orig", reply_markup=None) -> int:
    """
    Шлёт фото альбомами по MEDIA_GROUP_LIMIT. Для кадров с live photo (live[url] = ссылка на клип)
    в альбом кладётся короткое видео. Если Telegram не смог сам взять URL (403 от CDN и т.п.),
    файлы скачиваются ботом и отправляются загрузкой; если не скачался live-клип — шлётся обычное фото.

    reply_markup — кнопки (донат и т.п.), которые должны висеть ПРЯМО НА ФОТО. К альбому Telegram кнопки
    прикрепить не даёт, поэтому последний кадр уходит отдельным сообщением с кнопками и подписью, а остальные —
    альбомом перед ним.
    """
    from downloaders.photo_crop import normalize_ratio
    ratio_key = normalize_ratio(ratio)
    live = live or {}
    live_nums = [i + 1 for i, u in enumerate(urls) if live.get(u)]
    if live_nums:
        caption_html = (caption_html or "") + "\n\n" + tr(
            message, "🎞 Live-фото (пришли короткими видео): №{n}", n=", ".join(map(str, live_nums)))
    packs = chunk(urls, MEDIA_GROUP_LIMIT)
    for pi, pack in enumerate(packs):
        items = [(live[u], "video") if live.get(u) else (u, "photo") for u in pack]
        stills = list(pack)
        last_pack = pi == len(packs) - 1
        tail = None
        if reply_markup is not None and last_pack:
            tail = (items[-1], stills[-1])
            items, stills = items[:-1], stills[:-1]
        # подпись — на последнем кадре всей серии: либо на кадре с кнопками, либо на конце последнего альбома
        await _deliver(message, items, stills, ratio_key, None if (tail or not last_pack) else caption_html)
        if tail:
            if items:
                await asyncio.sleep(0.4)  # чтобы кадр с кнопками гарантированно шёл после альбома
            await _deliver(message, [tail[0]], [tail[1]], ratio_key, caption_html, reply_markup)
        await asyncio.sleep(random.uniform(ALBUM_PAUSE_MIN, ALBUM_PAUSE_MAX))

    return len(urls)


# Ошибки Telegram, при которых отправка видео по прямой ссылке не удалась, но
# скачать файл самим и залить его файлом — может получиться.
_URL_SEND_FAIL_MARKERS = (
    "failed to get http url content",
    "wrong type of the web page content",
    "wrong file identifier",
    "http url specified",
    "wrong remote file identifier",
    "file is too big",
    "request entity too large",
)


async def fit_video_to_limit(path: Path) -> Path:
    """
    Если файл тяжелее лимита отправки (49 МБ на облачном Bot API) — сжимает
    его через ffmpeg. Возвращает путь к файлу, который можно отправлять
    (исходный или новый _c.mp4; вызывающий код сам удаляет оба). Если сжать
    нельзя — бросает RuntimeError("File too large ...").
    """
    size = path.stat().st_size
    if size <= MAX_VIDEO_BYTES:
        return path
    if not (COMPRESS_OVER_LIMIT and ffmpeg_available()):
        raise RuntimeError(f"File too large (> {MAX_VIDEO_BYTES} bytes)")
    try:
        return await compress_to_limit(path, MAX_VIDEO_BYTES)
    except CompressError as e:
        raise RuntimeError(f"File too large (> {MAX_VIDEO_BYTES} bytes): {e}") from e


async def send_video_smart(
    message: Message,
    provider: BaseProvider,
    video_url: str,
    caption: str,
    status_msg: Optional[Message] = None,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    cancel_cb: Optional[Callable] = None,
) -> None:
    try:
        await message.answer_video(video_url, caption=caption, parse_mode="HTML", reply_markup=reply_markup)
        return
    except TelegramBadRequest as e:
        low = str(e).lower()
        if not any(m in low for m in _URL_SEND_FAIL_MARKERS):
            raise

        tmp = Path(f"tmp_video_{message.chat.id}_{int(time.time()*1000)}.mp4")
        sendable: Optional[Path] = None
        progress_msg: Optional[Message] = status_msg
        try:
            if progress_msg:
                with contextlib.suppress(Exception):
                    await progress_msg.edit_text(
                        tr(message, "⏳ <b>Скачиваю… понадобится немного больше времени...</b>"),
                        parse_mode="HTML",
                    )
            else:
                progress_msg = await message.answer(
                    tr(message, "⏳ <b>Скачиваю… понадобится немного больше времени...</b>"),
                    parse_mode="HTML",
                )

            # Качаем с запасом по размеру: если файл тяжелее лимита отправки —
            # ниже его сожмёт ffmpeg, а не откажет пользователю.
            can_compress = COMPRESS_OVER_LIMIT and ffmpeg_available()
            await provider.download_to_file(
                video_url,
                tmp,
                max(MAX_VIDEO_BYTES, DOWNLOAD_HARD_CAP_BYTES) if can_compress else MAX_VIDEO_BYTES,
                stage="video",
                cancel_cb=cancel_cb,
            )
            if tmp.stat().st_size > MAX_VIDEO_BYTES and progress_msg:
                with contextlib.suppress(Exception):
                    await progress_msg.edit_text(
                        tr(message, "🗜 <b>Видео тяжёлое — сжимаю, чтобы влезло в Telegram…</b>"),
                        parse_mode="HTML",
                    )
            sendable = await fit_video_to_limit(tmp)
            meta = await prepare_video_kwargs(sendable)
            try:
                await message.answer_video(
                    FSInputFile(sendable), caption=caption, parse_mode="HTML", reply_markup=reply_markup,
                    **telegram_kwargs(meta),
                )
            finally:
                cleanup_video_kwargs(meta)
        except RuntimeError as e:
            if "file too large" in str(e).lower():
                with contextlib.suppress(Exception):
                    if progress_msg and progress_msg != status_msg:
                        await progress_msg.delete()
                raise  # перебрасываем — main_handler тихо обработает
            raise
        finally:
            with contextlib.suppress(Exception):
                tmp.unlink(missing_ok=True)
            if sendable and sendable != tmp:
                with contextlib.suppress(Exception):
                    sendable.unlink(missing_ok=True)


def _audio_user_id(message: Message, uid: Optional[int]) -> int:
    """ID пользователя для логов/файлов: при вызове из callback message.from_user — бот."""
    if uid is not None:
        return uid
    return message.chat.id if message.chat else 0


async def send_music_if_any(
    message: Message,
    provider: BaseProvider,
    music_url: Optional[str],
    *,
    uid: Optional[int] = None,
    label: Optional[str] = None,
    src: Optional[str] = None,
    song: Optional[dict] = None,
) -> None:
    if not music_url:
        return
    user_id = _audio_user_id(message, uid)
    # Название и исполнитель — в теги аудио, в подписи — строка «🎵 Название — Автор», под файлом — поиск в сервисах
    from downloaders.song_search import audio_tags, song_caption
    from ui.keyboards import song_kb
    extra = dict(audio_tags(song))
    if song:
        extra["reply_markup"] = song_kb(get_lang(user_id), song)
    audio_caption = tr(message, CAPTION_AUDIO) + song_caption(song)
    try:
        await message.answer_audio(music_url, caption=audio_caption, parse_mode="HTML", **extra)
        if uid is not None:
            store.inc_audio(uid, 1, url=src or "", source="tiktok")
        if label is not None:
            await log_event(
                message.bot,
                "audiodl",
                [
                    "🎵 Категория: <b>Скачивание музыки</b>",
                    f"👤 User/id: <b>{format_user_for_log(label, user_id)}</b>",
                    f"🔗 Ссылка: {code(src or '')}" if src else "🔗 Ссылка: -",
                ],
            )
        return
    except TelegramBadRequest as e:
        store.inc_error("audio", e)
        tmp = Path(f"tmp_audio_{user_id}_{int(time.time())}.mp3")
        try:
            await provider.download_to_file(music_url, tmp, MAX_AUDIO_BYTES, stage="audio")
            await message.answer_audio(FSInputFile(tmp), caption=audio_caption, parse_mode="HTML", **extra)
            if uid is not None:
                store.inc_audio(uid, 1, url=src or "", source="tiktok")
            if label is not None:
                await log_event(
                    message.bot,
                    "audiodl",
                    [
                        "🎵 Категория: <b>Скачивание музыки</b>",
                        f"👤 User/id: <b>{format_user_for_log(label, user_id)}</b>",
                        f"🔗 Ссылка: {code(src or '')}" if src else "🔗 Ссылка: -",
                    ],
                )
        except Exception as fallback_err:
            if label is not None:
                await log_event(
                    message.bot,
                    "dlerr",
                    [
                        "❌ Категория: <b>Ошибка скачивания</b>",
                        f"👤 User/id: <b>{format_user_for_log(label, user_id)}</b>",
                        "🧩 Стадия: <b>audio</b>",
                        f"🧬 Тип: <b>{html_escape(exc_type_name(fallback_err))}</b>",
                        f"🔗 Ссылка: {code(src or '')}" if src else "🔗 Ссылка: -",
                        f"🧨 Причина: <b>{html_escape(clamp_reason(fallback_err))}</b>",
                    ],
                )
            raise
        finally:
            with contextlib.suppress(Exception):
                tmp.unlink(missing_ok=True)


async def send_description_if_any(message: Message, description: Optional[str]) -> None:
    """
    Отправляет описание (подпись/caption) TikTok-видео так же, как музыку:
    - если текст помещается в сообщение Telegram — шлём моно-блоком (<pre>),
      чтобы его можно было скопировать целиком тапом, как код;
    - если текст слишком большой — шлём файлом (.txt).
    Содержимое не меняется (экранируем только служебные HTML-символы,
    чтобы Telegram не пытался распарсить их как разметку — раньше из-за
    этого длинные описания с "&"/"<"/">" молча не отправлялись).
    """
    if not description:
        return
    text = description.strip()
    if not text:
        return

    try:
        if len(text) <= DESCRIPTION_TG_LIMIT:
            await message.answer(f"<pre>{html_escape(text)}</pre>", parse_mode="HTML")
            return

        tmp = Path(f"tmp_description_{message.chat.id}_{int(time.time())}.txt")
        try:
            tmp.write_text(text, encoding="utf-8")
            await message.answer_document(FSInputFile(tmp, filename="description.txt"))
        finally:
            with contextlib.suppress(Exception):
                tmp.unlink(missing_ok=True)
    except Exception as e:
        # Раньше ошибка тут проглатывалась молча — пользователь ничего не видел.
        # Теперь сообщаем и логируем причину.
        with contextlib.suppress(Exception):
            await message.answer(tr(message, "❌ Не удалось отправить описание. Попробуй ещё раз."))
        with contextlib.suppress(Exception):
            await log_event(
                message.bot,
                "dlerr",
                [
                    "❌ Категория: <b>Ошибка скачивания</b>",
                    "🧩 Стадия: <b>description</b>",
                    f"🧬 Тип: <b>{html_escape(exc_type_name(e))}</b>",
                    f"🧨 Причина: <b>{html_escape(clamp_reason(e))}</b>",
                ],
            )


async def send_external_audio(
    message: Message,
    src_url: Optional[str],
    *,
    uid: Optional[int] = None,
    label: Optional[str] = None,
) -> None:
    """
    Кнопка "🎵 Музыка" под видео из внешних источников (YouTube/Instagram/VK/
    Pinterest) — качаем звук заново через yt-dlp по исходной ссылке на пост,
    а не переиспользуем сырую CDN-ссылку (у многих площадок, особенно VK,
    она требует спец-заголовков, без которых скачивание падает/приходит
    битым файлом — yt-dlp сам знает, что нужно каждой площадке).
    """
    from downloaders.youtube_provider import download_audio_only  # локальный импорт — не плодим циклы на уровне модулей

    if not src_url:
        return
    user_id = uid if uid is not None else message.chat.id

    tmp_path: Optional[Path] = None
    try:
        tmp_path = await download_audio_only(src_url, Path("."))
        await message.answer_audio(FSInputFile(tmp_path), caption=tr(message, CAPTION_AUDIO), parse_mode="HTML")
        if uid is not None:
            store.inc_audio(uid, 1, url=src_url)
        if label is not None:
            await log_event(
                message.bot,
                "audiodl",
                [
                    "🎵 Категория: <b>Скачивание музыки</b>",
                    f"👤 User/id: <b>{format_user_for_log(label, user_id)}</b>",
                    f"🔗 Ссылка: {code(src_url)}",
                ],
            )
    except Exception as e:
        with contextlib.suppress(Exception):
            await message.answer(tr(message, "❌ Не получилось скачать звук с этого видео."))
        if label is not None:
            await log_event(
                message.bot,
                "dlerr",
                [
                    "❌ Категория: <b>Ошибка скачивания</b>",
                    f"👤 User/id: <b>{format_user_for_log(label, user_id)}</b>",
                    "🧩 Стадия: <b>audio_external</b>",
                    f"🧬 Тип: <b>{html_escape(exc_type_name(e))}</b>",
                    f"🔗 Ссылка: {code(src_url)}",
                    f"🧨 Причина: <b>{html_escape(clamp_reason(e))}</b>",
                ],
            )
    finally:
        if tmp_path:
            with contextlib.suppress(Exception):
                tmp_path.unlink(missing_ok=True)
