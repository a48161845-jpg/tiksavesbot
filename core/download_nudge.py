"""
Действия после ЛЮБОГО успешного скачивания (видео/фото, любой источник): частое персональное напоминание
о донате — только тому, кто только что скачал (не рассылка всем).

  • срабатывает каждые NUDGE_EVERY скачиваний (по умолчанию 2; env NUDGE_EVERY);
  • выбор: 70% — «кричащее» напоминание о донате (6 вариантов), 20% — промо Premium, 10% — напоминание про /support;
  • к сообщению сразу приклеены кнопки (Stars / любой банк / Donation Alerts / Premium);
  • у пользователей с активным Premium напоминаний нет.
Тексты и переводы — core/nudge_texts.py.
"""
import contextlib
import os
import random

from aiogram.types import LinkPreviewOptions

from core.config import PREMIUM_LIMIT_MULT
from core.nudge_texts import DONATE_NUDGES, PREMIUM_NUDGE, SUPPORT_NUDGE
from core.storage import store

NUDGE_EVERY = max(1, int(os.getenv("NUDGE_EVERY", "2")))  # раз в сколько скачиваний показывать напоминание
_WEIGHTS = (("donate", 70), ("premium", 20), ("support", 10))


def pick_nudge(rng=random) -> tuple:
    """-> (вид, русский текст). Вид: donate | premium | support."""
    kind = rng.choices([k for k, _ in _WEIGHTS], weights=[w for _, w in _WEIGHTS])[0]
    if kind == "donate":
        return kind, rng.choice(DONATE_NUDGES)["ru"]
    if kind == "premium":
        return kind, PREMIUM_NUDGE["ru"]
    return kind, SUPPORT_NUDGE["ru"]


async def _maybe_send_nudge(bot, uid: int) -> None:
    from i18n import tr, get_lang
    from ui.keyboards import nudge_kb

    total = store.bump_download_counter(uid)
    if total % NUDGE_EVERY != 0:
        return
    if store.is_premium(uid):
        return
    kind, ru_text = pick_nudge()
    text = tr(uid, ru_text, m=PREMIUM_LIMIT_MULT)
    with contextlib.suppress(Exception):
        await bot.send_message(
            uid, text, parse_mode="HTML",
            reply_markup=nudge_kb(get_lang(uid), kind),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )


async def after_download_hooks(bot, uid: int, label: str) -> None:
    """Общие действия после успешного скачивания. label оставлен в сигнатуре для совместимости."""
    await _maybe_send_nudge(bot, uid)
