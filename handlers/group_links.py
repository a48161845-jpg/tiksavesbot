"""
Группы: бот реагирует на КАЖДУЮ поддерживаемую ссылку, которую прислали в чат.

Что покрывает (чего не умел обычный `F.text`-хендлер):
  * ссылка в подписи к фото/видео/файлу (caption);
  * «спрятанная» ссылка — слово-гиперссылка (entity text_link);
  * несколько ссылок в одном сообщении — каждая обрабатывается отдельно (до MAX_LINKS_PER_MESSAGE).
Сообщения без поддерживаемых ссылок, команды и личные чаты проходят дальше без изменений.
Сам скачивающий код не меняется: для каждой ссылки хендлерам отдаётся копия сообщения, где text = ссылка.
"""
import re
from typing import Any, List

from aiogram import BaseMiddleware

from core.config import GROUP_AUTO_LINKS, log
from core.globals_state import dp
from core.helpers import has_supported_link, is_group_chat

MAX_LINKS_PER_MESSAGE = 3
_URL_RE = re.compile(r"https?://[^\s<>]+", re.I)


def collect_links(text: str, entities=None) -> List[str]:
    """Поддерживаемые ссылки из текста + text_link-сущностей, без повторов, по порядку."""
    found: List[str] = []
    for m in _URL_RE.finditer(text or ""):
        found.append(m.group(0).rstrip(").,;!?»\"'"))
    for e in entities or []:
        if getattr(e, "type", "") == "text_link" and getattr(e, "url", None):
            found.append(str(e.url))
    out: List[str] = []
    for u in found:
        if u not in out and has_supported_link(u):
            out.append(u)
    return out[:MAX_LINKS_PER_MESSAGE]


class GroupLinksMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Any, data: dict):
        if not (GROUP_AUTO_LINKS and is_group_chat(event) and getattr(event, "from_user", None)):
            return await handler(event, data)

        raw = event.text or event.caption or ""
        if not raw or raw.startswith("/"):
            return await handler(event, data)

        links = collect_links(raw, event.entities if event.text else event.caption_entities)
        if not links:
            return await handler(event, data)

        result = None
        for link in links:
            try:
                result = await handler(
                    event.model_copy(update={"text": link, "caption": None, "entities": None, "caption_entities": None}),
                    data,
                )
            except Exception:
                log.exception("group link failed: %s", link)
        return result


dp.message.outer_middleware(GroupLinksMiddleware())
