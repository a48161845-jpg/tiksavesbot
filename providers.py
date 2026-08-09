"""
Провайдеры скачивания медиа из TikTok: основной (TikWM API)
и резервный (Apify, опционально), а также логика переключения между ними.
"""

import json
import time
import asyncio
import contextlib

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List
from collections import deque

import aiohttp
from aiohttp import ClientPayloadError
from aiogram import Bot

from config import (
    API_URL,
    APIFY_TOKEN,
    APIFY_ACTOR,
    TIKWM_COOLDOWN_SEC,
    API_ERROR_WINDOW_SEC,
    API_ERROR_THRESHOLD,
)

from helpers import (
    html_escape,
    code,
    clamp_reason,
    ms_since,
    exc_type_name,
    resolve_tiktok_redirect,
    normalize_tiktok_url,
    normalize_description as _normalize_description,
)

from storage import store
from logging_channel import log_event


class _FileTooLargeError(Exception):
    """Внутренний сигнал: файл превышает лимит."""
    pass


# ============================================================
# MEDIA
# ============================================================

@dataclass
class MediaInfo:
    video: Optional[str]
    photos: List[str]
    music: Optional[str]
    description: Optional[str] = None


# ============================================================
# HELPERS
# ============================================================

def _deep_find_str(
    data: Any,
    keys: List[str],
    _depth: int = 0,
) -> Optional[str]:
    """
    Рекурсивно ищет в JSON первое строковое значение
    по одному из ключей-кандидатов.
    """

    if _depth > 4 or data is None:
        return None

    if isinstance(data, dict):
        for k in keys:
            v = data.get(k)

            if isinstance(v, str) and v.strip():
                return v.strip()

        for v in data.values():
            if isinstance(v, (dict, list)):
                result = _deep_find_str(
                    v,
                    keys,
                    _depth + 1,
                )

                if result:
                    return result

    elif isinstance(data, list):
        for item in data:
            result = _deep_find_str(
                item,
                keys,
                _depth + 1,
            )

            if result:
                return result

    return None


def _deep_find_url(
    data: Any,
    keys: List[str],
    _depth: int = 0,
) -> Optional[str]:

    value = _deep_find_str(
        data,
        keys,
        _depth,
    )

    if value and value.startswith("http"):
        return value

    return None


def _deep_find_list(
    data: Any,
    keys: List[str],
    _depth: int = 0,
) -> List[str]:
    """
    Ищет список URL-строк.
    Используется для фотографий/слайдов.
    """

    if _depth > 4 or data is None:
        return []

    if isinstance(data, dict):

        for k in keys:
            value = data.get(k)

            if isinstance(value, list) and value:

                result: List[str] = []

                for item in value:

                    if isinstance(item, str):
                        if item.startswith("http"):
                            result.append(item)

                    elif isinstance(item, dict):

                        url = (
                            item.get("url")
                            or item.get("image")
                            or item.get("urlList")
                        )

                        if isinstance(url, list) and url:
                            url = url[0]

                        if (
                            isinstance(url, str)
                            and url.startswith("http")
                        ):
                            result.append(url)

                if result:
                    return result

        for value in data.values():

            if isinstance(value, (dict, list)):

                result = _deep_find_list(
                    value,
                    keys,
                    _depth + 1,
                )

                if result:
                    return result

    elif isinstance(data, list):

        for item in data:

            result = _deep_find_list(
                item,
                keys,
                _depth + 1,
            )

            if result:
                return result

    return []


# ============================================================
# BASE PROVIDER
# ============================================================

class BaseProvider:

    name = "base"

    async def get_media(
        self,
        url: str,
    ) -> MediaInfo:
        raise NotImplementedError

    async def download_to_file(
        self,
        url: str,
        path: Path,
        max_bytes: int,
        stage: str,
        progress_cb: Optional[Callable] = None,
        cancel_cb: Optional[Callable] = None,
    ) -> int:
        raise NotImplementedError


# ============================================================
# ERROR LOGGING MIXIN
# ============================================================

class _DlErrMixin:
    """
    Общая логика логирования ошибок скачивания.
    """

    bot: Optional[Bot] = None

    async def _log_dlerr(
        self,
        stage: str,
        src: str,
        attempt: int,
        dur_ms: int,
        err: Exception,
    ) -> None:

        try:
            store.inc_error(
                stage,
                err,
            )
        except Exception:
            pass

        if not self.bot:
            return

        reason = clamp_reason(err)

        await log_event(
            self.bot,
            "dlerr",
            [
                "❌ Категория: <b>Ошибка скачивания</b>",
                f"🧩 Стадия: <b>{html_escape(stage)}</b>",
                f"🧬 Тип: <b>{html_escape(exc_type_name(err))}</b>",
                f"🔁 Попытка: <b>{attempt}</b>",
                f"⏱️ Время: <b>{dur_ms} мс</b>",
                f"🔗 Ссылка: {code(src)}",
                f"🧨 Причина: <b>{html_escape(reason)}</b>",
            ],
        )


# ============================================================
# TIKWM
# ============================================================

class TikWMClient(
    _DlErrMixin,
    BaseProvider,
):

    name = "tikwm"

    _cooldown_lock = asyncio.Lock()
    _last_call_ts = 0.0

    def __init__(
        self,
        session: aiohttp.ClientSession,
        bot: Optional[Bot] = None,
    ):
        self.session = session
        self.bot = bot

    @classmethod
    async def _respect_cooldown(cls) -> None:

        async with cls._cooldown_lock:

            now = time.monotonic()

            wait = (
                TIKWM_COOLDOWN_SEC
                - (now - cls._last_call_ts)
            )

            if wait > 0:
                await asyncio.sleep(wait)

            cls._last_call_ts = time.monotonic()

    @staticmethod
    def _media_from_data(
        data: Dict[str, Any],
    ) -> MediaInfo:

        video = (
            data.get("play")
            or data.get("wmplay")
        )

        photos: List[str] = []

        for key in (
            "images",
            "image",
            "photos",
        ):

            value = data.get(key)

            if isinstance(value, list) and value:

                if isinstance(value[0], dict):

                    photos = [
                        x
                        for x in (
                            (
                                obj.get("url")
                                or obj.get("image")
                                or ""
                            )
                            for obj in value
                        )
                        if x
                    ]

                else:

                    photos = [
                        str(x)
                        for x in value
                        if x
                    ]

                break

        music = None

        for key in (
            "music",
            "music_url",
            "musicUrl",
            "playUrl",
            "music_play",
            "musicPlay",
        ):

            value = data.get(key)

            if (
                isinstance(value, str)
                and value.startswith("http")
            ):
                music = value
                break

        if not music:

            music_info = (
                data.get("music_info")
                or data.get("musicInfo")
                or {}
            )

            if isinstance(
                music_info,
                dict,
            ):

                for key in (
                    "play",
                    "play_url",
                    "playUrl",
                    "url",
                ):

                    value = music_info.get(key)

                    if (
                        isinstance(value, str)
                        and value.startswith("http")
                    ):
                        music = value
                        break

        description = None

        for key in (
            "title",
            "desc",
            "description",
        ):

            value = data.get(key)

            if (
                isinstance(value, str)
                and value.strip()
            ):

                description = _normalize_description(
                    value.strip()
                )

                break

        return MediaInfo(
            video=video,
            photos=photos,
            music=music,
            description=description,
        )

    # ========================================================
    # GET MEDIA — ИСПРАВЛЕННЫЙ
    # ========================================================

    async def get_media(
        self,
        url: str,
    ) -> MediaInfo:

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": (
                "application/json,"
                "text/plain,*/*"
            ),
            "Content-Type": (
                "application/"
                "x-www-form-urlencoded"
            ),
            "Connection": "keep-alive",
        }

        last_err: Optional[Exception] = None

        for attempt in range(1, 4):

            t0 = time.perf_counter()

            try:

                await self._respect_cooldown()

                async with self.session.post(
                    API_URL,
                    data={"url": url},
                    headers=headers,
                    allow_redirects=True,
                    timeout=aiohttp.ClientTimeout(
                        total=30
                    ),
                ) as resp:

                    raw = await resp.read()

                    # ------------------------------------------------
                    # HTTP ERROR
                    # ------------------------------------------------

                    if resp.status >= 400:

                        preview = raw[:300].decode(
                            "utf-8",
                            "replace",
                        )

                        raise RuntimeError(
                            f"TikWM HTTP {resp.status}: "
                            f"{preview!r}"
                        )

                    # ------------------------------------------------
                    # EMPTY RESPONSE
                    # ------------------------------------------------

                    if not raw:

                        raise RuntimeError(
                            "Empty response body from API "
                            f"(HTTP {resp.status}, "
                            f"Content-Type: "
                            f"{resp.headers.get('Content-Type', '?')})"
                        )

                    # ------------------------------------------------
                    # JSON
                    # ------------------------------------------------

                    try:

                        js = json.loads(
                            raw.decode(
                                "utf-8",
                                "ignore",
                            )
                        )

                    except json.JSONDecodeError as e:

                        preview = raw[:300].decode(
                            "utf-8",
                            "replace",
                        )

                        raise RuntimeError(
                            "Invalid JSON from API "
                            f"(HTTP {resp.status}): "
                            f"{preview!r}"
                        ) from e

                # ----------------------------------------------------
                # RESPONSE TYPE
                # ----------------------------------------------------

                if not isinstance(js, dict):

                    raise RuntimeError(
                        "Unexpected API response type: "
                        f"{type(js).__name__}"
                    )

                # ----------------------------------------------------
                # API CODE
                # ----------------------------------------------------

                if js.get("code") != 0:

                    raise RuntimeError(
                        f"API error: {js}"
                    )

                # ----------------------------------------------------
                # DATA
                # ----------------------------------------------------

                if "data" not in js:

                    raise RuntimeError(
                        f"API response has no data: {js}"
                    )

                data = js["data"]

                if not isinstance(data, dict):

                    raise RuntimeError(
                        "API data has unexpected type: "
                        f"{type(data).__name__}"
                    )

                # ----------------------------------------------------
                # MEDIA
                # ----------------------------------------------------

                media = self._media_from_data(
                    data
                )

                if (
                    not media.video
                    and not media.photos
                ):

                    raise RuntimeError(
                        "API returned no video/photo links"
                    )

                return media

            # ========================================================
            # NETWORK ERRORS
            # ========================================================

            except (
                ClientPayloadError,
                aiohttp.ClientConnectionError,
                aiohttp.ServerDisconnectedError,
                asyncio.TimeoutError,
                aiohttp.ClientOSError,
                aiohttp.ClientResponseError,
            ) as e:

                last_err = e

                await self._log_dlerr(
                    "api",
                    url,
                    attempt,
                    ms_since(t0),
                    e,
                )

                if attempt < 3:
                    await asyncio.sleep(
                        0.6 * attempt
                    )

            # ========================================================
            # API / JSON / OTHER ERRORS
            # ========================================================

            except Exception as e:

                last_err = e

                await self._log_dlerr(
                    "api",
                    url,
                    attempt,
                    ms_since(t0),
                    e,
                )

                if attempt < 3:

                    await asyncio.sleep(
                        0.6 * attempt
                    )

                    continue

                raise

        raise RuntimeError(
            "TikWM fetch failed after retries: "
            f"{last_err}"
        ) from last_err

    # ========================================================
    # DOWNLOAD FILE
    # ========================================================

    async def download_to_file(
        self,
        url: str,
        path: Path,
        max_bytes: int,
        stage: str,
        progress_cb: Optional[Callable] = None,
        cancel_cb: Optional[Callable] = None,
    ) -> int:

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }

        last_err: Optional[Exception] = None

        for attempt in range(1, 4):

            t0 = time.perf_counter()

            tmp = path.with_suffix(
                path.suffix + ".part"
            )

            size = 0

            try:

                async with self.session.get(
                    url,
                    headers=headers,
                    allow_redirects=True,
                ) as resp:

                    resp.raise_for_status()

                    total = (
                        resp.content_length
                        or 0
                    )

                    if total > max_bytes:

                        raise _FileTooLargeError(
                            f"File too large "
                            f"(> {max_bytes} bytes)"
                        )

                    with tmp.open(
                        "wb"
                    ) as f:

                        async for chunk in resp.content.iter_chunked(
                            1024 * 64
                        ):

                            if not chunk:
                                continue

                            if (
                                cancel_cb
                                and cancel_cb()
                            ):
                                raise RuntimeError(
                                    "Cancelled"
                                )

                            size += len(chunk)

                            if size > max_bytes:

                                raise _FileTooLargeError(
                                    f"File too large "
                                    f"(> {max_bytes} bytes)"
                                )

                            f.write(chunk)

                            if (
                                progress_cb
                                and total > 0
                            ):

                                progress = int(
                                    size * 100 / total
                                )

                                progress_cb(
                                    progress
                                )

                tmp.replace(path)

                return size

            except _FileTooLargeError:

                with contextlib.suppress(
                    Exception
                ):
                    tmp.unlink(
                        missing_ok=True
                    )

                raise RuntimeError(
                    f"File too large "
                    f"(> {max_bytes} bytes)"
                )

            except (
                ClientPayloadError,
                aiohttp.ClientConnectionError,
                aiohttp.ServerDisconnectedError,
                asyncio.TimeoutError,
                aiohttp.ClientOSError,
                aiohttp.ClientResponseError,
            ) as e:

                last_err = e

                with contextlib.suppress(
                    Exception
                ):
                    tmp.unlink(
                        missing_ok=True
                    )

                await self._log_dlerr(
                    stage,
                    url,
                    attempt,
                    ms_since(t0),
                    e,
                )

                await asyncio.sleep(
                    0.6 * attempt
                )

            except Exception as e:

                with contextlib.suppress(
                    Exception
                ):
                    tmp.unlink(
                        missing_ok=True
                    )

                await self._log_dlerr(
                    stage,
                    url,
                    attempt,
                    ms_since(t0),
                    e,
                )

                raise

        raise RuntimeError(
            "Download failed after retries: "
            f"{last_err}"
        ) from last_err


# ============================================================
# APIFY
# ============================================================

class ApifyProvider(
    _DlErrMixin,
    BaseProvider,
):

    name = "apify"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        bot: Optional[Bot],
    ):
        self.session = session
        self.bot = bot

    async def get_media(
        self,
        url: str,
    ) -> MediaInfo:

        if not APIFY_TOKEN:
            raise RuntimeError(
                "APIFY_TOKEN not set"
            )

        run_url = (
            "https://api.apify.com/v2/acts/"
            f"{APIFY_ACTOR}/"
            "run-sync-get-dataset-items"
        )

        t0 = time.perf_counter()

        try:

            async with self.session.post(
                run_url,
                params={
                    "token": APIFY_TOKEN
                },
                json={
                    "postURLs": [url],
                    "shouldDownloadVideos": True,
                    "shouldDownloadCovers": False,
                },
                headers={
                    "Content-Type":
                        "application/json"
                },
                timeout=aiohttp.ClientTimeout(
                    total=60
                ),
            ) as resp:

                raw = await resp.read()

                if resp.status >= 400:

                    preview = raw[:300].decode(
                        "utf-8",
                        "replace",
                    )

                    raise RuntimeError(
                        f"Apify HTTP {resp.status}: "
                        f"{preview!r}"
                    )

                if not raw:

                    raise RuntimeError(
                        "Apify: empty response body"
                    )

                items = json.loads(
                    raw.decode(
                        "utf-8",
                        "ignore",
                    )
                )

            if not items:

                raise RuntimeError(
                    "Apify: empty dataset "
                    "(актор не вернул данные)"
                )

            item = (
                items[0]
                if isinstance(items, list)
                else items
            )

            video = _deep_find_url(
                item,
                [
                    "downloadAddr",
                    "play",
                    "video_url",
                    "videoUrl",
                    "noWatermark",
                    "hdplay",
                ],
            )

            photos = _deep_find_list(
                item,
                [
                    "images",
                    "imagePost",
                    "photos",
                    "slides",
                ],
            )

            music = _deep_find_url(
                item,
                [
                    "musicMeta",
                    "music",
                    "music_url",
                    "musicUrl",
                    "playUrl",
                ],
            )

            description = _normalize_description(
                _deep_find_str(
                    item,
                    [
                        "text",
                        "title",
                        "desc",
                        "description",
                    ],
                )
            )

            if not video and not photos:

                raise RuntimeError(
                    "Apify: no video/photo links "
                    "in dataset item"
                )

            return MediaInfo(
                video=video,
                photos=photos,
                music=music,
                description=description,
            )

        except Exception as e:

            await self._log_dlerr(
                "api_apify",
                url,
                1,
                ms_since(t0),
                e,
            )

            raise

    async def download_to_file(
        self,
        url: str,
        path: Path,
        max_bytes: int,
        stage: str,
        progress_cb: Optional[Callable] = None,
        cancel_cb: Optional[Callable] = None,
    ) -> int:

        client = TikWMClient(
            self.session,
            self.bot,
        )

        return await client.download_to_file(
            url,
            path,
            max_bytes,
            stage=stage,
            progress_cb=progress_cb,
            cancel_cb=cancel_cb,
        )


# ============================================================
# PROVIDER SWITCHER
# ============================================================

class ProviderSwitcher:
    """
    Цепочка провайдеров.

    Если основной провайдер падает —
    автоматически пробуется следующий.

    Если основной провайдер слишком часто
    ошибается — временно отправляется в конец очереди.
    """

    def __init__(
        self,
        providers: List[BaseProvider],
        bot: Bot,
    ):

        if not providers:
            raise ValueError(
                "ProviderSwitcher needs at least one provider"
            )

        self.providers = providers
        self.bot = bot

        self._errs: Dict[
            str,
            deque
        ] = {
            p.name: deque()
            for p in providers
        }

    def _cleanup(
        self,
        name: str,
    ) -> None:

        now = time.time()

        dq = self._errs.setdefault(
            name,
            deque(),
        )

        while (
            dq
            and now - dq[0]
            > API_ERROR_WINDOW_SEC
        ):
            dq.popleft()

    def mark_error(
        self,
        provider: BaseProvider,
    ) -> None:

        now = time.time()

        self._errs.setdefault(
            provider.name,
            deque(),
        ).append(now)

        self._cleanup(
            provider.name
        )

    def mark_success(
        self,
        provider: BaseProvider,
    ) -> None:

        self._errs.setdefault(
            provider.name,
            deque(),
        ).clear()

    def _order(
        self,
    ) -> List[BaseProvider]:

        primary = self.providers[0]

        self._cleanup(
            primary.name
        )

        if (
            len(
                self._errs.get(
                    primary.name,
                    [],
                )
            )
            >= API_ERROR_THRESHOLD
        ):

            return (
                self.providers[1:]
                + [primary]
            )

        return list(
            self.providers
        )

    def choose(
        self,
    ) -> BaseProvider:

        return self._order()[0]

    async def log_switch(
        self,
        using: str,
        reason: str = "",
    ) -> None:

        lines = [
            "🔁 Категория: "
            "<b>Переключение провайдера</b>",

            f"📡 Сработал запасной: "
            f"<b>{html_escape(using)}</b>",
        ]

        if reason:

            lines.append(
                "🧨 Основной не смог: "
                f"<b>{html_escape(reason)}</b>"
            )

        await log_event(
            self.bot,
            "providerfallback",
            lines,
        )

    async def get_media(
        self,
        url: str,
        raw_url: Optional[str] = None,
    ):

        order = self._order()

        last_err: Optional[Exception] = None

        tried: List[str] = []

        # ========================================================
        # ПЕРВЫЙ ПРОХОД
        # ========================================================

        for i, provider in enumerate(
            order
        ):

            try:

                media = await provider.get_media(
                    url
                )

                self.mark_success(
                    provider
                )

                if i > 0:

                    with contextlib.suppress(
                        Exception
                    ):

                        await self.log_switch(
                            provider.name,
                            reason=", ".join(
                                tried
                            ) or "?",
                        )

                return media, provider

            except Exception as e:

                last_err = e

                tried.append(
                    f"{provider.name}: "
                    f"{clamp_reason(e)}"
                )

                self.mark_error(
                    provider
                )

                continue

        # ========================================================
        # SHORT TIKTOK URL REDIRECT
        # ========================================================

        if raw_url:

            sess = getattr(
                order[0],
                "session",
                None,
            )

            if sess:

                with contextlib.suppress(
                    Exception
                ):

                    resolved = (
                        normalize_tiktok_url(
                            await resolve_tiktok_redirect(
                                sess,
                                raw_url,
                            )
                        )
                    )

                    if (
                        resolved
                        and resolved != raw_url
                        and resolved != url
                    ):

                        for provider in order:

                            try:

                                media = (
                                    await provider.get_media(
                                        resolved
                                    )
                                )

                                self.mark_success(
                                    provider
                                )

                                if provider.name != order[0].name:

                                    with contextlib.suppress(
                                        Exception
                                    ):

                                        await self.log_switch(
                                            provider.name,
                                            reason=(
                                                "redirect: "
                                                + ", ".join(
                                                    tried
                                                )
                                            ),
                                        )

                                return (
                                    media,
                                    provider,
                                )

                            except Exception as e:

                                last_err = e

                                tried.append(
                                    f"{provider.name}: "
                                    f"{clamp_reason(e)}"
                                )

                                self.mark_error(
                                    provider
                                )

                                continue

        raise (
            last_err
            or RuntimeError(
                "All providers failed"
            )
        )
