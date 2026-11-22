"""Словари переводов (ключ — русский оригинал). Подгружается лениво из i18n._ensure_loaded()."""


def register_all(_reg) -> None:
    from core.config import (
        CAPTION_VIDEO, CAPTION_PHOTO, CAPTION_AUDIO,
        MSG_SPAM, MSG_DL, MSG_PHOTO, PHOTO_WARNING_TEXT,
    )
    from ui.keyboards import START_TEXT, HELP_TEXT, HELP_SECTIONS

    # ---------------- старт / помощь ----------------


    hs = HELP_SECTIONS

    # ---------------- подписи ----------------

    # ---------------- лимиты ----------------
    _reg(MSG_DL, "⏳ <b>Download limit</b>\nWait ~{n} sec. — and we'll continue.",
         "⏳ <b>Ліміт завантажень</b>\nЗачекай ~{n} сек. — і продовжимо.")
    _reg(MSG_PHOTO, "📸 <b>Photo limit</b>\nWait ~{n} sec. — and we'll continue.",
         "📸 <b>Ліміт фото</b>\nЗачекай ~{n} сек. — і продовжимо.")

    # ---------------- простые сообщения ----------------
    simple = [
        ("⏳ Скачиваю…", "⏳ Downloading…", "⏳ Завантажую…"),
        ("📤 Отправляю…", "📤 Sending…", "📤 Надсилаю…"),
        ("⏳ Основной способ сейчас недоступен, пробую запасной…", "⏳ The main method is unavailable, trying a backup…", "⏳ Основний спосіб недоступний, пробую запасний…"),
        ("📎 Пришли ссылку на TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube или Reddit.", "📎 Send a link to TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube or Reddit.", "📎 Надішли посилання на TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube або Reddit."),
        ("❌ Проблема с сетью/сервисом. Попробуй позже.", "❌ Network/service problem. Try again later.", "❌ Проблема з мережею/сервісом. Спробуй пізніше."),
        ("❌ Файл больше лимита ({mb} МБ). Telegram не даёт боту отправлять файлы тяжелее.", "❌ The file is over the limit ({mb} MB). Telegram doesn't let bots send heavier files.", "❌ Файл більший за ліміт ({mb} МБ). Telegram не дозволяє ботам надсилати важчі файли."),
        ("❌ Не удалось скачать. Попробуй позже.", "❌ Couldn't download. Try again later.", "❌ Не вдалося завантажити. Спробуй пізніше."),
        ("❌ Видео приватное или недоступно.", "❌ The video is private or unavailable.", "❌ Відео приватне або недоступне."),
        ("❌ Видео удалено или не найдено.", "❌ The video was deleted or not found.", "❌ Відео видалено або не знайдено."),
        ("❌ Не удалось разобрать ссылку. Проверь ссылку и попробуй ещё раз.", "❌ Couldn't parse the link. Check it and try again.", "❌ Не вдалося розібрати посилання. Перевір його й спробуй ще раз."),
        ("⏳ Смотрю видео на YouTube…", "⏳ Checking the YouTube video…", "⏳ Дивлюся відео на YouTube…"),
        ("⏳ Смотрю {p}…", "⏳ Checking {p}…", "⏳ Дивлюся {p}…"),
        ("❌ Не удалось получить это видео. Проверь ссылку — может, оно приватное/удалено.", "❌ Couldn't get this video. Check the link — it may be private/deleted.", "❌ Не вдалося отримати це відео. Перевір посилання — можливо, воно приватне/видалене."),
        ("❌ Не удалось получить видео с {p}.\nВозможно, пост закрытый/приватный или требует входа в аккаунт — такое, увы, не скачать.", "❌ Couldn't get the video from {p}.\nThe post may be closed/private or require login — those can't be downloaded, sorry.", "❌ Не вдалося отримати відео з {p}.\nМожливо, пост закритий/приватний або потребує входу в акаунт — таке, на жаль, не завантажити."),
        ("❌ Видео слишком длинное ({m} мин). Лимит: {l} мин.", "❌ The video is too long ({m} min). Limit: {l} min.", "❌ Відео занадто довге ({m} хв). Ліміт: {l} хв."),
        ("\n\n⚠️ На сервере не найден ffmpeg — реально скачается максимум ~720p, даже если выбрать качество выше.", "\n\n⚠️ ffmpeg wasn't found on the server — at most ~720p will actually download, even if you pick higher.", "\n\n⚠️ На сервері не знайдено ffmpeg — реально завантажиться максимум ~720p, навіть якщо обрати вище."),
        ("⌛ Время выбора качества истекло. Пришли ссылку ещё раз.", "⌛ Quality selection expired. Send the link again.", "⌛ Час вибору якості минув. Надішли посилання ще раз."),
        ("Что-то пошло не так.", "Something went wrong.", "Щось пішло не так."),
        ("Это не твой запрос.", "This isn't your request.", "Це не твій запит."),
        ("❌ Скачивание отменено.", "❌ Download cancelled.", "❌ Завантаження скасовано."),
        ("⬇️ Скачиваю звук…", "⬇️ Downloading audio…", "⬇️ Завантажую звук…"),
        ("❌ Не получилось скачать звук с {p}.", "❌ Couldn't download audio from {p}.", "❌ Не вдалося завантажити звук з {p}."),
        ("❌ Скачанный файл пустой. Попробуй ещё раз.", "❌ The downloaded file is empty. Try again.", "❌ Завантажений файл порожній. Спробуй ще раз."),
        ("❌ Не удалось отправить звук.", "❌ Couldn't send the audio.", "❌ Не вдалося надіслати звук."),
        ("лучшем доступном", "the best available", "найкращій доступній"),
        ("⬇️ Скачиваю в {q} качестве…", "⬇️ Downloading in {q} quality…", "⬇️ Завантажую в {q} якості…"),
        ("❌ Не получилось скачать в этом качестве с {p}. Попробуй другое качество или другую ссылку.", "❌ Couldn't download in this quality from {p}. Try another quality or link.", "❌ Не вдалося завантажити в цій якості з {p}. Спробуй іншу якість або посилання."),
        ("🗜 Видео тяжёлое — сжимаю, чтобы влезло в Telegram…", "🗜 The video is heavy — compressing to fit Telegram…", "🗜 Відео важке — стискаю, щоб влізло в Telegram…"),
        ("❌ Файл в этом качестве больше лимита ({mb} МБ), а сжать его не получилось. Попробуй качество пониже.", "❌ The file in this quality is over the limit ({mb} MB) and couldn't be compressed. Try a lower quality.", "❌ Файл у цій якості більший за ліміт ({mb} МБ), а стиснути не вдалося. Спробуй нижчу якість."),
        ("❌ Telegram отклонил файл — скорее всего, он слишком большой для отправки ботом (лимит: {mb} МБ на файл).", "❌ Telegram rejected the file — most likely it's too big for the bot to send (limit: {mb} MB per file).", "❌ Telegram відхилив файл — найімовірніше, він завеликий для надсилання ботом (ліміт: {mb} МБ на файл)."),
        ("🎬 Собираю видео из фото, подожди немного…", "🎬 Building a video from the photos, wait a bit…", "🎬 Збираю відео з фото, зачекай трохи…"),
        ("❌ Не получилось собрать видео — попробуй ещё раз.", "❌ Couldn't build the video — try again.", "❌ Не вдалося зібрати відео — спробуй ще раз."),
        ("❌ Не получилось собрать видео из фото. Попробуй ещё раз позже.", "❌ Couldn't build a video from the photos. Try again later.", "❌ Не вдалося зібрати відео з фото. Спробуй ще раз пізніше."),
        ("⏱️ Выбор устарел. Скинь ссылку ещё раз.", "⏱️ The selection expired. Send the link again.", "⏱️ Вибір застарів. Надішли посилання ще раз."),
        ("Это не твой выбор фото.", "This isn't your photo selection.", "Це не твій вибір фото."),
        ("🖼️ Выбери фото по номерам или выдели страницу 👇", "🖼️ Pick photos by number or select a page 👇", "🖼️ Обери фото за номерами або виділи сторінку 👇"),
        ("Собираю видео…", "Building the video…", "Збираю відео…"),
        ("Ок.", "OK.", "Ок."),
        ("🧹 Очищено", "🧹 Cleared", "🧹 Очищено"),
        ("✅ Страница выбрана!", "✅ Page selected!", "✅ Сторінку обрано!"),
        ("🎵 Музыка добавлена", "🎵 Music added", "🎵 Музику додано"),
        ("🎵 Музыка убрана", "🎵 Music removed", "🎵 Музику прибрано"),
        ("📝 Описание добавлено", "📝 Description added", "📝 Опис додано"),
        ("📝 Описание убрано", "📝 Description removed", "📝 Опис прибрано"),
        ("Отправляю всё…", "Sending everything…", "Надсилаю все…"),
        ("Отправляю…", "Sending…", "Надсилаю…"),
        ("Выбери хотя бы одно фото (или галочку музыки/описания).", "Pick at least one photo (or the music/description checkbox).", "Обери хоча б одне фото (або галочку музики/опису)."),
        ("Отправляю музыку…", "Sending music…", "Надсилаю музику…"),
        ("Отправляю видео…", "Sending video…", "Надсилаю відео…"),
        ("⏳ <b>Скачиваю… понадобится немного больше времени...</b>", "⏳ <b>Downloading… this will take a bit longer...</b>", "⏳ <b>Завантажую… знадобиться трохи більше часу...</b>"),
        ("❌ Не удалось отправить описание. Попробуй ещё раз.", "❌ Couldn't send the description. Try again.", "❌ Не вдалося надіслати опис. Спробуй ще раз."),
        ("❌ Не получилось скачать звук с этого видео.", "❌ Couldn't download the audio from this video.", "❌ Не вдалося завантажити звук з цього відео."),
        ("Вы в бане.", "You are banned.", "Ти в бані."),
        ("Бан за флуд.", "Banned for flooding.", "Бан за флуд."),
        ("🛠 <b>Технические работы</b>", "🛠 <b>Maintenance</b>", "🛠 <b>Технічні роботи</b>"),
        # кнопки
        ("🎵 Музыка", "🎵 Music", "🎵 Музика"),
        ("📝 Описание", "📝 Description", "📝 Опис"),
        ("🖼️ Как фото", "🖼️ As photos", "🖼️ Як фото"),
        ("🎬 Как видео", "🎬 As video", "🎬 Як відео"),
        ("✅ Выбрать страницу", "✅ Select page", "✅ Обрати сторінку"),
        ("🔽 Скачать всё", "🔽 Download all", "🔽 Завантажити все"),
        ("🧹 Очистить", "🧹 Clear", "🧹 Очистити"),
        ("➡️ Продолжить ({n})", "➡️ Continue ({n})", "➡️ Продовжити ({n})"),
        ("✨ Лучшее качество", "✨ Best quality", "✨ Найкраща якість"),
        ("🎵 Только звук (MP3)", "🎵 Audio only (MP3)", "🎵 Лише звук (MP3)"),
        ("❌ Отмена", "❌ Cancel", "❌ Скасувати"),
        ("🎬 Скачать видео", "🎬 Download video", "🎬 Завантажити відео"),
        ("🖼️ Скачать фото", "🖼️ Download photos", "🖼️ Завантажити фото"),
        ("⚠️ Лимиты", "⚠️ Limits", "⚠️ Ліміти"),
        ("📳 Inline-режим", "📳 Inline mode", "📳 Inline-режим"),
        ("❌ Закрыть", "❌ Close", "❌ Закрити"),
        ("⬅️ Назад", "⬅️ Back", "⬅️ Назад"),
    ]
    for ru, en, uk in simple:
        _reg(ru, en, uk)
