"""
Скачивание видео с YouTube (и через общий движок — Instagram/VK/Pinterest)
через yt-dlp.

В отличие от TikTok-провайдеров (providers.py), тут нет отдельного "получить
ссылки" + "скачать по ссылке" — yt-dlp сам качает файл на диск за один вызов,
и делает это синхронно, поэтому каждый вызов заворачиваем в отдельный поток
(asyncio.to_thread), чтобы не блокировать event loop бота.

Плюс: поддержка выбора качества (пользователь может выбрать конкретное
разрешение или "только звук") и ускорение больших закачек (YouTube/VK)
через параллельные фрагменты/чанки.
"""
import asyncio
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp

from config import (
    YOUTUBE_MAX_HEIGHT,
    YOUTUBE_CONCURRENT_FRAGMENTS,
    YOUTUBE_HTTP_CHUNK_MB,
    YTDLP_COOKIES_FILE,
    YTDLP_COOKIES_B64,
    YTDLP_PROXY,
    DOWNLOAD_HARD_CAP_BYTES,
)
from cobalt_client import cobalt_enabled, cobalt_download


class YoutubeTooLargeError(Exception):
    """Итоговый файл больше допустимого лимита."""


def _find_ffmpeg() -> Optional[str]:
    """
    Ищет ffmpeg: сначала системный (если вдруг есть), потом — портативный
    бинарник из пакета imageio-ffmpeg (ставится через pip, ничего вручную
    в систему устанавливать не нужно — именно так чинили отсутствие ffmpeg
    на этом сервере).

    Критично для качества: БЕЗ ffmpeg нельзя склеить отдельные видео- и
    аудио-потоки, а YouTube уже много лет не генерирует готовые (уже
    смешанные) mp4-файлы выше ~720p — независимо от того, что выбрал
    пользователь в кнопках качества (1080p/1440p/2160p), реальный
    результат без ffmpeg почти всегда упрётся в ~720p или ниже. Поэтому
    отсутствие ffmpeg — не мелочь, а причина №1 того, что "качество выше
    не работает".
    """
    system_path = shutil.which("ffmpeg")
    if system_path:
        return system_path
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and Path(path).exists():
            return path
        return None
    except Exception:
        return None


_FFMPEG_PATH: Optional[str] = _find_ffmpeg()


def ffmpeg_available() -> bool:
    """Есть ли рабочий ffmpeg — от этого зависит, доступно ли качество выше ~720p."""
    return bool(_FFMPEG_PATH)

# Общие для всех вызовов yt-dlp клиенты-экстракторы YouTube. Важно: одного
# android/ios часто НЕДОСТАТОЧНО — с 2024–2025 YouTube всё чаще требует
# PO-токен именно для их adaptive-форматов и в ответ отдаёт им куцый список
# (нередко буквально только 360p/144p) — то самое "качество только самое
# плохое". tv_embedded и mweb в большинстве случаев отдают лестницу вплоть
# до 1080p/4K без PO-токена, поэтому перечисляем сразу несколько клиентов —
# yt-dlp сам опрашивает все и СКЛАДЫВАЕТ форматы вместе, а не берёт только
# первый ответивший. Чем больше клиентов в списке, тем больше шанс получить
# полный набор качеств.
_YT_PLAYER_CLIENTS = ["android", "ios", "tv_embedded", "mweb", "web"]

# Если YouTube ответил "Sign in to confirm you're not a bot" — пробуем другие
# наборы клиентов БЕЗ cookies. android_vr / tv_simply / web_embedded обычно не
# требуют ни входа, ни PO-токена. Применяется только к YouTube.
_YT_CLIENT_CHAINS = [
    # С рабочим JS-движком (deno) клиенты по умолчанию отдают всю лестницу
    # качеств вплоть до 4K. Старые android/ios без PO-токена отдают ТОЛЬКО
    # готовый файл 360p (и без ошибки!) — поэтому они в самом конце.
    ["default"],
    ["tv", "web_safari", "mweb"],
    ["android_vr", "tv_simply", "web_embedded"],
    _YT_PLAYER_CLIENTS,
]

# Какой набор клиентов сработал лучше всего для ссылки (запоминаем на пробе,
# чтобы скачивание сразу шло тем же путём и получало то же качество).
_CLIENT_CACHE: Dict[str, List[str]] = {}
# Меньшая сторона видео (px), начиная с которой считаем качество "достаточно хорошим"
# и не перебираем остальные наборы клиентов.
_GOOD_ENOUGH_SIDE = 720

_AUTH_WALL_MARKERS = (
    "sign in to confirm",
    "not a bot",
    "use --cookies",
    "log in for access",
    "login required",
    "empty media response",
    "this video is only available for registered users",
    "confirm your age",
)


def is_auth_wall_error(e: BaseException) -> bool:
    low = str(e).lower()
    return any(m in low for m in _AUTH_WALL_MARKERS) or is_no_formats_error(e)


def is_no_formats_error(e: BaseException) -> bool:
    """Клиент YouTube ответил, но без нормальных форматов (нужен PO-токен / клиент не
    поддерживает cookies) — лечится сменой набора клиентов, как и стена авторизации."""
    low = str(e).lower()
    return "requested format is not available" in low or "no video formats" in low


def _is_youtube_url(url: str) -> bool:
    low = (url or "").lower()
    return "youtube.com" in low or "youtu.be" in low


def _best_side(info: Dict[str, Any]) -> int:
    """Меньшая сторона самого большого видеоформата (1080 для 1080x1920 и для 1920x1080)."""
    best = 0
    for f in info.get("formats") or []:
        h = f.get("height")
        if not h or f.get("vcodec") in (None, "none"):
            continue
        w = f.get("width")
        best = max(best, min(int(h), int(w)) if w else int(h))
    return best


def _run_chains(url: str, fn):
    """fn(clients) -> result. Для YouTube перебирает наборы клиентов при стене авторизации."""
    if not _is_youtube_url(url):
        return fn(None)
    chains = list(_YT_CLIENT_CHAINS)
    cached = _CLIENT_CACHE.get(url)
    if cached:
        chains = [cached] + [c for c in chains if c != cached]
    last: Optional[BaseException] = None
    for clients in chains:
        try:
            return fn(clients)
        except Exception as e:
            last = e
            if not is_auth_wall_error(e):
                raise
    raise last  # type: ignore[misc]


# Предпочитаем h264/mp4 — Telegram воспроизводит его без перекодирования на
# любом устройстве, к тому же декодируется быстрее vp9/av1 (важно, когда
# сервер сам собирает превью/отправляет файл). При этом не жертвуем
# доступностью — если h264 нет, yt-dlp всё равно возьмёт лучшее, что есть.
_FORMAT_SORT = ["res", "codec:h264:m4a", "fps", "hdr:12", "br"]

# Признаки в логах yt-dlp, что часть форматов (обычно как раз качественных)
# была молча выброшена из-за проблем с расшифровкой подписи ("n"-параметр,
# nsig) — это ПОЧТИ ВСЕГДА значит, что версия yt-dlp отстала от текущего
# плеера YouTube и её пора обновить (pip install -U yt-dlp). Форматы без
# такой защиты (обычно старые прогрессивные — 144p/360p, itag 17/18) при
# этом продолжают работать как ни в чём не бывало — отсюда и симптом
# "доступно только 360p".
_NSIG_WARNING_MARKERS = (
    "nsig extraction failed",
    "some formats may be missing",
    "unable to obtain the nsig",
    "signature extraction failed",
)


class _DiagnosticLogger:
    """
    Минимальный логгер для yt-dlp: не шумит в консоль (как quiet=True), но
    ловит характерные предупреждения о потере форматов, чтобы можно было
    сообщить об этом в лог-канал бота, а не просто молча отдавать 360p.
    """

    def __init__(self) -> None:
        self.limited_formats = False
        self.last_warning = ""
        self.messages: List[str] = []  # последние предупреждения/ошибки yt-dlp — для диагностики

    def _remember(self, msg: str) -> None:
        msg = (msg or "").strip().replace("\n", " ")
        if msg and not msg.startswith("[debug]") and msg not in self.messages:
            self.messages.append(msg[:260])
            del self.messages[:-6]

    def _check(self, msg: str) -> None:
        low = msg.lower()
        if any(marker in low for marker in _NSIG_WARNING_MARKERS):
            self.limited_formats = True
            self.last_warning = msg.strip()

    def debug(self, msg: str) -> None:
        self._check(msg)

    def info(self, msg: str) -> None:
        self._check(msg)

    def warning(self, msg: str) -> None:
        self._remember(msg)
        self._check(msg)

    def error(self, msg: str) -> None:
        self._remember(msg)
        self._check(msg)


def _resolve_cookies_file() -> Optional[str]:
    """Путь к cookies.txt: из YTDLP_COOKIES_FILE либо из YTDLP_COOKIES_B64 (декодируем во временный файл)."""
    if YTDLP_COOKIES_FILE and Path(YTDLP_COOKIES_FILE).is_file():
        return YTDLP_COOKIES_FILE
    if YTDLP_COOKIES_B64:
        try:
            import base64, tempfile
            target = Path(tempfile.gettempdir()) / "ytdlp_cookies.txt"
            target.write_bytes(base64.b64decode(YTDLP_COOKIES_B64))
            return str(target)
        except Exception:
            return None
    return None


_COOKIES_PATH: Optional[str] = _resolve_cookies_file()


def _find_js_runtime() -> Dict[str, Dict[str, Any]]:
    """
    JS-движок для yt-dlp. Новые версии YouTube прячут ссылки на видео за
    JS-вызовом (n-challenge): без deno/node остаются только превью и звук
    ("Requested format is not available"). Ищем deno (в т.ч. из pip-пакета
    `deno`), затем node.
    """
    runtimes: Dict[str, Dict[str, Any]] = {}
    path = shutil.which("deno")
    if not path:
        try:
            import deno  # type: ignore
            path = deno.find_deno_bin()
        except Exception:
            path = None
    if path:
        runtimes["deno"] = {"path": str(path)}
    node = shutil.which("node") or shutil.which("nodejs")
    if node:
        runtimes["node"] = {"path": node}
    return runtimes


_JS_RUNTIMES = _find_js_runtime()


def js_runtime_available() -> bool:
    return bool(_JS_RUNTIMES)


def environment_summary() -> str:
    """Короткая сводка окружения yt-dlp для лог-канала."""
    import importlib.util
    try:
        ver = yt_dlp.version.__version__
    except Exception:
        ver = "?"
    ejs = importlib.util.find_spec("yt_dlp_ejs") is not None
    return (
        f"yt-dlp {ver}; JS: {','.join(_JS_RUNTIMES) or 'НЕТ'}; yt-dlp-ejs: {'да' if ejs else 'НЕТ'}; "
        f"ffmpeg: {'да' if _FFMPEG_PATH else 'НЕТ'}; cookies: {'да' if _COOKIES_PATH else 'нет'}; "
        f"proxy: {'да' if YTDLP_PROXY else 'нет'}"
    )


def _base_opts(extra: Optional[Dict[str, Any]] = None, logger: Optional[_DiagnosticLogger] = None,
               url: str = "", clients: Optional[List[str]] = None) -> Dict[str, Any]:
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "socket_timeout": 20,
        "retries": 5,
        "fragment_retries": 10,
        "skip_unavailable_fragments": False,
        "extractor_args": {"youtube": {"player_client": list(clients or _YT_PLAYER_CLIENTS)}},
        "format_sort": _FORMAT_SORT,
        # Параллельные фрагменты — основное ускорение для DASH/HLS (YouTube,
        # часто и VK). Без этого фрагменты качаются строго по одному.
        "concurrent_fragment_downloads": max(1, YOUTUBE_CONCURRENT_FRAGMENTS),
        # Параллельные HTTP Range-запросы для обычных (progressive) ссылок.
        "http_chunk_size": max(1, YOUTUBE_HTTP_CHUNK_MB) * 1024 * 1024,
    }
    if _COOKIES_PATH:
        opts["cookiefile"] = _COOKIES_PATH
    if YTDLP_PROXY:
        opts["proxy"] = YTDLP_PROXY
    if _JS_RUNTIMES:
        opts["js_runtimes"] = _JS_RUNTIMES
        # скрипт-решатель n-challenge: из пакета yt-dlp-ejs, а если его нет — скачать с GitHub
        opts["remote_components"] = ["ejs:github"]
    low_url = (url or "").lower()
    if "pinterest" in low_url or "pin.it" in low_url:
        # Pinterest отдаёт ошибку "Conflicting range" на чанковых Range-запросах —
        # качаем одним потоком.
        opts.pop("http_chunk_size", None)
    if logger is not None:
        # Свой логгер полностью заменяет вывод yt-dlp — quiet/no_warnings
        # тут просто означают "не пиши сама, зови мой логгер", предупреждения
        # при этом всё равно долетают до _DiagnosticLogger.
        opts["logger"] = logger
    if extra:
        opts.update(extra)
    return opts


def _probe_once(url: str, clients: Optional[List[str]] = None) -> Dict[str, Any]:
    logger = _DiagnosticLogger()
    opts = _base_opts(
        {"skip_download": True, "ignore_no_formats_error": True, "check_formats": False},
        logger=logger, url=url, clients=clients,
    )
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if info is None:
            raise RuntimeError("yt-dlp: пустой ответ при получении информации о видео")
        if _is_youtube_url(url) and not any(
            f.get("height") and f.get("vcodec") not in (None, "none") for f in (info.get("formats") or [])
        ):
            # Клиент вернул только превью/сторибоарды — пробуем следующий набор клиентов.
            raise RuntimeError("Requested format is not available (no video formats)")
        info["_msgs"] = list(logger.messages)
        info["_limited_formats_warning"] = logger.limited_formats
        info["_limited_formats_detail"] = logger.last_warning
        return info


def _probe_sync(url: str) -> Dict[str, Any]:
    if not _is_youtube_url(url):
        return _probe_once(url, None)

    # Перебираем наборы клиентов и берём тот, что отдал лучшее качество: часть
    # клиентов отвечает "успешно", но подсовывает только 360p.
    best_info: Optional[Dict[str, Any]] = None
    best_clients: Optional[List[str]] = None
    best_side = -1
    last: Optional[BaseException] = None
    diag: List[str] = []
    for clients in _YT_CLIENT_CHAINS:
        try:
            info = _probe_once(url, clients)
        except Exception as e:
            last = e
            diag.append(f"{'+'.join(clients or [])}: ОШИБКА {str(e)[:160]}")
            if not is_auth_wall_error(e):
                if best_info is not None:
                    break
                raise
            continue
        side = _best_side(info)
        msgs = "; ".join(info.get("_msgs") or [])
        diag.append(f"{'+'.join(clients or [])}: {side}p" + (f" | {msgs[:240]}" if msgs else ""))
        if side > best_side:
            best_info, best_clients, best_side = info, clients, side
        if side >= _GOOD_ENOUGH_SIDE:
            break

    if best_info is None:
        raise last or RuntimeError("yt-dlp: не удалось получить форматы")
    if best_clients:
        _CLIENT_CACHE[url] = best_clients
        if len(_CLIENT_CACHE) > 500:
            _CLIENT_CACHE.clear()
    best_info["_diag"] = diag
    best_info["_yt_clients"] = best_clients
    best_info["_best_side"] = best_side
    return best_info


async def probe_youtube(url: str) -> Dict[str, Any]:
    """Узнаёт длительность/название/доступные качества БЕЗ скачивания."""
    try:
        return await asyncio.to_thread(_probe_sync, url)
    except Exception as e:
        # yt-dlp упёрся в "войдите/вы не бот" — если настроен cobalt, пропускаем
        # пробу: качество выберется "лучшее", а скачивание пойдёт через cobalt.
        if is_auth_wall_error(e) and cobalt_enabled():
            return {"_cobalt": True, "formats": [], "duration": 0, "title": "", "webpage_url": url,
                    "acodec": "unknown"}
        raise


def list_qualities(info: Dict[str, Any], max_options: int = 6) -> List[Dict[str, Any]]:
    """
    Строит короткий список качеств для показа пользователю кнопками: берёт
    реально существующие высоты видео из форматов (не выдуманные), убирает
    дубли и мусор (сторибоарды/превью без видеодорожки), сортирует по
    убыванию.

    Важно: тут НЕТ отсечки "если качество не дотягивает до стандартного
    порога — выкидываем" (раньше была и могла случайно спрятать лучшее
    доступное качество, если оно не попадало ровно в 2160/1440/1080/...) —
    самое высокое реально доступное качество попадает в список ВСЕГДА,
    даже если оно нестандартное (например, 900p).
    """
    formats = info.get("formats") or []
    by_height: Dict[int, Optional[int]] = {}
    short_side: Dict[int, int] = {}  # реальная высота -> "привычное" качество (меньшая сторона)
    for f in formats:
        height = f.get("height")
        vcodec = f.get("vcodec")
        # Отсекаем сторибоарды/превью-спрайты (нет vcodec вообще, но есть
        # "height" — иначе они попадали бы в список как отдельное "качество").
        if not height or vcodec in (None, "none"):
            continue
        if (f.get("format_note") or "").lower() in ("storyboard",):
            continue
        height = int(height)
        width = f.get("width")
        # У вертикальных видео (Shorts) "height" — это 1920 для "1080p": подписываем
        # по меньшей стороне, как привыкли пользователи.
        short_side[height] = min(height, int(width)) if width else height
        size = f.get("filesize") or f.get("filesize_approx")
        by_height.setdefault(height, None)
        prev = by_height.get(height)
        if size and (prev is None or size > prev):
            by_height[height] = size

    if not by_height:
        return []

    heights = sorted(by_height.keys(), reverse=True)

    if len(heights) <= max_options:
        picked = heights
    else:
        # Больше вариантов, чем нужно показать: всегда берём самое высокое
        # и самое низкое (чтобы был реальный разброс), остальное — примерно
        # равномерно по индексам отсортированного списка (не по "стандартным"
        # порогам — так ни одно реальное качество не теряется из-за того,
        # что не совпало с 1080/720/...).
        step = (len(heights) - 1) / (max_options - 1)
        picked = []
        for i in range(max_options):
            idx = round(i * step)
            idx = max(0, min(idx, len(heights) - 1))
            h = heights[idx]
            if h not in picked:
                picked.append(h)
        # Гарантируем, что самое высокое и самое низкое качество точно в списке.
        if heights[0] not in picked:
            picked[0] = heights[0]
        if heights[-1] not in picked:
            picked[-1] = heights[-1]

    picked = sorted(set(picked), reverse=True)[:max_options]
    return [{"height": h, "label": f"{short_side.get(h, h)}p", "filesize": by_height.get(h)} for h in picked]


def _format_for_height(height: Optional[int]) -> str:
    """
    Строит строку формата yt-dlp: ограничение по высоте (или лучшее, если
    height=None), с раздельной склейкой видео+аудио через ffmpeg, если он
    доступен, и без неё — иначе.
    """
    if _FFMPEG_PATH:
        if height:
            return (
                f"bestvideo[height<={height}]+bestaudio/"
                f"best[height<={height}]/best"
            )
        return "bestvideo+bestaudio/best"
    if height:
        return f"best[ext=mp4][height<={height}]/best[height<={height}]/best"
    return "best[ext=mp4]/best"


async def download_youtube(
    url: str,
    out_dir: Path,
    max_height: int = YOUTUBE_MAX_HEIGHT,
    quality_height: Optional[int] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """
    Качает видео на диск, возвращает путь к файлу и распарсенный info-dict
    yt-dlp. quality_height — явный выбор пользователя (например, 720); если
    не задан — берём лучшее в пределах max_height (авто-режим по умолчанию).
    """
    info_holder: Dict[str, Any] = {}

    def _run(clients: Optional[List[str]] = None) -> Path:
        out_template = str(out_dir / "%(id)s.%(ext)s")

        effective_height = quality_height or max_height
        fmt = _format_for_height(effective_height)

        opts = _base_opts(
            {
                "format": fmt,
                "outtmpl": out_template,
            },
            url=url,
            clients=clients,
        )
        if _FFMPEG_PATH:
            opts["merge_output_format"] = "mp4"
            opts["ffmpeg_location"] = _FFMPEG_PATH

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            info_holder.update(info or {})
            filename = ydl.prepare_filename(info)
            p = Path(filename)
            if not p.exists():
                candidate = p.with_suffix(".mp4")
                if candidate.exists():
                    p = candidate
            if not p.exists():
                raise RuntimeError(f"yt-dlp: итоговый файл не найден ({filename})")
            return p

    try:
        path = await asyncio.to_thread(lambda: _run_chains(url, _run))
    except Exception as e:
        if is_auth_wall_error(e) and cobalt_enabled():
            path = await cobalt_download(url, out_dir, height=quality_height, max_bytes=DOWNLOAD_HARD_CAP_BYTES)
            info_holder.update({"webpage_url": url, "acodec": "unknown"})
        else:
            raise
    return path, info_holder


def has_audio_track(info: Dict[str, Any]) -> bool:
    """Есть ли у видео вообще звук — проверяем по данным пробы/скачивания разными способами."""
    acodec = info.get("acodec")
    if acodec and acodec != "none":
        return True
    for f in info.get("requested_formats") or []:
        if f.get("acodec") and f.get("acodec") != "none":
            return True
    for f in info.get("formats") or []:
        if f.get("acodec") and f.get("acodec") != "none":
            return True
    return False


async def download_audio_only(url: str, out_dir: Path) -> Path:
    """
    Качает только звук через yt-dlp (bestaudio) — так же, как видео, а не
    попыткой переиспользовать сырую CDN-ссылку напрямую. У многих площадок
    (особенно VK) прямые ссылки на медиа требуют специфичных заголовков
    (Referer и т.п.), которых у нашего простого HTTP-скачивателя нет — из-за
    этого звук иногда не скачивался/приходил битым. yt-dlp сам знает, что
    нужно каждой площадке, поэтому эта дорожка надёжнее.
    """
    def _run(clients: Optional[List[str]] = None) -> Path:
        out_template = str(out_dir / "%(id)s.audio.%(ext)s")
        opts = _base_opts(
            {
                "format": "bestaudio/best",
                "outtmpl": out_template,
            },
            url=url,
            clients=clients,
        )
        if _FFMPEG_PATH:
            opts["ffmpeg_location"] = _FFMPEG_PATH
            opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ]

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            p = Path(filename)
            # После FFmpegExtractAudio (если ffmpeg найден) расширение меняется на .mp3
            for ext in (".mp3", ".m4a", ".webm", ".opus", ".ogg"):
                candidate = p.with_suffix(ext)
                if candidate.exists():
                    return candidate
            if p.exists():
                return p
            raise RuntimeError(f"yt-dlp: аудиофайл не найден ({filename})")

    try:
        return await asyncio.to_thread(lambda: _run_chains(url, _run))
    except Exception as e:
        if is_auth_wall_error(e) and cobalt_enabled():
            return await cobalt_download(url, out_dir, audio_only=True, max_bytes=DOWNLOAD_HARD_CAP_BYTES)
        raise


# Эти функции на самом деле не привязаны к YouTube — просто вызывают
# yt-dlp.extract_info(url), который сам определяет площадку. Алиасы с
# нейтральными именами — для использования с Instagram/VK/Pinterest и т.п.
probe_media = probe_youtube


async def download_media(
    url: str, out_dir: Path, quality_height: Optional[int] = None
) -> Tuple[Path, Dict[str, Any]]:
    return await download_youtube(url, out_dir, quality_height=quality_height)
