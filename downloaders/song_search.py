"""
Песня из TikTok-поста: название, исполнитель, поиск в музыкальных сервисах.

TikTok отдаёт вместе с постом данные о звуке: название, автора и признак «оригинальный звук» (когда автор записал
звук сам — в стримингах его обычно нет). Из них строим карточку песни и ссылки на поиск.
Чистые функции без сети — проверяются tests/test_song_search.py.
"""
import html
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, quote_plus

# Так TikTok называет звуки, записанные автором видео (на разных языках интерфейса)
_ORIGINAL_MARKERS = (
    "original sound", "оригинальный звук", "оригінальний звук", "оригинальная звуковая дорожка",
    "son original", "sonido original", "som original", "suono originale", "originalton", "original audio",
    "orijinal ses", "original ljud", "geluid origineel", "dźwięk oryginalny", "originalni zvuk",
    "オリジナル楽曲", "原声", "原創音訊", "원본 사운드", "ต้นฉบับ",
)
_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u2060\ufeff]")


def clean(text: Any) -> str:
    """Убирает невидимые символы и лишние пробелы."""
    return re.sub(r"\s+", " ", _ZERO_WIDTH.sub("", str(text or ""))).strip()


def is_original_sound(title: str, original: Optional[bool] = None) -> bool:
    """«Оригинальный звук» автора видео: по флагу TikTok или по характерному названию."""
    if original:
        return True
    low = clean(title).lower()
    return any(low.startswith(m) for m in _ORIGINAL_MARKERS)


def make_song(title: Any, author: Any, original: Optional[bool] = None, cover: Any = None) -> Optional[Dict[str, Any]]:
    """Словарь песни или None, если о звуке ничего не известно."""
    t, a = clean(title), clean(author)
    if not t and not a:
        return None
    return {
        "title": t,
        "author": a,
        "original": is_original_sound(t, original),
        "cover": cover if isinstance(cover, str) and cover.startswith("http") else None,
    }


def song_from_tikwm(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Данные ответа tikwm (поле music_info) -> песня."""
    mi = data.get("music_info") or data.get("musicInfo") or {}
    if not isinstance(mi, dict):
        return None
    return make_song(mi.get("title"), mi.get("author"), mi.get("original"), mi.get("cover"))


def song_from_page(music: Any) -> Optional[Dict[str, Any]]:
    """Блок music из JSON страницы TikTok (itemStruct.music) -> песня."""
    if not isinstance(music, dict):
        return None
    cover = music.get("coverLarge") or music.get("coverMedium") or music.get("coverThumb")
    return make_song(music.get("title"), music.get("authorName") or music.get("author"), music.get("original"), cover)


def search_query(song: Dict[str, Any]) -> str:
    """Строка поиска: «название исполнитель». Для «оригинального звука» — только автор (названия там служебные)."""
    if song.get("original"):
        return song.get("author", "")
    return clean(f"{song.get('title', '')} {song.get('author', '')}")


def search_links(song: Dict[str, Any]) -> List[Tuple[str, str]]:
    """[(подпись кнопки, URL)] — поиск этой песни в музыкальных сервисах."""
    q = search_query(song)
    if not q:
        return []
    if song.get("original"):
        # у оригинального звука стриминга обычно нет — поиск на YouTube по автору, вдруг выложен
        return [("▶️ YouTube", f"https://www.youtube.com/results?search_query={quote_plus(q)}")]
    return [
        ("🎵 YouTube Music", f"https://music.youtube.com/search?q={quote_plus(q)}"),
        ("🟢 Spotify", f"https://open.spotify.com/search/{quote(q)}"),
        ("🍎 Apple Music", f"https://music.apple.com/search?term={quote_plus(q)}"),
        ("🟡 Яндекс Музыка", f"https://music.yandex.ru/search?text={quote_plus(q)}"),
    ]


def song_caption(song: Optional[Dict[str, Any]]) -> str:
    """Строка для подписи под видео/фото: «🎵 Название — Автор» (HTML-безопасно) или пустая строка."""
    if not song:
        return ""
    title, author = html.escape(song.get("title", "")), html.escape(song.get("author", ""))
    if title and author and title.lower() != author.lower():
        body = f"{title} — {author}"
    else:
        body = title or author
    return f"\n🎵 <i>{body}</i>" if body else ""


def audio_tags(song: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Название и исполнитель для тегов аудиофайла в Telegram (kwargs для answer_audio)."""
    if not song:
        return {}
    tags: Dict[str, str] = {}
    if song.get("title"):
        tags["title"] = song["title"][:64]
    if song.get("author"):
        tags["performer"] = song["author"][:64]
    return tags
