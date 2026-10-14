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
_WARN_COOLDOWN_SEC = 120
_last_warn_ts = 0.0


async def maybe_report_limited_quality(
    bot,
    platform: str,
    url: str,
    info: Dict[str, Any],
    qualities: List[dict],
) -> None:
    global _last_warn_ts

    # Предупреждение «yt-dlp отстал» — про плеер YouTube. У Pinterest/VK/Instagram низкое
    # качество — нормальное явление, ложные тревоги в лог не шлём.
    if platform != "youtube":
        return

    explicit_warning = bool(info.get("_limited_formats_warning"))
    heights = [q["height"] for q in qualities]
    best_side = info.get("_best_side")
    if best_side is not None:
        suspiciously_few = int(best_side) < 720
    else:
        suspiciously_few = bool(heights) and max(heights) <= 480 and len(heights) <= 3

    if not (explicit_warning or suspiciously_few):
        return

    now = time.time()
    if now - _last_warn_ts < _WARN_COOLDOWN_SEC:
        return
    _last_warn_ts = now

    detail = info.get("_limited_formats_detail") or ""
    try:
        from youtube_provider import environment_summary
        env = environment_summary()
    except Exception:
        env = "?"
    diag = "\n".join(info.get("_diag") or []) or "—"
    best = f"{max(heights)}p" if heights else "нет вариантов"

    await log_event(
        bot,
        "yt_dlp_outdated",
        [
            "⚠️ Категория: <b>yt-dlp мог отдать урезанные качества</b>",
            f"📡 Источник: <b>{html_escape(platform)}</b>",
            f"🔝 Лучшее доступное: <b>{html_escape(best)}</b>",
            f"🔗 Ссылка: {code(url)}",
            f"🧰 Окружение: <b>{html_escape(env)}</b>",
            f"🔬 Что ответил YouTube по наборам клиентов:\n<pre>{html_escape(diag[:1500])}</pre>",
            "📌 Скорее всего, версия yt-dlp на сервере отстала от текущего "
            "плеера YouTube (не удаётся расшифровать подпись у "
            "качественных потоков — доживают только старые низкие форматы). "
            f"Причина от yt-dlp: <b>{html_escape(detail) or '—'}</b>\n"
            "🛠 Обнови: <code>pip install -U yt-dlp --break-system-packages</code> и перезапусти бота.",
        ],
    )
