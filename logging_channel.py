"""
Буферизованная отправка логов в служебный Telegram-канал,
а также автосейв хранилища в фоне.
"""
import re
import time
import asyncio
import contextlib
from typing import Optional, Tuple, List

from aiogram import Bot
from aiogram.types import LinkPreviewOptions
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest

from config import LOG_CHANNEL_ID, AUTO_SAVE_INTERVAL_SEC, log
from helpers import html_escape, code, now_msk_str
from storage import store

# ================== AUTOSAVE LOOP ==================

async def autosave_loop() -> None:
    while True:
        try:
            await asyncio.sleep(AUTO_SAVE_INTERVAL_SEC)
            await store.save_unthrottled()
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.exception("autosave_loop: %s", e)

# ================== LOGS TO CHANNEL (BUFFERED + DUAL TAGS) ==================
LOG_RATE_LIMIT_SEC = 0.25

CAT_TAG = {
    "user": "user",
    "userstats": "userstats",
    "help": "help",
    "support": "support",
    "donate_open": "donate_open",
    "gate_ban": "gate_ban",
    "gate_spam": "gate_spam",
    "photodl": "photodl",
    "videodl": "videodl",
    "audiodl": "audiodl",
    "dlerr": "dlerr",
    "spamstrike": "spamstrike",
    "dlstrike": "dlstrike",
    "photostrike": "photostrike",
    "autoban": "autoban",
    "userban": "userban",
    "userunban": "userunban",
    "adminadd": "adminadd",
    "admindel": "admindel",
    "providerfallback": "providerfallback",
    "yt_dlp_outdated": "ytdlpold",
    "stars": "stars",
    "broadcast": "broadcast",
    "admin": "admin",
}

# Разрешённые категории лога (в канал): запуск/остановка бота (шлются
# напрямую, не через эту фильтрацию), ошибки скачивания, сбои провайдера,
# новые пользователи, покупки/донаты, баны/разбаны и назначение/снятие
# администраторов, плюс рассылки. Всё остальное (скачивания видео/фото/музыки,
# открытие меню, обычная статистика, просмотр админ-панели и т.п.)
# в канал не шлётся — только считается в статистику/БД.
ALLOWED_LOG_CATEGORIES = {
    "dlerr",
    "providerfallback",
    "yt_dlp_outdated",
    "user",
    "stars",
    "userban",
    "userunban",
    "autoban",
    "adminadd",
    "admindel",
    "broadcast",
}

def base_tag_for(category: str) -> str:
    return f"#{CAT_TAG.get(category, 'log')}"

def numbered_tag_for(category: str) -> str:
    seq = store.next_seq(category)
    return f"#{CAT_TAG.get(category, 'log')}{seq}"

def format_user_for_log(label: str, uid: int) -> str:
    """
    Кликабельное упоминание пользователя для логов.

    Важный нюанс Telegram: бот может узнать имя/юзернейм только у тех,
    кто хотя бы раз ему писал (или есть в кэше store) — так устроен Bot API,
    это не баг бота. Если имени нет — показываем просто ID один раз
    (раньше в этом случае ID дублировался: "12345 (12345)").

    Если известен @username — ссылка на https://t.me/username (работает
    всегда, у любого клиента). Если известны только имя/фамилия —
    tg://user?id=... (best-effort упоминание, кликабельно не всегда —
    тоже ограничение Telegram, а не бота).
    """
    s = (label or "").strip()
    m = re.search(r"\((\d+)\)\s*$", s)
    name_part = s[:m.start()].strip() if m else s

    if not name_part or name_part == str(uid):
        return code(uid)

    if name_part.startswith("@"):
        username = name_part[1:]
        return f'<a href="https://t.me/{username}">{html_escape(name_part)}</a> ({code(uid)})'

    return f'<a href="tg://user?id={uid}">{html_escape(name_part)}</a> ({code(uid)})'

_log_queue: "asyncio.Queue[Tuple[int, str]]" = asyncio.Queue(maxsize=2000)
_log_worker_task: Optional[asyncio.Task] = None
_last_log_ts = 0.0

async def _log_worker(bot: Bot) -> None:
    global _last_log_ts
    while True:
        try:
            chat_id, text = await _log_queue.get()
            try:
                dt = time.time() - _last_log_ts
                if dt < LOG_RATE_LIMIT_SEC:
                    await asyncio.sleep(LOG_RATE_LIMIT_SEC - dt)

                await send_channel_log_reliable(bot, text, chat_id=chat_id, attempts=3)
                _last_log_ts = time.time()
            except Exception as e:
                log.warning("log worker: не удалось отправить лог в канал %s: %s: %s", chat_id, e.__class__.__name__, e)
            finally:
                _log_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception:
            pass

async def start_log_worker(bot: Bot) -> None:
    global _log_worker_task
    if _log_worker_task and not _log_worker_task.done():
        return
    _log_worker_task = asyncio.create_task(_log_worker(bot))

async def stop_log_worker() -> None:
    global _log_worker_task
    try:
        await asyncio.wait_for(_log_queue.join(), timeout=3.0)
    except Exception:
        pass
    if _log_worker_task and not _log_worker_task.done():
        _log_worker_task.cancel()
        with contextlib.suppress(Exception):
            await _log_worker_task

async def send_channel_log_reliable(bot: Bot, text: str, chat_id: int = 0, attempts: int = 5) -> bool:
    """Отправка прямо сейчас (не через очередь) с ретраями: flood-wait, сеть, битый HTML.
    Для важных сообщений (запуск/остановка/перед перезапуском). Ошибки не глотаются — пишутся в лог."""
    chat_id = chat_id or LOG_CHANNEL_ID
    parse_mode = "HTML"
    last: Optional[Exception] = None
    for i in range(attempts):
        try:
            await bot.send_message(chat_id, text, parse_mode=parse_mode,
                                   link_preview_options=LinkPreviewOptions(is_disabled=True))
            return True
        except TelegramRetryAfter as e:
            last = e
            await asyncio.sleep(min(float(e.retry_after) + 1, 60))
        except TelegramBadRequest as e:
            last = e
            if parse_mode and "parse" in str(e).lower():
                parse_mode = None  # битая HTML-разметка — шлём как обычный текст
                continue
            break  # chat not found / not enough rights и т.п. — ретраи бесполезны
        except Exception as e:
            last = e
            await asyncio.sleep(2 * (i + 1))
    log.error("send_channel_log_reliable: не удалось отправить в %s: %s: %s",
              chat_id, last.__class__.__name__, last)
    return False

async def send_channel_log(_bot: Bot, text: str) -> None:
    try:
        _log_queue.put_nowait((LOG_CHANNEL_ID, text))
    except asyncio.QueueFull:
        pass

async def log_event(bot: Bot, category: str, lines: List[str]) -> None:
    if category not in ALLOWED_LOG_CATEGORIES:
        return
    t_base = base_tag_for(category)
    t_num = numbered_tag_for(category)
    if category == "audiodl":
        t_base = "#audiodl #audiodl23"
    header = f"🧾 Лог: <b>{html_escape(category)}</b>\n🕒 {now_msk_str()}"
    lines = list(lines)
    if category == "dlerr":
        try:
            from error_explain import explain_log_line
            hint = explain_log_line(lines)
            if hint:
                lines.append(hint)
        except Exception:
            pass
    await send_channel_log(bot, f"{t_base} {t_num}\n" + "\n".join([header, *lines]))

async def log_admin_action_to_channel(bot: Bot, title: str, lines: List[str]) -> None:
    await log_event(
        bot,
        "admin",
        [
            "👑 Категория: <b>Админ-действие</b>",
            f"🧩 Действие: <b>{html_escape(title)}</b>",
            *lines,
        ],
    )
