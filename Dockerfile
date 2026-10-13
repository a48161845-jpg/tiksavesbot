# syntax=docker/dockerfile:1
#
# ============================================================================
# Бот + ffmpeg + telegram-bot-api (одной цепочкой слоёв)
# ============================================================================
FROM python:3.12-slim AS bot

# ВАЖНО: раньше telegram-bot-api собирался в отдельной стадии и копировался через
# "COPY --from=botapi-builder". На некоторых хостингах (старый builder + чистка образов)
# промежуточный образ пропадал между стадиями и сборка падала с
# "invalid from flag value botapi-builder: No such image". Теперь всё собирается
# в одной цепочке слоёв — ссылаться на другую стадию не нужно.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOCAL_BOT_API_BIN=/usr/local/bin/telegram-bot-api \
    LOCAL_BOT_API_DIR=/data/telegram-bot-api

# ffmpeg — для качества выше ~720p, сжатия и сборки фото в видео.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Сборка telegram-bot-api (для файлов до 2 ГБ). Самая долгая часть (10-20+ мин на первом
# билде), но кэшируется слоем. Инструменты сборки удаляются в этом же слое; dev-библиотеки
# (libssl-dev, zlib1g-dev) и рантайм-библиотеки остаются, поэтому бинарник продолжает работать.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git gperf libssl-dev zlib1g-dev \
    && git clone --depth=1 --recursive https://github.com/tdlib/telegram-bot-api.git /src \
    && mkdir -p /src/build && cd /src/build \
    && CXXFLAGS="-O2" CFLAGS="-O2" cmake -DCMAKE_BUILD_TYPE=Release .. \
    && cmake --build . --target install -j2 \
    && cd / && rm -rf /src \
    && apt-get purge -y build-essential cmake git gperf \
    && rm -rf /var/lib/apt/lists/* \
    && test -x /usr/local/bin/telegram-bot-api

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
# БЕЗ telegram-bot-api (если сборка не укладывается в лимит времени площадки или
# большие файлы не нужны): удали блок "Сборка telegram-bot-api" выше — бот запустится
# и без него, с лимитом 50 МБ на файл, ffmpeg при этом останется.
# ============================================================================
