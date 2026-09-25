"""
Действия после ЛЮБОГО успешного скачивания (видео/фото, любой источник):
периодическое персональное напоминание (раз в NUDGE_EVERY скачиваний,
случайный выбор из текстов) — только тому, кто только что скачал, не
рассылка всем.

Раньше здесь же начислялись баллы рефереру (реферальная система удалена).
"""
import contextlib

from storage import store

NUDGE_EVERY = 5  # раз в сколько скачиваний может сработать напоминание


async def _maybe_send_nudge(bot, uid: int) -> None:
    import random
    from broadcast import REMINDER_MSG, DONATE_REMINDER_MSG
    from helpers import to_html_simple

    total = store.bump_download_counter(uid)
    if total % NUDGE_EVERY != 0:
        return
    text = random.choice([REMINDER_MSG, DONATE_REMINDER_MSG])
    with contextlib.suppress(Exception):
        await bot.send_message(uid, to_html_simple(text), parse_mode="HTML")


async def after_download_hooks(bot, uid: int, label: str) -> None:
    """Общие действия после успешного скачивания. label оставлен в сигнатуре
    для совместимости с местами вызова, сейчас не используется."""
    await _maybe_send_nudge(bot, uid)
