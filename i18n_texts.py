"""Словари переводов (ключ — русский оригинал). Подгружается лениво из i18n._ensure_loaded()."""


def register_all(_reg) -> None:
    from config import (
        CAPTION_VIDEO, CAPTION_PHOTO, CAPTION_AUDIO,
        MSG_SPAM, MSG_DL, MSG_PHOTO, PHOTO_WARNING_TEXT,
    )
    from keyboards import START_TEXT, HELP_TEXT, HELP_SECTIONS

    # ---------------- старт / помощь ----------------
    _reg(START_TEXT,
         "👋 <b>Hi! I'm TikSaves</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "I download videos, photo slideshows and music from TikTok, plus videos from YouTube (incl. Shorts), Instagram, VK, Pinterest, X, Rutube and Reddit.\n\n"
         "📎 <b>Just send a link</b> — I'll do the rest, no watermarks, no subscriptions.\n\n"
         "🧭 <b>Useful:</b>\n🧾 Help — /help\n📊 My stats — /me\n⚙️ Settings — /settings\n💛 Support the project — /donate\n🆘 Support — /support",
         "👋 <b>Привіт! Я TikSaves</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "Завантажую відео, фото-слайдшоу та музику з TikTok, а також відео з YouTube (зокрема Shorts), Instagram, VK, Pinterest, X, Rutube і Reddit.\n\n"
         "📎 <b>Просто надішли посилання</b> — решту зроблю сам, без водяних знаків і підписок.\n\n"
         "🧭 <b>Корисне:</b>\n🧾 Допомога — /help\n📊 Моя статистика — /me\n⚙️ Налаштування — /settings\n💛 Підтримати проєкт — /donate\n🆘 Підтримка — /support")

    _reg(HELP_TEXT,
         "🧾 <b>TikSaves help</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "📎 Just send a link to TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube or Reddit — the bot will offer the options.\n\n"
         "🧭 <b>Help buttons:</b>\n🎬 Download video — how to download videos\n🖼️ Download photos — how to download photos\n"
         "⚠️ Limits — about limits\n📳 Inline mode — how to download in inline mode",
         "🧾 <b>Допомога TikSaves</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "📎 Просто надішли посилання на TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube або Reddit — бот сам запропонує варіанти.\n\n"
         "🧭 <b>Кнопки допомоги:</b>\n🎬 Завантажити відео — як завантажувати відео\n🖼️ Завантажити фото — як завантажувати фото\n"
         "⚠️ Ліміти — про ліміти\n📳 Inline-режим — як завантажувати в inline-режимі")

    hs = HELP_SECTIONS
    _reg(hs["video"],
         "🎬 <b>How to download videos</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "1️⃣ Send a link to TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube or Reddit 📱\n\n"
         "2️⃣ For YouTube/Instagram/VK/Pinterest/X/Rutube/Reddit pick the video quality (or «Audio only») 🎚️\n\n"
         "3️⃣ Wait a few seconds while the video downloads ⏳\n\n"
         "4️⃣ Get your video in good quality without watermarks 🎉\n\n"
         "⛔ If an error occurs, try again; if it repeats, write to /support",
         "🎬 <b>Як завантажувати відео</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "1️⃣ Надішли посилання на TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube або Reddit 📱\n\n"
         "2️⃣ Для YouTube/Instagram/VK/Pinterest/X/Rutube/Reddit обери якість відео (або «Лише звук») 🎚️\n\n"
         "3️⃣ Зачекай кілька секунд, поки відео завантажується ⏳\n\n"
         "4️⃣ Отримай відео в гарній якості без водяних знаків 🎉\n\n"
         "⛔ У разі помилки повтори спробу, а якщо вона повториться — напиши в /support")
    _reg(hs["photo"],
         "🖼️ <b>How to download photos</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "1️⃣ Send a link to a TikTok slideshow 📱\n\n"
         "2️⃣ Choose to download as photos or as a video\n\n"
         "3️⃣ With «as photos» a menu opens: pick pages and optionally 🎵 Music / 📝 Description\n\n"
         "4️⃣ With «as video» you get a file with 🎵 Music / 📝 Description buttons\n\n"
         "🖼️ <b>Photo menu:</b>\n\n"
         "5️⃣ Numbers on top — tap a number to select that photo. You can select 1, 2, 3 or all 10\n\n"
         "6️⃣ «Select page» — selects all 10 photos on the page (use the page buttons to switch)\n\n"
         "7️⃣ «Download all» — downloads all photos plus music and description\n\n"
         "8️⃣ «🎵 Music» / «📝 Description» — toggle them (if you didn't choose «Download all»)\n\n"
         "9️⃣ «Clear» resets the selection, «Continue» downloads what is selected\n\n"
         "⛔ If an error occurs, try again; if it repeats, write to /support",
         "🖼️ <b>Як завантажувати фото</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "1️⃣ Надішли посилання на TikTok-слайдшоу 📱\n\n"
         "2️⃣ Обери: завантажити як фото чи як відео\n\n"
         "3️⃣ При виборі «як фото» відкриється меню: обери сторінки та за бажанням 🎵 Музику / 📝 Опис\n\n"
         "4️⃣ При виборі «як відео» прийде файл із кнопками 🎵 Музика / 📝 Опис\n\n"
         "🖼️ <b>Меню фото:</b>\n\n"
         "5️⃣ Цифри зверху — натисни цифру, щоб обрати конкретне фото. Можна обрати 1, 2, 3 або всі 10\n\n"
         "6️⃣ «Обрати сторінку» — обирає всі 10 фото на сторінці (є кнопки перемикання)\n\n"
         "7️⃣ «Завантажити все» — усі фото, а також музика й опис\n\n"
         "8️⃣ «🎵 Музика» / «📝 Опис» — вмикають їх (якщо не обрано «Завантажити все»)\n\n"
         "9️⃣ «Очистити» скидає вибір, «Продовжити» завантажує обране\n\n"
         "⛔ У разі помилки повтори спробу, а якщо вона повториться — напиши в /support")
    _reg(hs["limits"],
         "⚠️ <b>Limits</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "Limits are soft: you can send several links in a row. If there are too many requests the bot will ask you to wait a few seconds.\n"
         "Systematic flooding may lead to a temporary ban.\n\n"
         "📦 <b>File size:</b> videos heavier than Telegram's limit are compressed automatically so they arrive. Truly huge (multi-hour) videos can't be downloaded.",
         "⚠️ <b>Ліміти</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "Ліміти м'які: можна надсилати кілька посилань поспіль. Якщо запитів забагато — бот попросить зачекати кілька секунд.\n"
         "За систематичний флуд можливе тимчасове блокування.\n\n"
         "📦 <b>Розмір файлу:</b> відео, важчі за ліміт Telegram, бот автоматично стискає, щоб воно дійшло. Величезні (багатогодинні) відео завантажити не вийде.")
    _reg(hs["inline"],
         "📳 <b>Inline mode</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "Download videos not only in the bot 🎉\n\n"
         "1️⃣ In any chat type <code>@tiksavesbot</code>, wait for the result to appear, then paste a link to a TikTok video, YouTube, Instagram, VK, Pinterest, X, Rutube or Reddit\n\n"
         "2️⃣ Wait a moment while the video downloads\n\n"
         "3️⃣ Get your video in good quality without watermarks 🎉\n\n"
         "⛔ If an error occurs, try again; if it repeats, write to /support",
         "📳 <b>Inline-режим</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "Завантажуй відео не лише в боті 🎉\n\n"
         "1️⃣ У будь-якому чаті введи <code>@tiksavesbot</code>, зачекай, поки з'явиться результат, потім встав посилання на TikTok-відео, YouTube, Instagram, VK, Pinterest, X, Rutube або Reddit\n\n"
         "2️⃣ Зачекай, поки відео завантажиться\n\n"
         "3️⃣ Отримай відео в гарній якості без водяних знаків 🎉\n\n"
         "⛔ У разі помилки повтори спробу, а якщо вона повториться — напиши в /support")

    # ---------------- подписи ----------------
    _reg(CAPTION_VIDEO,
         "✨ <b>Done!</b> 🎬\nNo watermarks, just as it should be 😉\n\n📥 <i>Downloaded with</i> @tiksavesbot",
         "✨ <b>Готово!</b> 🎬\nБез водяних знаків, як і має бути 😉\n\n📥 <i>Завантажено в</i> @tiksavesbot")
    _reg(CAPTION_PHOTO,
         "✨ <b>Done!</b> 🖼️\nEnjoy — and have fun watching 😎\n\n📥 <i>Downloaded with</i> @tiksavesbot",
         "✨ <b>Готово!</b> 🖼️\nЗабирай — і приємного перегляду 😎\n\n📥 <i>Завантажено в</i> @tiksavesbot")
    _reg(CAPTION_AUDIO,
         "🎵 <b>Your audio is ready!</b>\nSave it and enjoy 🎧\n\n📥 <i>Downloaded with</i> @tiksavesbot",
         "🎵 <b>Твій звук готовий!</b>\nЗберігай і слухай 🎧\n\n📥 <i>Завантажено в</i> @tiksavesbot")

    # ---------------- лимиты ----------------
    _reg(MSG_SPAM, "🛡 <b>Too fast!</b>\nTake a breather for ~{n} sec. and try again.",
         "🛡 <b>Занадто швидко!</b>\nПереведи подих ~{n} сек. і спробуй знову.")
    _reg(MSG_DL, "⏳ <b>Download limit</b>\nWait ~{n} sec. — and we'll continue.",
         "⏳ <b>Ліміт завантажень</b>\nЗачекай ~{n} сек. — і продовжимо.")
    _reg(MSG_PHOTO, "📸 <b>Photo limit</b>\nWait ~{n} sec. — and we'll continue.",
         "📸 <b>Ліміт фото</b>\nЗачекай ~{n} сек. — і продовжимо.")
    _reg(PHOTO_WARNING_TEXT,
         "⚠️ <b>Before you download</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "Download only your own content or content you have the author's permission for.\nRespect other people's work 🙏",
         "⚠️ <b>Перш ніж завантажувати</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
         "Завантажуй лише власний контент або той, на який маєш дозвіл автора.\nПовažай чужу працю 🙏".replace("Повažай", "Поважай"))

    # ---------------- простые сообщения ----------------
    simple = [
        ("⏳ Скачиваю…", "⏳ Downloading…", "⏳ Завантажую…"),
        ("📤 Отправляю…", "📤 Sending…", "📤 Надсилаю…"),
        ("⏳ Основной способ сейчас недоступен, пробую запасной…", "⏳ The main method is unavailable, trying a backup…", "⏳ Основний спосіб недоступний, пробую запасний…"),
        ("📎 Пришли ссылку на TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube или Reddit.", "📎 Send a link to TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube or Reddit.", "📎 Надішли посилання на TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube або Reddit."),
        ("📎 <b>В посте несколько фото</b>\n\nКак скачать?", "📎 <b>This post has several photos</b>\n\nHow to download?", "📎 <b>У пості кілька фото</b>\n\nЯк завантажити?"),
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
        ("🎞️ <b>Выбери качество видео</b>\n\nЧем выше качество — тем дольше скачивание и больше файл.", "🎞️ <b>Choose video quality</b>\n\nThe higher the quality, the longer the download and the bigger the file.", "🎞️ <b>Обери якість відео</b>\n\nЧим вища якість — тим довше завантаження і більший файл."),
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
