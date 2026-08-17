"""
Генерация и отправка отчёта по базе данных в лог-канал.
По команде /dbfile (только для админов) и автоматически раз в месяц — файлом.
"""
import asyncio
import contextlib
import json
from typing import Optional

from aiogram import Bot
from aiogram.types import BufferedInputFile

from config import LOG_CHANNEL_ID, ADMINS, log
from helpers import msk_now, now_msk_str
from storage import store


def _build_db_json() -> bytes:
    """Сериализует всё содержимое store в JSON-файл."""
    return json.dumps(store.data, ensure_ascii=False, indent=2).encode("utf-8")


async def send_db_json(bot: Bot, chat_id: int) -> None:
    """Отправляет полный дамп БД как JSON-файл в указанный чат (для /dbfile)."""
    try:
        data_bytes = _build_db_json()
        now_dt = msk_now()
        filename = f"db_dump_{now_dt.strftime('%Y-%m-%d_%H-%M')}.json"
        input_file = BufferedInputFile(data_bytes, filename=filename)
        await bot.send_document(
            chat_id=chat_id,
            document=input_file,
            caption=f"🗄 <b>Дамп базы данных</b>\n{now_msk_str()}",
            parse_mode="HTML",
        )
        log.info("db_report: отправлен JSON-дамп в chat_id=%s", chat_id)
    except Exception as e:
        log.error("db_report: ошибка отправки JSON-дампа: %s", e)


# =================== PINNED OVERVIEW (лог-канал) ===================
# Вместо ежедневной сводки в 23:55 — одно закреплённое сообщение с общей
# статистикой за всё время, которое периодически обновляется (редактируется),
# а не плодит новые сообщения каждый день.
_pinned_stats_task: Optional[asyncio.Task] = None
PINNED_STATS_INTERVAL_SEC = 900  # обновление раз в 15 минут


def _pinned_overview_text() -> str:
    d = store.data
    users_total = store.get_users_count()
    # list_bans() сначала чистит просроченные баны — иначе тут могли считаться
    # давно истёкшие баны как "активные", если долго не было банов/разбанов
    # (единственное место, где это реально чистилось раньше).
    bans_active = len(store.list_bans())
    admins_total = len(ADMINS) + len(store.get_extra_admins())

    all_stats = (d.get("stats") or {}).get("all", {})
    dls = all_stats.get("downloads", {}) or {}
    video_ops = dls.get("video_ops", 0)
    photo_ops = dls.get("photo_ops", 0)
    photos_sent = dls.get("photos_sent", 0)
    audio_sent = dls.get("audio_sent", 0)
    stars_total = all_stats.get("stars_total", 0)
    errors_total = (all_stats.get("errors") or {}).get("total", 0)
    bans_total = all_stats.get("bans_total", 0)

    return (
        "📌 <b>Общая статистика TikSaves</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Пользователей: <b>{users_total}</b>\n"
        f"👑 Администраторов: <b>{admins_total}</b>\n"
        f"🚫 Активных банов: <b>{bans_active}</b> (всего за всё время: {bans_total})\n\n"
        f"🎬 Видео скачано: <b>{video_ops}</b>\n"
        f"🖼️ Фото-сессий: <b>{photo_ops}</b> (фото отправлено: {photos_sent})\n"
        f"🎵 Музыки отправлено: <b>{audio_sent}</b>\n"
        f"⭐ Stars получено: <b>{stars_total}</b>\n"
        f"❌ Ошибок всего: <b>{errors_total}</b>"
    )


async def _update_pinned_overview(bot: Bot) -> None:
    text = _pinned_overview_text()
    info = store.data.get("pinned_stats") or {}
    msg_id = info.get("message_id")
    chat_id = info.get("chat_id") or LOG_CHANNEL_ID

    if msg_id:
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, parse_mode="HTML")
            return
        except Exception as e:
            if "not modified" in str(e).lower():
                # Текст не изменился с прошлого раза (не с чем сравнивать) — это
                # не ошибка, ничего пересоздавать не нужно.
                return
            log.info("pinned_overview: не смог отредактировать (%s) — пересоздаю сообщение", e)

    try:
        msg = await bot.send_message(chat_id=LOG_CHANNEL_ID, text=text, parse_mode="HTML")
        store.data["pinned_stats"] = {"chat_id": msg.chat.id, "message_id": msg.message_id}
        store._mark_dirty()
        with contextlib.suppress(Exception):
            await bot.pin_chat_message(chat_id=msg.chat.id, message_id=msg.message_id, disable_notification=True)
    except Exception as e:
        log.error("pinned_overview: не удалось создать/закрепить сообщение: %s", e)


async def pinned_overview_loop(bot: Bot) -> None:
    """Обновляет закреплённую общую статистику в лог-канале раз в PINNED_STATS_INTERVAL_SEC."""
    while True:
        try:
            await _update_pinned_overview(bot)
            await asyncio.sleep(PINNED_STATS_INTERVAL_SEC)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("pinned_overview_loop: %s", e)
            await asyncio.sleep(300)


def start_pinned_overview(bot: Bot) -> asyncio.Task:
    global _pinned_stats_task
    _pinned_stats_task = asyncio.create_task(pinned_overview_loop(bot))
    return _pinned_stats_task
