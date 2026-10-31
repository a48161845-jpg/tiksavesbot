"""
Автоперевод текста рассылок (русский -> язык пользователя).

Сначала пробуется готовый перевод из i18n (для пресетов-напоминаний), для произвольного текста админа
используется бесплатный переводчик (translate.googleapis.com, client=gtx, без ключа). Работает так:
  • HTML-теги не трогаются, переводятся только текстовые куски; содержимое <code>/<pre> не переводится;
  • перевод идёт построчно — переносы строк и пустые строки сохраняются;
  • результаты кэшируются в памяти; при любой ошибке сети возвращается исходный русский текст
    (рассылка не должна ломаться из-за переводчика).
"""
import asyncio
import html as _html
import re
from typing import Dict, List, Optional, Tuple

import aiohttp

from config import log

_TAG_RE = re.compile(r"(<[^>]+>)")
_HAS_LETTER = re.compile(r"[A-Za-zА-Яа-яЁёІіЇїЄєҐґҚқҒғҢңӨөҮүҰұӘәҺһЎўҲҳ]")
_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
_cache: Dict[Tuple[str, str], str] = {}
_SKIP_TAGS = ("code", "pre")


async def _translate_line(session: aiohttp.ClientSession, text: str, lang: str, sem: asyncio.Semaphore) -> str:
    key = (lang, text)
    if key in _cache:
        return _cache[key]
    params = {"client": "gtx", "sl": "ru", "tl": lang, "dt": "t", "q": text}
    try:
        async with sem:
            async with session.get(_ENDPOINT, params=params, timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status != 200:
                    raise RuntimeError(f"HTTP {r.status}")
                data = await r.json(content_type=None)
        out = "".join(part[0] for part in (data[0] or []) if part and part[0])
        out = out.strip("\r\n")
        if not out:
            return text
        _cache[key] = out
        return out
    except Exception as e:
        log.warning("auto_translate[%s]: %s", lang, e)
        return text


async def _translate_chunk(session, chunk: str, lang: str, sem) -> str:
    """Один текстовый кусок между тегами: сохраняем крайние пробелы/переносы, переводим построчно."""
    lines = _html.unescape(chunk).split("\n")

    async def one(line: str) -> str:
        if not _HAS_LETTER.search(line):
            return line
        lead = line[: len(line) - len(line.lstrip())]
        trail = line[len(line.rstrip()):]
        core = line.strip()
        return lead + await _translate_line(session, core, lang, sem) + trail

    done = await asyncio.gather(*(one(ln) for ln in lines))
    return _html.escape("\n".join(done), quote=False)


async def translate_html(html_text: str, lang: str, session: Optional[aiohttp.ClientSession] = None) -> str:
    """Переводит Telegram-HTML с русского на lang. Теги сохраняются, при сбое — исходный текст."""
    if not html_text or lang == "ru":
        return html_text
    own = session is None
    sess = session or aiohttp.ClientSession()
    sem = asyncio.Semaphore(4)
    try:
        parts: List[str] = _TAG_RE.split(html_text)
        skip_depth = 0
        jobs = []
        for part in parts:
            if _TAG_RE.fullmatch(part or ""):
                m = re.match(r"<\s*(/?)\s*([a-zA-Z0-9-]+)", part)
                if m and m.group(2).lower() in _SKIP_TAGS:
                    skip_depth = max(0, skip_depth + (-1 if m.group(1) else 1))
                jobs.append(("tag", part))
            elif skip_depth or not part.strip():
                jobs.append(("raw", part))
            else:
                jobs.append(("txt", part))
        results = await asyncio.gather(*(
            _translate_chunk(sess, p, lang, sem) if kind == "txt" else _noop(p) for kind, p in jobs
        ))
        return "".join(results)
    except Exception as e:
        log.warning("translate_html[%s]: %s", lang, e)
        return html_text
    finally:
        if own:
            await sess.close()


async def _noop(x: str) -> str:
    return x
