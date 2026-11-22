"""
Автозапуск Local Bot API Server (telegram-bot-api) рядом с ботом, если в
.env заданы API_ID и API_HASH — чтобы не нужно было руками поднимать
отдельный процесс (удобно в первую очередь для Termux, где нет docker).

Если бинарник telegram-bot-api не найден или API_ID/API_HASH не заданы —
просто ничего не делаем, бот работает как обычно (лимит 50 МБ на файл).
"""
import asyncio
import contextlib

import aiohttp
from pathlib import Path
from typing import Optional

from core.config import API_ID, API_HASH, LOCAL_BOT_API_BIN, LOCAL_BOT_API_PORT, LOCAL_BOT_API_DIR


async def _port_open(host: str, port: int) -> bool:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=1)
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
        return True
    except Exception:
        return False


async def start_local_bot_api() -> Optional[asyncio.subprocess.Process]:
    """Пытается поднять telegram-bot-api. Возвращает Process, если запустили
    сами (и его потом нужно останавливать вместе с ботом), или None — если
    не настроено, сервер уже был поднят кем-то другим, или не получилось
    (в этом случае просто печатаем предупреждение и едем дальше на обычном
    Bot API с лимитом 50 МБ)."""
    if not (API_ID and API_HASH):
        return None

    if await _port_open("127.0.0.1", LOCAL_BOT_API_PORT):
        print(f"ℹ️ На порту {LOCAL_BOT_API_PORT} уже что-то слушает — считаю, что Local Bot API Server уже поднят вручную.")
        return None

    Path(LOCAL_BOT_API_DIR).mkdir(parents=True, exist_ok=True)

    try:
        proc = await asyncio.create_subprocess_exec(
            LOCAL_BOT_API_BIN,
            f"--api-id={API_ID}",
            f"--api-hash={API_HASH}",
            f"--http-port={LOCAL_BOT_API_PORT}",
            f"--dir={LOCAL_BOT_API_DIR}",
            "--local",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print(
            f"⚠️ Бинарник '{LOCAL_BOT_API_BIN}' не найден (LOCAL_BOT_API_BIN в .env). "
            "Local Bot API Server не запущен — файлы тяжелее 50 МБ отправляться не будут. "
            "Смотри инструкцию по сборке telegram-bot-api для Termux."
        )
        return None
    except Exception as e:
        print(f"⚠️ Не удалось запустить telegram-bot-api: {e.__class__.__name__}: {e}")
        return None

    for _ in range(30):
        if await _port_open("127.0.0.1", LOCAL_BOT_API_PORT):
            print(f"✅ Local Bot API Server поднят (pid={proc.pid}, порт {LOCAL_BOT_API_PORT}).")
            return proc
        if proc.returncode is not None:
            print("⚠️ telegram-bot-api завершился сразу после запуска — проверь API_ID/API_HASH в .env.")
            return None
        await asyncio.sleep(1)

    print("⚠️ Local Bot API Server не ответил на порту за 30 секунд — продолжаю без него.")
    return proc


async def stop_local_bot_api(proc: Optional[asyncio.subprocess.Process]) -> None:
    if proc is None:
        return
    with contextlib.suppress(Exception):
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=10)


# Итог выбора режима Bot API при старте: ("local" | "cloud", причина). Заполняет bot.py, читает /botapi и сообщение о запуске.
STATE = {"mode": "unknown", "reason": ""}


def set_state(mode: str, reason: str) -> None:
    STATE["mode"], STATE["reason"] = mode, reason


def diagnose_config() -> str:
    """Почему локальный Bot API может быть не настроен: какие переменные не заданы, есть ли бинарник и .env."""
    from core.config import ENV_PATH
    import shutil
    problems = []
    if not API_ID:
        problems.append("не задан API_ID")
    if not API_HASH:
        problems.append("не задан API_HASH")
    if (API_ID and API_HASH) and not (shutil.which(LOCAL_BOT_API_BIN) or Path(LOCAL_BOT_API_BIN).exists()):
        problems.append(f"не найден бинарник telegram-bot-api ({LOCAL_BOT_API_BIN})")
    if problems:
        problems.append(f"файл .env {'найден' if Path(ENV_PATH).exists() else 'НЕ найден'}: {ENV_PATH}")
    return "; ".join(problems)


async def ensure_local_login(base_url: str, token: str) -> bool:
    """
    Бота нужно один раз "разлогинить" на облачном api.telegram.org, прежде чем он заработает на Local Bot API
    Server. Порядок: сначала терпеливо ждём локальный сервер (он может ещё стартовать — тогда logOut в облаке
    не нужен и вреден: после него облако 10 минут не пускает бота), и только потом logOut и повторные проверки.
    Возвращает True, если локальный сервер отвечает на getMe.
    """
    async def _get_me() -> bool:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
                async with s.get(f"{base_url}/bot{token}/getMe") as r:
                    js = await r.json(content_type=None)
                    return bool(js.get("ok"))
        except Exception:
            return False

    for _ in range(5):  # локальный сервер мог только что подняться
        if await _get_me():
            return True
        await asyncio.sleep(2)

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as s:
            async with s.post(f"https://api.telegram.org/bot{token}/logOut") as r:
                js = await r.json(content_type=None)
                print(f"ℹ️ logOut с облачного Bot API: {js}")
    except Exception as e:
        print(f"⚠️ logOut с облачного Bot API не удался: {e.__class__.__name__}: {e}")

    for _ in range(20):  # после logOut локальному серверу нужно время, чтобы принять бота
        await asyncio.sleep(3)
        if await _get_me():
            return True
    return False
