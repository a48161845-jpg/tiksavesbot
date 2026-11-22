"""
Оформление текстов бота (единый стиль экранов).

Правила:
  • заголовок — одна жирная строка с одним эмодзи: <b>🎵 Заголовок</b>;
  • без «заборов» из ━━━; блоки разделяет пустая строка;
  • шаги — «1  текст» с жирной цифрой, перечни — «•»;
  • подсказки и оговорки — в <blockquote> внизу экрана;
  • статусы: ⏳ в процессе · 📤 отправка · ✅ готово · ⚠️ внимание · ❌ ошибка.
Здесь только чистые функции без зависимостей — их можно импортировать откуда угодно.
"""
from typing import Iterable

BRAND = "@tiksavesbot"
PLATFORMS = "TikTok · YouTube · Instagram · VK · Pinterest · X · Rutube · Reddit"


def title(emoji: str, text: str) -> str:
    return f"<b>{emoji} {text}</b>"


def quote(text: str) -> str:
    return f"<blockquote>{text}</blockquote>"


def bullets(items: Iterable[str]) -> str:
    return "\n".join(f"• {i}" for i in items)


def steps(items: Iterable[str]) -> str:
    return "\n".join(f"<b>{n}</b>  {t}" for n, t in enumerate(items, 1))


def screen(*blocks: str) -> str:
    """Склеивает блоки экрана через пустую строку (пустые пропускает)."""
    return "\n\n".join(b for b in blocks if b)


def head(emoji: str, text: str, subtitle: str = "") -> str:
    """Заголовок + (необязательно) строка-подзаголовок сразу под ним."""
    return title(emoji, text) + (f"\n{subtitle}" if subtitle else "")
