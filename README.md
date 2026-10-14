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

## Что изменилось в этой версии

**Площадки.** Добавлены Rutube (`rutube.ru/video/<id>`, `/shorts/`, `/play/embed/`, приватные `video/private/<id>/?p=…`) и Reddit (`reddit.com/r/…/comments/…`, короткие `/s/…`, `redd.it`, `v.redd.it`); они есть в статистике и во всех текстах на 6 языках. Likee и Одноклассники из скачивания убраны: ссылки на них не распознаются, из текстов и справки они удалены. В статистике метки `likee`/`ok` оставлены, чтобы не терять старые счётчики.

**Запасные пути, когда yt-dlp не справился** (модуль `platform_fallbacks.py`, переключение в `youtube_provider.py`: `probe_youtube`, `download_youtube`, `download_audio_only`):

- **X (Twitter) 18+** — через `api.fxtwitter.com` → `api.vxtwitter.com` (прямой mp4 с video.twimg.com), без cookies; звук достаётся ffmpeg-ом. Хосты: `TWITTER_FX_API_HOSTS`.
- **Reddit** («Account authentication is required» на IP дата-центров) — раскрытие короткой ссылки → JSON поста → DASH-видео + аудио v.redd.it, склейка ffmpeg (без ffmpeg придёт видео без звука) → зеркала `vxreddit.com`/`rxddit.com`. Хосты: `REDDIT_JSON_HOSTS`, `REDDIT_MIRRORS`. Видео не на v.redd.it и галереи так не скачиваются; для закрытых/NSFW-сабреддитов нужны cookies `reddit.com`. Если Reddit режет IP целиком — `COBALT_API_URL` или `YTDLP_PROXY` с домашним IP.
- Когда не сработали оба пути, в лог уходит причина обоих: `yt-dlp … | fallback: …`.

## /history — только для админов

Команда есть в админ-справке (раздел «История скачиваний»). Обычным пользователям бот не отвечает, как и на остальные админ-команды.

- `/history` — своя история файлом `.txt` (новые записи сверху: дата по МСК, площадка, тип, ссылка, название).
- `/history 123456789` или `/history @username` — история конкретного человека.
- `/history all` — последние до 3000 скачиваний всех пользователей (с метками и id).
- В конец любой формы можно добавить `csv` — таблица `.csv` (UTF-8 с BOM, открывается в Excel).

Записи пишутся в `data.json`/БД (ключ `history`) из `store.inc_download` / `store.inc_audio`; хранятся последние `HISTORY_MAX_PER_USER` (по умолчанию 300) на человека. Скачивания до этого обновления в историю не попадают — в них не сохранялись ссылки. При сбое команда отвечает «Не удалось собрать историю» и пишет traceback в лог сервера (`/history failed …`).
