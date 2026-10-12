"""
Мультиязычность. Ключ перевода — сама русская строка (так в коде сразу видно,
что показывается пользователю): tr(message, "⏳ Скачиваю…").
Языки: ru (по умолчанию), en, uk. Чтобы добавить язык — заведи словарь
TRANSLATIONS["xx"] и строку в LANGUAGES.

Язык хранится в store.data["user_lang"][uid]. Если строки нет в словаре языка —
показывается русский оригинал (бот никогда не падает из-за отсутствия перевода).
"""
from typing import Any, Dict

DEFAULT_LANG = "ru"

LANGUAGES: Dict[str, str] = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "uk": "🇺🇦 Українська",
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {"en": {}, "uk": {}}


def _reg(ru: str, en: str, uk: str) -> None:
    TRANSLATIONS["en"][ru] = en
    TRANSLATIONS["uk"][ru] = uk


def get_lang(uid: int) -> str:
    from storage import store
    try:
        lang = store.data.get("user_lang", {}).get(str(uid))
    except Exception:
        lang = None
    return lang if lang in LANGUAGES else DEFAULT_LANG


def has_lang(uid: int) -> bool:
    from storage import store
    return str(uid) in store.data.get("user_lang", {})


def set_lang(uid: int, lang: str) -> None:
    from storage import store
    if lang not in LANGUAGES:
        return
    store.data.setdefault("user_lang", {})[str(uid)] = lang
    store._mark_dirty()


def _uid_of(who: Any) -> int:
    """int | Message | CallbackQuery | InlineQuery -> id пользователя (в личке chat.id == user id)."""
    if isinstance(who, int):
        return who
    chat = getattr(who, "chat", None)
    if chat is None:
        msg = getattr(who, "message", None)
        chat = getattr(msg, "chat", None) if msg is not None else None
    if chat is not None and getattr(chat, "type", "private") == "private":
        return int(chat.id)
    frm = getattr(who, "from_user", None)
    return int(frm.id) if frm is not None else 0


def lang_of(who: Any) -> str:
    return who if isinstance(who, str) and who in LANGUAGES else get_lang(_uid_of(who))


def tr(who: Any, ru: str, **kw: Any) -> str:
    """Перевод строки `ru` на язык пользователя `who` (+ .format(**kw), если переданы параметры)."""
    _ensure_loaded()
    lang = lang_of(who)
    text = ru if lang == DEFAULT_LANG else TRANSLATIONS.get(lang, {}).get(ru, ru)
    if kw:
        try:
            return text.format(**kw)
        except Exception:
            try:
                return ru.format(**kw)
            except Exception:
                return text
    return text


# Переводы подгружаются лениво при первом вызове (i18n_texts импортирует keyboards/config,
# а те сами используют tr — так избегаем циклического импорта).
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    from i18n_texts import register_all
    register_all(_reg)
