"""
Общая диагностика для пикера качества (YouTube/Instagram/VK/Pinterest):
если yt-dlp явно сигнализировал о потере форматов (nsig/подпись — см.
youtube_provider._DiagnosticLogger) или в итоге доступно подозрительно мало
вариантов качества, сообщаем об этом в лог-канал бота. Обычно это значит,
что на сервере отстала версия yt-dlp и её пора обновить — а не то, что у
конкретного видео и правда нет ничего кроме 360p.
"""
import time
from typing import Any, Dict, List

from helpers import html_escape, code
from logging_channel import log_event

# Не шлём в канал чаще, чем раз в это окно — иначе при массовом наплыве
# ссылок на старом yt-dlp лог-канал завалит одинаковыми сообщениями.
_WARN_COOLDOWN_SEC = 1800
_last_warn_ts = 0.0


async def maybe_report_limited_quality(
    bot,
    platform: str,
    url: str,
    info: Dict[str, Any],
    qualities: List[dict],
) -> None:
    global _last_warn_ts

    explicit_warning = bool(info.get("_limited_formats_warning"))
    heights = [q["height"] for q in qualities]
    suspiciously_few = bool(heights) and max(heights) <= 360 and len(heights) <= 2

    if not (explicit_warning or suspiciously_few):
        return

    now = time.time()
    if now - _last_warn_ts < _WARN_COOLDOWN_SEC:
        return
    _last_warn_ts = now

    detail = info.get("_limited_formats_detail") or ""
    best = f"{max(heights)}p" if heights else "нет вариантов"

    await log_event(
        bot,
        "yt_dlp_outdated",
        [
            "⚠️ Категория: <b>yt-dlp мог отдать урезанные качества</b>",
            f"📡 Источник: <b>{html_escape(platform)}</b>",
            f"🔝 Лучшее доступное: <b>{html_escape(best)}</b>",
            f"🔗 Ссылка: {code(url)}",
            "📌 Скорее всего, версия yt-dlp на сервере отстала от текущего "
            "плеера YouTube (не удаётся расшифровать подпись у "
            "качественных потоков — доживают только старые низкие форматы). "
            f"Причина от yt-dlp: <b>{html_escape(detail) or '—'}</b>\n"
            "🛠 Обнови: <code>pip install -U yt-dlp --break-system-packages</code> и перезапусти бота.",
        ],
    )
