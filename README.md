# TikSaves Bot

Telegram-бот для скачивания видео/фото/музыки из TikTok (aiogram 3.29+).

## Запуск

```bash
pip install -r requirements.txt
cp .env.example .env   # заполни BOT_TOKEN
python bot.py
```

## Структура

```
tiksaves_bot/
├── bot.py                 # точка входа (main, polling)
├── config.py               # переменные окружения, константы
├── helpers.py                # HTML/даты/URL утилиты, парсинг длительности бана
├── storage.py                  # класс Storage (data.json) — пользователи, баны, страйки, статистика
├── admin_log_file.py             # текстовый лог-файл (admin.log)
├── logging_channel.py              # буферизованные логи в Telegram-канал + автосейв
├── user_label.py                     # resolve_user_label (имя/юзернейм для логов)
├── limiters.py                         # анти-флуд, лимит скачиваний/фото
├── strikes.py                            # страйки и авто-баны
├── gates.py                                # проверка бана + анти-флуд перед хендлерами
├── providers.py                              # TikWMClient / ApifyProvider / ProviderSwitcher
├── globals_state.py                            # общий Dispatcher (dp) и текущий provider
├── send_helpers.py                               # отправка фото-альбомов/видео/музыки
├── picker_state.py                                 # состояние фото-пикера
├── keyboards.py                                      # инлайн-клавиатуры и тексты UI
├── donate.py                                           # логика донатов / Stars-инвойсов
├── broadcast.py                                          # ручная и плановая рассылка
├── stats.py                                                # тексты статистики/топов
└── handlers/
    ├── __init__.py            # регистрирует все хендлеры на dp
    ├── commands.py              # /start /help /support /donate /admin /stats /top
    ├── admin_commands.py          # /ban /unban /banlist /baninfo /info /broadcast ...
    ├── strikes_commands.py          # /strikes /strikeadd /strikedel
    ├── admin_callbacks.py             # кнопки админ-панели (ad:*)
    ├── donate_callbacks.py              # кнопки донатов/Stars (dl:*, donate:*, stars:*)
    ├── help_callbacks.py                  # кнопки раздела помощи (help:*)
    ├── picker_callbacks.py                  # кнопки фото-пикера (pk:*)
    ├── video_choice_callbacks.py               # задел на выбор перед видео (vd:*, сейчас не используется)
    └── main_handler.py                           # основной catch-all обработчик ссылок
```

## Заметки

- `video_choice_callbacks.py` / `picker_state.pending_video` сохранены как есть из
  оригинала, но сейчас не используются: `main_handler` отправляет видео сразу,
  без промежуточного экрана выбора. Это не баг, просто незавершённая ветка функционала.
- Данные хранятся в `data.json` рядом с `bot.py` (создаётся автоматически).
- Для резервного провайдера скачивания установи `ALT_PROVIDER=apify` и `APIFY_TOKEN`
  в `.env` — но `ApifyProvider.get_media` потребует доработки (маппинг полей актора).

## Что изменилось (обновление)

- **Лимиты смягчены**: 25 скачиваний/мин (было 6), 30 событий/15 с до кулдауна (было 8), кулдаун 15 с (был 60), фото 400/мин. Всё настраивается через `.env` (см. `.env.example`).
- **Новые форматы ссылок TikTok**: `tt.site/t/...`, `tiktok.com/t/...`, любые поддомены `*.tiktok.com`, `tiktokv.com`. Короткие ссылки раскрываются до полного URL перед скачиванием; при `Url parsing is failed` пробуются запасные формы URL.
- **Файлы > 50 МБ**: задай `API_ID` и `API_HASH` — Dockerfile поднимет Local Bot API (до 2 ГБ). Если сервер не поднялся или переменных нет — бот не отказывает, а **сжимает видео через ffmpeg** до 49 МБ.
- Pinterest: исправлена ошибка `Conflicting range`.
- TikTok-слайдшоу: исправлен HTTP 403 при скачивании фото (Referer + повтор с другим User-Agent).
- yt-dlp: поддержка cookies (`YTDLP_COOKIES_B64` / `YTDLP_COOKIES_FILE`) — лечит «Sign in to confirm you're not a bot» на YouTube и закрытые Instagram-посты.

## Стабильность качества YouTube
- Для YouTube cookies используются только как крайняя мера (с ними YouTube включает SABR-only и отдаёт 360p).
- После скачивания бот проверяет реальное разрешение файла; если оно хуже доступного — пробует другие наборы клиентов и оставляет лучший файл. При желании добирает у cobalt (`COBALT_API_URL`).
- yt-dlp сам обновляется (`YTDLP_AUTOUPDATE=1`) и перезапускает бота при смене версии.
- При низком качестве в лог-канал приходит `#ytdlpold` с диагностикой.

## Что изменилось (X 18+, Likee, Одноклассники, Rutube)

- **Новая площадка — Rutube** (`rutube.ru/video/<id>`, `/shorts/`, `/play/embed/`, приватные `video/private/<id>/?p=…`). Shorts/embed приводятся к обычной ссылке на видео. Добавлена в статистику и во все тексты (6 языков).
- **Одноклассники**: распознавание расширено — `ok.ru`, `m.ok.ru`, `odnoklassniki.ru`, `video/ID`, `videoembed/ID`, `live/ID`, `movie/ID`, `profile/…/video/ID`, `group/…/video/ID`, старые `dk?st.cmd=movieLayer&st.mvId=ID`, `web-api/video/moviePlayer/ID`. Перед yt-dlp любая такая ссылка приводится к `https://ok.ru/video/ID`.
- **Likee**: короткая ссылка `l.likee.video/v/XXXX` раньше «раскрывалась» в корень сайта (`https://likee.video/`) → `Unsupported URL`. Теперь редиректы идут вручную (мобильный UA), из ответа/страницы берётся реальный `likee.video/v/<id>` или `likee.video/@user/video/<id>`, а `https://likee.video/v/<id из короткой ссылки>` пробуется как запасной вариант. Корень сайта в yt-dlp больше не попадает. Если yt-dlp всё равно не смог — читается `window.data.video_url` со страницы (best effort).
- **X (Twitter) 18+**: если yt-dlp не отдал видеоформаты или упёрся в «войдите», берётся запасной путь через `api.fxtwitter.com` → `api.vxtwitter.com` (прямая ссылка на mp4 с video.twimg.com). Работает без cookies; звук достаётся из скачанного видео через ffmpeg. Хосты настраиваются через `TWITTER_FX_API_HOSTS`.
- Новый модуль `platform_fallbacks.py`; логика переключения — в `youtube_provider.py` (`probe_youtube`, `download_youtube`, `download_audio_only`). В лог-канал при двойной неудаче уходит причина обоих путей: `yt-dlp … | fallback: …`.
