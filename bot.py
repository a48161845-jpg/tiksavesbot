"""
Точка входа: поднимает aiohttp-сессию, провайдеров, фоновые задачи
(автосейв, лог-воркер, рассылки, ежемесячный отчёт) и запускает polling.
"""
import asyncio
import contextlib
import time
from typing import Optional, List

import aiohttp
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode

import config as _config
from config import BOT_TOKEN, GLOBAL_CONCURRENCY, ADMINS, LOCAL_BOT_API_URL, LOCAL_BOT_API_IS_LOCAL
from helpers import now_msk_str, html_escape
from storage import store, init_db, close_db
import globals_state
from globals_state import dp
from providers import TikWMClient, BaseProvider, ProviderSwitcher
from logging_channel import autosave_loop, start_log_worker, stop_log_worker, send_channel_log
from db_report import send_db_json
from local_bot_api import start_local_bot_api, stop_local_bot_api
from ytdlp_updater import autoupdate_loop
from youtube_provider import ffmpeg_available, js_runtime_available

# Импорт регистрирует все хендлеры (@dp.message/@dp.callback_query) на dp.
import handlers  # noqa: F401

_autosave_task: Optional[asyncio.Task] = None
_ytdlp_update_task: Optional[asyncio.Task] = None
_monthly_task: Optional[asyncio.Task] = None
_pinned_overview_task: Optional[asyncio.Task] = None
_local_bot_api_proc = None


def _janitor_temp_files():
    import glob, os
    for pat in ("tmp_video_*", "*.part", "cobalt_*", "inline_*", "*.audio.*", "*.ytdl"):
        for f in glob.glob(pat):
            try:
                if os.path.isfile(f):
                    os.remove(f)
            except Exception:
                pass


async def main():
    _janitor_temp_files()
    global _autosave_task, _monthly_task, _pinned_overview_task, _local_bot_api_proc, _ytdlp_update_task

    # 1) Инициализируем БД (создаём таблицы, мигрируем из JSON если нужно)
    await init_db()

    # 2) Загружаем данные в память
    await store.load_from_db()

    # 3) Если заданы API_ID/API_HASH — поднимаем Local Bot API Server рядом
    #    с ботом (тем же процессом-родителем), чтобы снять лимит 50 МБ на
    #    отправку файлов. Если не задано/бинарник не найден — просто едем
    #    дальше на обычном облачном Bot API.
    _local_bot_api_proc = await start_local_bot_api()

    # Если локальный сервер должен был быть, но на порту его нет (не собрался
    # бинарник / неверные API_ID/API_HASH) — не ломаем бота целиком, а
    # возвращаемся на облачный Bot API с лимитом 49 МБ (+ авто-сжатие видео).
    local_api_ok = bool(_config.LOCAL_BOT_API_URL)
    if local_api_ok:
        from urllib.parse import urlparse
        from local_bot_api import _port_open
        _u = urlparse(_config.LOCAL_BOT_API_URL)
        if _u.hostname and _u.port and not await _port_open(_u.hostname, _u.port):
            print("⚠️ Local Bot API Server недоступен — работаю через облачный Bot API (лимит 49 МБ, большие видео сжимаются).")
            _config.downgrade_to_cloud_limits()
            local_api_ok = False
        else:
            from local_bot_api import ensure_local_login
            if not await ensure_local_login(_config.LOCAL_BOT_API_URL, BOT_TOKEN):
                print("⚠️ Local Bot API Server не принял бота (проверь API_ID/API_HASH) — работаю через облачный Bot API.")
                _config.downgrade_to_cloud_limits()
                local_api_ok = False

    # Скачивание видео с источника (tikwm/yt-dlp) может занимать долго для
    # тяжёлых файлов (до 2 ГБ) — общего total-лимита нет, только лимиты на
    # установление соединения и на "тишину" в потоке (если сервер перестал
    # присылать данные — считаем зависшим).
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=15, sock_read=90)
    connector = aiohttp.TCPConnector(limit=50, ttl_dns_cache=300)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        # Если задан LOCAL_BOT_API_URL — шлём запросы к боту через свой
        # Local Bot API Server (только там снимается лимит в 50 МБ на
        # отправку файлов, до 2000 МБ). Подробности — в README.
        bot_session = None
        if local_api_ok:
            api_server = TelegramAPIServer.from_base(LOCAL_BOT_API_URL, is_local=LOCAL_BOT_API_IS_LOCAL)
            # Большие файлы (до 2 ГБ) заливаются долго: локальный сервер отвечает только
            # когда файл полностью ушёл в Telegram. Дефолтные 60 сек клиента обрывали
            # такую отправку — отсюда "2 ГБ не работает".
            bot_session = AiohttpSession(api=api_server, timeout=7200)

        bot = Bot(
            BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            session=bot_session,
        )

        primary = TikWMClient(session, bot=bot)
        providers: List[BaseProvider] = [primary]
        provider_names = ["tikwm (осн.)"]

        switcher = ProviderSwitcher(providers, bot)
        globals_state.set_global_provider(primary)
        globals_state.set_global_switcher(switcher)

        await start_log_worker(bot)

        _autosave_task = asyncio.create_task(autosave_loop())
        _ytdlp_update_task = asyncio.create_task(autoupdate_loop(bot))

        start_ts = time.time()
        shutdown_reason = "⏹️ Штатная остановка"

        try:
            me = await bot.get_me()
            bans_active = len(store.list_bans())
            admins_total = len(ADMINS) + len(store.get_extra_admins())
            provider_line = " + ".join(provider_names)
            api_mode_line = f"🌐 Bot API: <b>{'локальный сервер (до 2 ГБ)' if local_api_ok else 'облачный (лимит 50 МБ, большие видео авто-сжимаются)'}</b>"
            ffmpeg_line = (
                "🎞️ ffmpeg: <b>найден</b> — доступна склейка видео+аудио (качество выше ~720p работает)"
                if ffmpeg_available()
                else (
                    "🎞️ ffmpeg: <b>НЕ найден</b> ⚠️ — качество выше ~720p работать НЕ будет (YouTube не "
                    "отдаёт готовые файлы выше 720p без склейки видео+аудио). Установи ffmpeg или проверь, "
                    "что пакет imageio-ffmpeg реально ставится на этом сервере."
                )
            )
            js_line = (
                "🧩 JS-движок (deno/node): <b>найден</b> — YouTube отдаёт видео"
                if js_runtime_available()
                else "🧩 JS-движок (deno/node): <b>НЕ найден</b> ⚠️ — YouTube отдаст только звук и превью "
                "(ошибка «Requested format is not available»). Проверь, что в requirements.txt установился пакет deno."
            )
            await send_channel_log(
                bot,
                "🚀 <b>Бот запущен</b>\n"
                f"🤖 Бот: @{me.username} (<code>{me.id}</code>)\n"
                f"👥 Пользователей в базе: <b>{store.get_users_count()}</b>\n"
                f"👑 Администраторов: <b>{admins_total}</b>\n"
                f"🚫 Активных банов: <b>{bans_active}</b>\n"
                f"📡 Провайдер(ы): <b>{provider_line}</b>\n"
                f"{api_mode_line}\n"
                f"{ffmpeg_line}\n"
                f"{js_line}\n"
                f"⚙️ Параллельных скачиваний: <b>{GLOBAL_CONCURRENCY}</b>\n"
                f"🕒 Время запуска: {now_msk_str()}",
            )
            await dp.start_polling(bot, client=primary, switcher=switcher)
        except asyncio.CancelledError:
            shutdown_reason = "⏹️ Штатная остановка (получен сигнал остановки)"
            raise
        except Exception as e:
            shutdown_reason = f"💥 Аварийная остановка: <b>{e.__class__.__name__}</b> — {html_escape(str(e)[:200])}"
            raise
        finally:
            for task in (_autosave_task, _monthly_task, _pinned_overview_task, _ytdlp_update_task):
                if task and not task.done():
                    task.cancel()
                    with contextlib.suppress(Exception):
                        await task

            await store.save_unthrottled()

            uptime_sec = int(time.time() - start_ts)
            uptime_str = f"{uptime_sec // 3600}ч {(uptime_sec % 3600) // 60}м {uptime_sec % 60}с"
            with contextlib.suppress(Exception):
                await send_channel_log(
                    bot,
                    "🛑 <b>Бот остановлен</b>\n"
                    f"{shutdown_reason}\n"
                    f"⏳ Время работы: <b>{uptime_str}</b>\n"
                    f"👥 Пользователей в базе: <b>{store.get_users_count()}</b>\n"
                    f"🕒 Время остановки: {now_msk_str()}",
                )

            await stop_log_worker()
            await close_db()
            await stop_local_bot_api(_local_bot_api_proc)


if __name__ == "__main__":
    asyncio.run(main())
