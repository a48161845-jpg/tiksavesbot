# syntax=docker/dockerfile:1
#
# ============================================================================
# Стадия 1: сборка telegram-bot-api (опционально, но включена по умолчанию).
#
# Зачем: без своего Local Bot API Server у обычного облачного Bot API лимит
# на отправку файла — 50 МБ, а YouTube/VK-видео в хорошем качестве часто
# больше. Собираем официальный сервер из исходников tdlib/telegram-bot-api.
#
# Это САМАЯ долгая часть сборки образа (может занять 10-20+ минут на первом
# билде). Но она кэшируется отдельным слоем: пока этот Dockerfile и версия
# telegram-bot-api не меняются, повторные деплои (когда меняется только код
# бота) не будут пересобирать эту стадию — платформа возьмёт её из кэша.
#
# Если сборка не проходит из-за лимита времени на твоей площадке — смотри
# комментарий "БЕЗ telegram-bot-api" в конце файла, как отключить эту стадию.
# ============================================================================
FROM debian:bookworm-slim AS botapi-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        gperf \
        libssl-dev \
        zlib1g-dev \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --depth=1 --recursive https://github.com/tdlib/telegram-bot-api.git

RUN mkdir -p telegram-bot-api/build && cd telegram-bot-api/build \
    && CXXFLAGS="-O2" CFLAGS="-O2" cmake -DCMAKE_BUILD_TYPE=Release .. \
    && cmake --build . --target install -j"$(nproc)"
# Бинарник после install лежит в /usr/local/bin/telegram-bot-api


# ============================================================================
# Стадия 2: сам бот
# ============================================================================
FROM python:3.12-slim AS bot

# ffmpeg — главное, ради чего вообще имеет смысл переезжать на Docker с
# Termux: тут он ставится одной командой и гарантированно работает, без
# шаманства с imageio-ffmpeg/pkg на устройстве. Именно из-за отсутствия
# ffmpeg качество видео выше ~720p не скачивалось раньше.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Собранный на стадии 1 telegram-bot-api — для файлов тяжелее 50 МБ.
COPY --from=botapi-builder /usr/local/bin/telegram-bot-api /usr/local/bin/telegram-bot-api

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOCAL_BOT_API_BIN=/usr/local/bin/telegram-bot-api \
    LOCAL_BOT_API_DIR=/data/telegram-bot-api

WORKDIR /app

# Сначала только requirements.txt — чтобы pip install кэшировался отдельным
# слоем и не переустанавливался при каждом изменении кода бота.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# /data — сюда стоит подключить persistent volume на твоей площадке (если
# она это поддерживает), чтобы data.json (fallback-хранилище) и файлы
# telegram-bot-api не терялись при каждом передеплое. Если задан
# DATABASE_URL (Postgres) — data.json вообще не используется, это только
# для Local Bot API Server.
RUN mkdir -p /data
VOLUME ["/data"]

CMD ["python", "bot.py"]

# ============================================================================
# БЕЗ telegram-bot-api (если сборка стадии 1 не укладывается в лимит времени
# твоей площадки, или большие файлы не нужны): удали весь блок
# "Стадия 1" выше и строку "COPY --from=botapi-builder ..." в стадии 2 —
# бот запустится и без него, просто с лимитом 50 МБ на файл (как в
# облачном Bot API), ffmpeg при этом всё равно будет на месте.
# ============================================================================
