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

## /history — история скачиваний файлом

- `/history` — присылает `.txt` со скачиваниями человека (новые сверху: дата по МСК, площадка, тип, ссылка, название); `/history csv` — то же таблицей `.csv` (UTF-8 с BOM, открывается в Excel).
- Записи пишутся в `data.json`/БД (ключ `history`) из `store.inc_download` / `store.inc_audio`; хранятся последние `HISTORY_MAX_PER_USER` (по умолчанию 300) на человека. Скачивания до этого обновления в историю не попадают — в них не сохранялись ссылки.
- Команда `/history` показывает только историю самого запросившего.

## Reddit

- Reddit добавлен как площадка (`reddit.com/r/…/comments/…`, короткие `reddit.com/r/…/s/…`, `redd.it/…`, `v.redd.it/…`), есть в статистике и во всех текстах на 6 языках.
- Если yt-dlp отвечает `Account authentication is required` (Reddit режет IP дата-центров), включается обход: короткая ссылка раскрывается → читается JSON поста → качаются DASH-видео и аудио с v.redd.it и склеиваются ffmpeg (без ffmpeg придёт видео без звука) → если JSON закрыт, берётся OG-страница зеркал vxreddit.com / rxddit.com. Хосты настраиваются через `REDDIT_JSON_HOSTS` и `REDDIT_MIRRORS`.
- Видео, которого нет на v.redd.it (ссылка на YouTube/Redgifs внутри поста) и галереи этим путём не скачиваются. Для закрытых/NSFW-сабреддитов нужны cookies `reddit.com` в `YTDLP_COOKIES_*`.

## OK клипы и Likee (обновление)

- Одноклассники: ссылки-клипы `ok.ru/clip?owner_id=…&clip_id=…` (и `ok.ru/clip/ID`) теперь распознаются и приводятся к `https://ok.ru/video/<clip_id>`. Если yt-dlp не справился — запасной путь через тот же запрос метаданных, что делает плеер OK (`https://ok.ru/dk`, `cmd=videoPlayerMetadata`): берётся лучшее качество до 1080p.
- Likee: yt-dlp-экстрактор сейчас падает с `Unable to extract video info` (Likee поменял страницу). Запасной путь теперь: API сайта по числовому `postId` (из `/@user/video/<id>` или `?postId=`), затем разбор HTML (`window.data`, JSON-блоки, `og:video`, любой `.mp4`). Для коротких `l.likee.video/v/…` числового id нет — там работает только разбор страницы.
- Все эндпоинты неофициальные: при смене формата в лог придёт причина каждого шага (`api[…]: нет данных; page: …`).

## /history для админов и исправление Likee

- Админы (`ADMINS` + `admins_extra`): `/history 123456789` или `/history @username` — история конкретного человека; `/history all` — последние до 3000 скачиваний всех пользователей (с метками и id); к любому варианту можно добавить `csv`. Обычному пользователю лишние аргументы игнорируются — он всегда получает только свою историю. При сбое команда отвечает «Не удалось собрать историю» и пишет traceback в лог сервера (`/history failed …`).
- Likee: раньше при раскрытии короткой ссылки из тела страницы подбиралась первая попавшаяся ссылка likee.video (например промо-видео `@likee`) — бот «додумывал» ссылку. Теперь кандидаты берутся только из настоящих редиректов (заголовок `Location`) и из кода самой короткой ссылки (`likee.video/v/<код>`); редирект на `@likee/video/…` игнорируется; страница принимается, только если в ней встречается id этого видео. Если уверенности нет — честная ошибка с диагностикой (`page …: len=…, id_in_page=…; redirects: …`), а не чужое видео.
