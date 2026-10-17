"""
Автообновление yt-dlp. YouTube меняет защиту каждые несколько недель, и старый
yt-dlp внезапно начинает отдавать только 360p или ошибки. Бот сам раз в N часов
выполняет `pip install -U yt-dlp[default]` (по умолчанию nightly-сборки — фиксы
выходят в них быстрее) и, если версия реально поменялась, один раз
перезапускает себя, чтобы подхватить новый код.

Отключить: YTDLP_AUTOUPDATE=0. Стабильные релизы вместо nightly: YTDLP_UPDATE_PRE=0.
Если хост запрещает pip install (read-only) — тихо ничего не делаем.
"""
import asyncio
import contextlib
import os
import sys
from importlib import metadata

from config import YTDLP_AUTOUPDATE, YTDLP_UPDATE_PRE, YTDLP_UPDATE_EVERY_HOURS, log


def _installed_version() -> str:
    try:
        return metadata.version("yt-dlp")
    except Exception:
        return ""


def _loaded_version() -> str:
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except Exception:
        return ""


async def _pip_update() -> bool:
    cmd = [sys.executable, "-m", "pip", "install", "-U", "--quiet", "--disable-pip-version-check"]
    if YTDLP_UPDATE_PRE:
        cmd.append("--pre")
    cmd.append("yt-dlp[default]")
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
        )
        _, err = await asyncio.wait_for(proc.communicate(), timeout=300)
    except Exception as e:
        log.info("yt-dlp autoupdate: pip не запустился: %s", e)
        return False
    if proc.returncode != 0:
        # Повторим с --break-system-packages (Debian/Ubuntu с системным pip).
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, "--break-system-packages",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
            )
            _, err = await asyncio.wait_for(proc.communicate(), timeout=300)
        except Exception:
            return False
        if proc.returncode != 0:
            log.info("yt-dlp autoupdate: pip завершился с ошибкой: %s", (err or b"")[-300:].decode("utf-8", "ignore"))
            return False
    return True


async def check_and_update(bot=None) -> None:
    """Один проход: обновить пакет; если версия изменилась — сообщить в лог-канал и перезапуститься."""
    before = _loaded_version()
    if not await _pip_update():
        return
    after = _installed_version()
    if not after or after == before:
        return

    log.info("yt-dlp обновлён: %s -> %s", before, after)
    if os.environ.get("YTDLP_RESTARTED") == "1":
        # Уже перезапускались ради обновления, но загружается всё ещё старая версия
        # (pip поставил в другое место) — не уходим в бесконечный перезапуск.
        return

    if bot is not None:
        with contextlib.suppress(Exception):
            # Напрямую, а не через очередь: os.execv ниже убивает процесс до того,
            # как фоновый воркер успел бы отправить сообщение из очереди.
            from logging_channel import send_channel_log_reliable
            await send_channel_log_reliable(bot, attempts=2, text=f"🔄 <b>yt-dlp обновлён</b>: {before} → {after}\nПерезапускаюсь, чтобы применить.")
    with contextlib.suppress(Exception):
        from storage import store
        await store.save_unthrottled()

    os.environ["YTDLP_RESTARTED"] = "1"
    # execv не вызывает finally в bot.py — останавливаем локальный Bot API вручную не нужно
    # (новый процесс увидит занятый порт и подхватит его), но БД/сессии закрываем штатно.
    os.execv(sys.executable, [sys.executable] + sys.argv)


async def autoupdate_loop(bot=None) -> None:
    if not YTDLP_AUTOUPDATE:
        return
    # Первая проверка — через минуту после старта (чтобы не тормозить запуск).
    await asyncio.sleep(60)
    while True:
        try:
            await check_and_update(bot)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # никогда не роняем бота из-за апдейтера
            log.info("yt-dlp autoupdate: ошибка: %s", e)
        await asyncio.sleep(max(1, YTDLP_UPDATE_EVERY_HOURS) * 3600)
