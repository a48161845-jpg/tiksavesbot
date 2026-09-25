"""
Состояние "ожидает выбора качества" для видео из YouTube/Instagram/VK/
Pinterest (общий движок yt-dlp, см. youtube_provider.py). Пикер качества —
отдельный шаг между "нашли видео" и "качаем": сначала показываем кнопки
с доступными разрешениями (плюс "🎵 Только звук"), а качаем уже то, что
выбрал пользователь.

Ключ — req_id (не uid), по той же причине, что и в picker_state.py: у
одного пользователя может быть открыто сразу несколько таких сообщений
(если он прислал несколько ссылок подряд).
"""
import time
from typing import Any, Dict, List

from config import QUALITY_CHOICE_TTL_SEC

quality_pending: Dict[str, Dict[str, Any]] = {}


def cleanup_quality_pending() -> None:
    now = time.time()
    dead = [rid for rid, st in quality_pending.items() if now - float(st.get("ts", 0)) > QUALITY_CHOICE_TTL_SEC]
    for rid in dead:
        quality_pending.pop(rid, None)


def save_quality_pending(
    req_id: str,
    *,
    uid: int,
    url: str,
    platform: str,
    platform_name: str,
    emoji: str,
    duration: int,
    qualities: List[Dict[str, Any]],
) -> None:
    cleanup_quality_pending()
    quality_pending[req_id] = {
        "uid": uid,
        "url": url,
        "platform": platform,
        "platform_name": platform_name,
        "emoji": emoji,
        "duration": duration,
        "qualities": qualities,
        "ts": time.time(),
    }
