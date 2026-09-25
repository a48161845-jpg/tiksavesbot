"""
Диагностика доступных качеств для конкретной ссылки — запускать прямо на
сервере бота (там есть интернет и настоящий yt-dlp), не в песочнице.

Использование:
    python diag_quality.py "https://youtu.be/xxxxxxxxxxx"

Покажет:
  - версию yt-dlp и путь к ffmpeg, которые реально использует бот;
  - было ли поймано предупреждение о потере форматов (nsig);
  - итоговый список качеств, который увидел бы пользователь в кнопках;
  - сырой список высот из всех форматов (до фильтрации) — на случай,
    если у видео и правда нет ничего кроме низких.
"""
import sys
import asyncio

import yt_dlp
from youtube_provider import probe_youtube, list_qualities, ffmpeg_available, _FFMPEG_PATH


async def main() -> None:
    if len(sys.argv) < 2:
        print("Использование: python diag_quality.py <ссылка>")
        return
    url = sys.argv[1]

    print("=== Окружение ===")
    print("yt-dlp версия:", yt_dlp.version.__version__)
    print("ffmpeg найден:", ffmpeg_available(), "->", _FFMPEG_PATH)
    print()

    print("=== Пробую видео ===")
    try:
        info = await probe_youtube(url)
    except Exception as e:
        print("ОШИБКА при получении информации о видео:", repr(e))
        return

    print("Название:", info.get("title"))
    print("Длительность (сек):", info.get("duration"))
    print("nsig-предупреждение поймано:", info.get("_limited_formats_warning"))
    if info.get("_limited_formats_detail"):
        print("Текст предупреждения:", info.get("_limited_formats_detail"))
    print()

    print("=== Сырые высоты из всех video-форматов (до фильтрации) ===")
    raw_heights = sorted(
        {f.get("height") for f in (info.get("formats") or []) if f.get("height") and f.get("vcodec") not in (None, "none")},
        reverse=True,
    )
    print(raw_heights or "(нет ни одного видео-формата с известной высотой!)")
    print()

    print("=== Итоговый список качеств (то, что увидит пользователь) ===")
    qualities = list_qualities(info)
    for q in qualities:
        print(f"  {q['label']}  (height={q['height']}, filesize={q['filesize']})")
    if not qualities:
        print("  (пусто)")


if __name__ == "__main__":
    asyncio.run(main())
