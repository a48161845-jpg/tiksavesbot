"""Дополнительные переводы (ru, en, uk, kk, uz, ky) — экраны доната, поддержки, статистики, inline и т.п."""


def register_extra(_reg) -> None:
    from keyboards import (
        DONATE_TEXT, STARS_MENU_TEXT, SUPPORT_TEXT, SUPPORT_SENT_TEXT, SHARE_TEXT,
    )
    from broadcast import REMINDER_MSG, DONATE_REMINDER_MSG

    # ---------------- донат / поддержка ----------------
    _reg(DONATE_TEXT,
         "💛 <b>Support TikSaves</b>\n━━━━━━━━━━━━━━━━━━━━\n\nThanks for using the bot! Donations keep it fast and stable:\n\n☁️ hosting and traffic 24/7\n🔌 API and server support\n🚀 new features and improvements\n\nChoose a convenient way 👇",
         "💛 <b>Підтримати TikSaves</b>\n━━━━━━━━━━━━━━━━━━━━\n\nДякуємо, що користуєшся ботом! Донат допомагає тримати його швидким і стабільним:\n\n☁️ хостинг і трафік 24/7\n🔌 підтримка API та серверів\n🚀 нові функції та покращення\n\nОбери зручний спосіб 👇",
         "💛 <b>TikSaves-ті қолдау</b>\n━━━━━━━━━━━━━━━━━━━━\n\nБотты пайдаланғаныңыз үшін рахмет! Донат оны жылдам әрі тұрақты ұстауға көмектеседі:\n\n☁️ хостинг және трафик 24/7\n🔌 API мен серверлерді қолдау\n🚀 жаңа функциялар мен жақсартулар\n\nҚолайлы тәсілді таңдаңыз 👇",
         "💛 <b>TikSaves’ni qoʻllab-quvvatlash</b>\n━━━━━━━━━━━━━━━━━━━━\n\nBotdan foydalanayotganingiz uchun rahmat! Xayriya uni tez va barqaror ushlab turishga yordam beradi:\n\n☁️ hosting va trafik 24/7\n🔌 API va serverlarni qoʻllab-quvvatlash\n🚀 yangi imkoniyatlar va yaxshilanishlar\n\nQulay usulni tanlang 👇",
         "💛 <b>TikSaves’ти колдоо</b>\n━━━━━━━━━━━━━━━━━━━━\n\nБотту колдонгонуңуз үчүн рахмат! Донат аны ылдам жана туруктуу кармоого жардам берет:\n\n☁️ хостинг жана трафик 24/7\n🔌 API жана серверлерди колдоо\n🚀 жаңы функциялар жана жакшыртуулар\n\nЫңгайлуу ыкманы тандаңыз 👇")
    _reg(STARS_MENU_TEXT,
         "⭐ <b>Telegram Stars</b>\n━━━━━━━━━━━━━━━━━━━━\n\nThe fastest way to support the project right in Telegram.\n\nChoose an amount ({a}–{b} ⭐) or enter your own 👇",
         "⭐ <b>Telegram Stars</b>\n━━━━━━━━━━━━━━━━━━━━\n\nНайшвидший спосіб підтримати проєкт прямо в Telegram.\n\nОбери суму ({a}–{b} ⭐) або введи свою 👇",
         "⭐ <b>Telegram Stars</b>\n━━━━━━━━━━━━━━━━━━━━\n\nЖобаны тікелей Telegram-да қолдаудың ең жылдам тәсілі.\n\nСоманы таңдаңыз ({a}–{b} ⭐) немесе өзіңізді енгізіңіз 👇",
         "⭐ <b>Telegram Stars</b>\n━━━━━━━━━━━━━━━━━━━━\n\nLoyihani toʻgʻridan-toʻgʻri Telegram’da qoʻllab-quvvatlashning eng tez usuli.\n\nMiqdorni tanlang ({a}–{b} ⭐) yoki oʻzingiznikini kiriting 👇",
         "⭐ <b>Telegram Stars</b>\n━━━━━━━━━━━━━━━━━━━━\n\nДолбоорду түз эле Telegram’да колдоонун эң ылдам жолу.\n\nСуммаңызды тандаңыз ({a}–{b} ⭐) же өзүңүздүкүн киргизиңиз 👇")
    _reg(SUPPORT_TEXT,
         "🆘 <b>Support</b>\n━━━━━━━━━━━━━━━━━━━━\n\nDescribe your question or problem in one message — it goes straight to the admin.\n\nAttach a link to the video and say what went wrong — we'll sort it out faster 🙌",
         "🆘 <b>Підтримка</b>\n━━━━━━━━━━━━━━━━━━━━\n\nОпиши своє питання або проблему одним повідомленням — воно піде напряму адміністратору.\n\nДодай посилання на відео і опиши, що пішло не так — так розберемося швидше 🙌",
         "🆘 <b>Қолдау</b>\n━━━━━━━━━━━━━━━━━━━━\n\nСұрағыңызды немесе мәселеңізді бір хабарламамен сипаттаңыз — ол тікелей әкімшіге жетеді.\n\nБейнеге сілтеме қосып, не дұрыс болмағанын жазыңыз — тезірек шешеміз 🙌",
         "🆘 <b>Yordam</b>\n━━━━━━━━━━━━━━━━━━━━\n\nSavolingiz yoki muammoingizni bitta xabarda yozing — u toʻgʻridan-toʻgʻri administratorga boradi.\n\nVideo havolasini qoʻshing va nima notoʻgʻri ketganini yozing — tezroq hal qilamiz 🙌",
         "🆘 <b>Колдоо</b>\n━━━━━━━━━━━━━━━━━━━━\n\nСурооңузду же көйгөйүңүздү бир билдирүү менен сүрөттөңүз — ал түз администраторго жетет.\n\nВидеонун шилтемесин тиркеп, эмне туура эмес болгонун жазыңыз — тезирээк чечебиз 🙌")
    _reg(SUPPORT_SENT_TEXT,
         "✅ <b>Message sent!</b>\n\nThe administrator will reply right here in this chat soon.",
         "✅ <b>Повідомлення надіслано!</b>\n\nАдміністратор незабаром відповість тобі прямо тут, у цьому чаті.",
         "✅ <b>Хабарлама жіберілді!</b>\n\nӘкімші жақында осы чатта жауап береді.",
         "✅ <b>Xabar yuborildi!</b>\n\nAdministrator tez orada shu chatda javob beradi.",
         "✅ <b>Билдирүү жөнөтүлдү!</b>\n\nАдминистратор жакында ушул чатта жооп берет.")
    _reg(SHARE_TEXT,
         "🔥 Found a top bot for downloading videos and photos from TikTok — no watermarks, no subscriptions. Check it out ☝️",
         "🔥 Знайшов топового бота для завантаження відео та фото з TikTok — без водяних знаків і підписок. Заходь ☝️",
         "🔥 TikTok-тан бейне мен фото жүктейтін тамаша бот таптым — су белгісіз, жазылымсыз. Кіріп көріңіз ☝️",
         "🔥 TikTok’dan video va rasm yuklab oladigan zoʻr bot topdim — suv belgisiz, obunasiz. Kiring ☝️",
         "🔥 TikTok’тон видео жана сүрөт жүктөөчү сонун бот таптым — суу белгисиз, жазылуусуз. Кирип көрүңүз ☝️")
    _reg(REMINDER_MSG,
         "📌 **Don't forget** \n\nIf something doesn't work or you have a question — the **/support** command shows where to write.\n\n*We're always in touch* 🙌",
         "📌 **Не забувай** \n\nЯкщо щось не працює або є питання — команда **/support** підкаже, куди писати.\n\n*Ми завжди на зв'язку* 🙌",
         "📌 **Ұмытпаңыз** \n\nЕгер бірдеңе жұмыс істемесе немесе сұрағыңыз болса — **/support** командасы қайда жазу керегін көрсетеді.\n\n*Біз әрдайым байланыстамыз* 🙌",
         "📌 **Unutmang** \n\nAgar biror narsa ishlamasa yoki savolingiz boʻlsa — **/support** buyrugʻi qayerga yozishni koʻrsatadi.\n\n*Biz doim aloqadamiz* 🙌",
         "📌 **Унутпаңыз** \n\nЭгер бир нерсе иштебесе же суроо болсо — **/support** буйругу кайда жазууну көрсөтөт.\n\n*Биз дайыма байланыштабыз* 🙌")
    _reg(DONATE_REMINDER_MSG,
         "💛 **Like the bot?**\n\nIf TikSaves helps you — support the project via **/donate**: Telegram Stars ⭐️, crypto 💲, Donation Alerts\n\nEvery bit goes to hosting and development — thank you! 🙏",
         "💛 **Подобається бот?**\n\nЯкщо TikSaves допомагає — підтримай проєкт через **/donate**: Telegram Stars ⭐️, крипта 💲, Donation Alerts\n\nКожна допомога йде на хостинг і розвиток бота — дякуємо! 🙏",
         "💛 **Бот ұнай ма?**\n\nЕгер TikSaves көмектессе — жобаны **/donate** арқылы қолдаңыз: Telegram Stars ⭐️, крипто 💲, Donation Alerts\n\nӘрбір көмек хостинг пен ботты дамытуға кетеді — рахмет! 🙏",
         "💛 **Bot yoqdimi?**\n\nAgar TikSaves yordam bersa — loyihani **/donate** orqali qoʻllab-quvvatlang: Telegram Stars ⭐️, kripto 💲, Donation Alerts\n\nHar bir yordam hosting va botni rivojlantirishga ketadi — rahmat! 🙏",
         "💛 **Бот жактыбы?**\n\nЭгер TikSaves жардам берсе — долбоорду **/donate** аркылуу колдоңуз: Telegram Stars ⭐️, крипто 💲, Donation Alerts\n\nЫкма жардам хостингге жана ботту өнүктүрүүгө кетет — рахмат! 🙏")

    rows = [
        # ban
        ("🚫 <b>Вы заблокированы.</b>\n\n👤 User/id: <b>{u}</b>\n⏳ Бан до: <b>{until} МСК</b>\n📌 Причина: <b>{reason}</b>\n\n🆘 Поддержка: {support}",
         "🚫 <b>You are banned.</b>\n\n👤 User/id: <b>{u}</b>\n⏳ Ban until: <b>{until} MSK</b>\n📌 Reason: <b>{reason}</b>\n\n🆘 Support: {support}",
         "🚫 <b>Тебе заблоковано.</b>\n\n👤 User/id: <b>{u}</b>\n⏳ Бан до: <b>{until} МСК</b>\n📌 Причина: <b>{reason}</b>\n\n🆘 Підтримка: {support}",
         "🚫 <b>Сіз бұғатталдыңыз.</b>\n\n👤 User/id: <b>{u}</b>\n⏳ Бан мерзімі: <b>{until} МСК</b>\n📌 Себебі: <b>{reason}</b>\n\n🆘 Қолдау: {support}",
         "🚫 <b>Siz bloklandingiz.</b>\n\n👤 User/id: <b>{u}</b>\n⏳ Ban muddati: <b>{until} MSK</b>\n📌 Sababi: <b>{reason}</b>\n\n🆘 Yordam: {support}",
         "🚫 <b>Сиз бөгөттөлдүңүз.</b>\n\n👤 User/id: <b>{u}</b>\n⏳ Тыюу мөөнөтү: <b>{until} МСК</b>\n📌 Себеби: <b>{reason}</b>\n\n🆘 Колдоо: {support}"),
        # stats
        ("📊 <b>Твоя статистика (диапазон)</b>", "📊 <b>Your stats (range)</b>", "📊 <b>Твоя статистика (діапазон)</b>", "📊 <b>Сіздің статистикаңыз (аралық)</b>", "📊 <b>Statistikangiz (oraliq)</b>", "📊 <b>Сиздин статистикаңыз (аралык)</b>"),
        ("📊 <b>Твоя статистика:</b>", "📊 <b>Your stats:</b>", "📊 <b>Твоя статистика:</b>", "📊 <b>Сіздің статистикаңыз:</b>", "📊 <b>Statistikangiz:</b>", "📊 <b>Сиздин статистикаңыз:</b>"),
        ("📊 <b>Твоя статистика</b>", "📊 <b>Your stats</b>", "📊 <b>Твоя статистика</b>", "📊 <b>Сіздің статистикаңыз</b>", "📊 <b>Statistikangiz</b>", "📊 <b>Сиздин статистикаңыз</b>"),
        ("🎬 Видео скачано:", "🎬 Videos downloaded:", "🎬 Відео завантажено:", "🎬 Жүктелген бейне:", "🎬 Yuklab olingan video:", "🎬 Жүктөлгөн видео:"),
        ("По платформам:", "By platform:", "За платформами:", "Платформалар бойынша:", "Platformalar boʻyicha:", "Платформалар боюнча:"),
        ("🗃️ <b>Другие скачивания:</b>", "🗃️ <b>Other downloads:</b>", "🗃️ <b>Інші завантаження:</b>", "🗃️ <b>Басқа жүктеулер:</b>", "🗃️ <b>Boshqa yuklashlar:</b>", "🗃️ <b>Башка жүктөөлөр:</b>"),
        ("🖼️ Фото скачано:", "🖼️ Photos downloaded:", "🖼️ Фото завантажено:", "🖼️ Жүктелген фото:", "🖼️ Yuklab olingan rasm:", "🖼️ Жүктөлгөн сүрөт:"),
        ("🎵 Аудио скачано:", "🎵 Audio downloaded:", "🎵 Аудіо завантажено:", "🎵 Жүктелген аудио:", "🎵 Yuklab olingan audio:", "🎵 Жүктөлгөн аудио:"),
        ("📝 Описаний скачано:", "📝 Descriptions downloaded:", "📝 Описів завантажено:", "📝 Жүктелген сипаттама:", "📝 Yuklab olingan tavsif:", "📝 Жүктөлгөн сүрөттөмө:"),
        ("💛 <b>Донаты:</b>", "💛 <b>Donations:</b>", "💛 <b>Донати:</b>", "💛 <b>Донаттар:</b>", "💛 <b>Xayriyalar:</b>", "💛 <b>Донаттар:</b>"),
        ("⭐ Донат звёздами:", "⭐ Donated in Stars:", "⭐ Донат зірками:", "⭐ Жұлдызбен донат:", "⭐ Yulduzlar bilan xayriya:", "⭐ Жылдыз менен донат:"),
        ("🪙 Донат в рублях (крипто/DonationAlerts):", "🪙 Donated in rubles (crypto/DonationAlerts):", "🪙 Донат у рублях (крипто/DonationAlerts):", "🪙 Рубльмен донат (крипто/DonationAlerts):", "🪙 Rublda xayriya (kripto/DonationAlerts):", "🪙 Рубль менен донат (крипто/DonationAlerts):"),
        ("неизвестно", "unknown", "невідомо", "белгісіз", "nomaʼlum", "белгисиз"),
        ("⭐ Stars пожертвовано:", "⭐ Stars donated:", "⭐ Stars пожертвувано:", "⭐ Stars қайырымдалды:", "⭐ Stars xayriya qilindi:", "⭐ Stars кайрымдалды:"),
        ("🪙 Рублей пожертвовано:", "🪙 Rubles donated:", "🪙 Рублів пожертвувано:", "🪙 Рубль қайырымдалды:", "🪙 Rubl xayriya qilindi:", "🪙 Рубль кайрымдалды:"),
        ("🕒 Первое появление в боте:", "🕒 First seen in the bot:", "🕒 Перша поява в боті:", "🕒 Ботта алғаш пайда болған уақыт:", "🕒 Botda birinchi koʻrinish:", "🕒 Ботто биринчи пайда болгон убакыт:"),
        ("день", "day", "день", "күн", "kun", "күн"),
        ("неделя", "week", "тиждень", "апта", "hafta", "апта"),
        ("месяц", "month", "місяць", "ай", "oy", "ай"),
        ("год", "year", "рік", "жыл", "yil", "жыл"),
        ("МБ", "MB", "МБ", "МБ", "MB", "МБ"),
        ("ГБ", "GB", "ГБ", "ГБ", "GB", "ГБ"),
        # donate
        ("💖 Поддержка разработчика", "💖 Support the developer", "💖 Підтримка розробника", "💖 Әзірлеушіні қолдау", "💖 Dasturchini qoʻllab-quvvatlash", "💖 Иштеп чыгуучуну колдоо"),
        ("Донат на развитие бота", "A donation for the bot's development", "Донат на розвиток бота", "Ботты дамытуға донат", "Botni rivojlantirish uchun xayriya", "Ботту өнүктүрүүгө донат"),
        ("Чаевые", "Tip", "Чайові", "Шайлық", "Choychaqa", "Чайлык"),
        ("🗜 <b>Видео тяжёлое — сжимаю, чтобы влезло в Telegram…</b>", "🗜 <b>The video is heavy — compressing to fit Telegram…</b>", "🗜 <b>Відео важке — стискаю, щоб влізло в Telegram…</b>", "🗜 <b>Бейне ауыр — Telegram-ға сыю үшін сығып жатырмын…</b>", "🗜 <b>Video ogʻir — Telegram’ga sigʻishi uchun siqyapman…</b>", "🗜 <b>Видео оор — Telegram’га батышы үчүн кысып жатам…</b>"),
        ("⭐ Донат звёздами", "⭐ Donate with Stars", "⭐ Донат зірками", "⭐ Жұлдызбен донат", "⭐ Yulduzlar bilan xayriya", "⭐ Жылдыз менен донат"),
        ("🆘 Поддержка", "🆘 Support", "🆘 Підтримка", "🆘 Қолдау", "🆘 Yordam", "🆘 Колдоо"),
        ("✍️ Другая сумма", "✍️ Other amount", "✍️ Інша сума", "✍️ Басқа сома", "✍️ Boshqa miqdor", "✍️ Башка сумма"),
        ("💛 Донат", "💛 Donate", "💛 Донат", "💛 Донат", "💛 Xayriya", "💛 Донат"),
        ("🔗 Поделиться", "🔗 Share", "🔗 Поділитися", "🔗 Бөлісу", "🔗 Ulashish", "🔗 Бөлүшүү"),
        ("❌ Сумма должна быть {a}–{b} ⭐", "❌ The amount must be {a}–{b} ⭐", "❌ Сума має бути {a}–{b} ⭐", "❌ Сома {a}–{b} ⭐ болуы керек", "❌ Miqdor {a}–{b} ⭐ boʻlishi kerak", "❌ Сумма {a}–{b} ⭐ болушу керек"),
        ("✅ <b>Оплата прошла!</b>\nПолучено: <b>{stars} ⭐</b>\n\nСпасибо за поддержку 🙌", "✅ <b>Payment successful!</b>\nReceived: <b>{stars} ⭐</b>\n\nThank you for your support 🙌", "✅ <b>Оплата пройшла!</b>\nОтримано: <b>{stars} ⭐</b>\n\nДякуємо за підтримку 🙌", "✅ <b>Төлем сәтті өтті!</b>\nАлынды: <b>{stars} ⭐</b>\n\nҚолдауыңыз үшін рахмет 🙌", "✅ <b>Toʻlov amalga oshdi!</b>\nQabul qilindi: <b>{stars} ⭐</b>\n\nQoʻllab-quvvatlaganingiz uchun rahmat 🙌", "✅ <b>Төлөм ийгиликтүү өттү!</b>\nАлынды: <b>{stars} ⭐</b>\n\nКолдооңуз үчүн рахмат 🙌"),
        ("Отправляю звук…", "Sending audio…", "Надсилаю звук…", "Дыбыс жіберілуде…", "Audio yuborilmoqda…", "Үн жөнөтүлүүдө…"),
        ("Отправляю описание…", "Sending description…", "Надсилаю опис…", "Сипаттама жіберілуде…", "Tavsif yuborilmoqda…", "Сүрөттөмө жөнөтүлүүдө…"),
        ("Нет звука для этого видео.", "This video has no audio.", "Для цього відео немає звуку.", "Бұл бейнеде дыбыс жоқ.", "Bu videoda audio yoʻq.", "Бул видеодо үн жок."),
        ("Нет описания для этого видео.", "This video has no description.", "Для цього відео немає опису.", "Бұл бейнеде сипаттама жоқ.", "Bu videoda tavsif yoʻq.", "Бул видеодо сүрөттөмө жок."),
        ("✍️ Введи сумму доната {a}–{b} ⭐ одним числом:", "✍️ Enter the donation amount {a}–{b} ⭐ as a single number:", "✍️ Введи суму донату {a}–{b} ⭐ одним числом:", "✍️ Донат сомасын {a}–{b} ⭐ бір санмен енгізіңіз:", "✍️ Xayriya miqdorini {a}–{b} ⭐ bitta son bilan kiriting:", "✍️ Донат суммасын {a}–{b} ⭐ бир сан менен киргизиңиз:"),
        ("❌ Ошибка суммы", "❌ Invalid amount", "❌ Помилка суми", "❌ Сома қате", "❌ Miqdor notoʻgʻri", "❌ Сумма туура эмес"),
        # inline
        ("✅ Готово — отправить видео", "✅ Ready — send the video", "✅ Готово — надіслати відео", "✅ Дайын — бейнені жіберу", "✅ Tayyor — videoni yuborish", "✅ Даяр — видеону жөнөтүү"),
        ("Вставь ссылку на TikTok / YouTube / Instagram / VK / Pinterest / Likee / X / OK", "Paste a link to TikTok / YouTube / Instagram / VK / Pinterest / Likee / X / OK", "Встав посилання на TikTok / YouTube / Instagram / VK / Pinterest / Likee / X / OK", "TikTok / YouTube / Instagram / VK / Pinterest / Likee / X / OK сілтемесін қойыңыз", "TikTok / YouTube / Instagram / VK / Pinterest / Likee / X / OK havolasini qoʻying", "TikTok / YouTube / Instagram / VK / Pinterest / Likee / X / OK шилтемесин коюңуз"),
        ("Начни печатать — бот покажет результат прямо тут", "Start typing — the bot will show the result right here", "Почни друкувати — бот покаже результат прямо тут", "Теруді бастаңыз — бот нәтижені осы жерде көрсетеді", "Yozishni boshlang — bot natijani shu yerda koʻrsatadi", "Тере баштаңыз — бот натыйжаны ушул жерден көрсөтөт"),
        ("Ссылка не распознана", "Link not recognized", "Посилання не розпізнано", "Сілтеме танылмады", "Havola aniqlanmadi", "Шилтеме таанылган жок"),
        ("Поддерживаются TikTok, YouTube, Instagram, VK, Pinterest, Likee, X, OK", "Supported: TikTok, YouTube, Instagram, VK, Pinterest, Likee, X, OK", "Підтримуються TikTok, YouTube, Instagram, VK, Pinterest, Likee, X, OK", "Қолдау көрсетіледі: TikTok, YouTube, Instagram, VK, Pinterest, Likee, X, OK", "Qoʻllab-quvvatlanadi: TikTok, YouTube, Instagram, VK, Pinterest, Likee, X, OK", "Колдоого алынат: TikTok, YouTube, Instagram, VK, Pinterest, Likee, X, OK"),
        ("⏳ Слишком много запросов подряд", "⏳ Too many requests in a row", "⏳ Забагато запитів поспіль", "⏳ Қатарынан тым көп сұраныс", "⏳ Ketma-ket juda koʻp soʻrov", "⏳ Удаалаш өтө көп суроо"),
        ("Попробуй через минуту", "Try again in a minute", "Спробуй за хвилину", "Бір минуттан кейін қайталаңыз", "Bir daqiqadan keyin urinib koʻring", "Бир мүнөттөн кийин кайра аракет кылыңыз"),
        ("⏳ Видео скачивается…", "⏳ The video is downloading…", "⏳ Відео завантажується…", "⏳ Бейне жүктелуде…", "⏳ Video yuklanmoqda…", "⏳ Видео жүктөлүүдө…"),
        ("Подожди ~10 сек и поменяй запрос (добавь/убери пробел) — видео будет готово мгновенно", "Wait ~10 sec and change the query (add/remove a space) — the video will be ready instantly", "Зачекай ~10 сек і зміни запит (додай/прибери пробіл) — відео буде готове миттєво", "~10 сек күтіп, сұранысты өзгертіңіз (бос орын қосыңыз/алыңыз) — бейне бірден дайын болады", "~10 soniya kuting va soʻrovni oʻzgartiring (probel qoʻshing/oʻchiring) — video darhol tayyor boʻladi", "~10 сек күтүп, сурооңузду өзгөртүңүз (боштук кошуңуз/алыңыз) — видео ошол замат даяр болот"),
        ("❌ Не получилось скачать это видео", "❌ Couldn't download this video", "❌ Не вдалося завантажити це відео", "❌ Бұл бейнені жүктеу мүмкін болмады", "❌ Bu videoni yuklab boʻlmadi", "❌ Бул видеону жүктөө мүмкүн болгон жок"),
        ("📎 Пришли мне ссылку на TikTok, YouTube, Instagram, VK, Pinterest, Likee, X или OK — скачаю видео.", "📎 Send me a link to TikTok, YouTube, Instagram, VK, Pinterest, Likee, X or OK — I'll download the video.", "📎 Надішли мені посилання на TikTok, YouTube, Instagram, VK, Pinterest, Likee, X або OK — завантажу відео.", "📎 TikTok, YouTube, Instagram, VK, Pinterest, Likee, X немесе OK сілтемесін жіберіңіз — бейнені жүктеп беремін.", "📎 TikTok, YouTube, Instagram, VK, Pinterest, Likee, X yoki OK havolasini yuboring — videoni yuklab beraman.", "📎 TikTok, YouTube, Instagram, VK, Pinterest, Likee, X же OK шилтемесин жөнөтүңүз — видеону жүктөп берем."),
        ("❌ Не нашёл поддерживаемую ссылку в запросе.", "❌ No supported link found in the query.", "❌ Не знайшов підтримуваного посилання в запиті.", "❌ Сұраныста қолдау көрсетілетін сілтеме табылмады.", "❌ Soʻrovda qoʻllab-quvvatlanadigan havola topilmadi.", "❌ Суроодо колдоого алынган шилтеме табылган жок."),
        ("⏳ Слишком много запросов подряд — попробуй через минуту.", "⏳ Too many requests in a row — try again in a minute.", "⏳ Забагато запитів поспіль — спробуй за хвилину.", "⏳ Қатарынан тым көп сұраныс — бір минуттан кейін қайталаңыз.", "⏳ Ketma-ket juda koʻp soʻrov — bir daqiqadan keyin urinib koʻring.", "⏳ Удаалаш өтө көп суроо — бир мүнөттөн кийин кайра аракет кылыңыз."),
        ("⏳ Видео ещё скачивается. Повтори запрос через несколько секунд — оно уже будет в кэше и отправится мгновенно. Или пришли ссылку боту в чат.", "⏳ The video is still downloading. Repeat the query in a few seconds — it will already be cached and sent instantly. Or send the link to the bot in chat.", "⏳ Відео ще завантажується. Повтори запит через кілька секунд — воно вже буде в кеші й надішлеться миттєво. Або надішли посилання боту в чат.", "⏳ Бейне әлі жүктелуде. Бірнеше секундтан кейін сұранысты қайталаңыз — ол кэште болады да, бірден жіберіледі. Немесе сілтемені ботқа чатта жіберіңіз.", "⏳ Video hali yuklanmoqda. Bir necha soniyadan keyin soʻrovni takrorlang — u keshda boʻladi va darhol yuboriladi. Yoki havolani botga chatda yuboring.", "⏳ Видео дагы жүктөлүп жатат. Бир нече секунддан кийин сурооңузду кайталаңыз — ал кэште болуп, ошол замат жөнөтүлөт. Же шилтемени ботко чатка жөнөтүңүз."),
        ("❌ {reason}. Попробуй прислать ссылку боту напрямую в чат.", "❌ {reason}. Try sending the link to the bot directly in chat.", "❌ {reason}. Спробуй надіслати посилання боту напряму в чат.", "❌ {reason}. Сілтемені ботқа тікелей чатта жіберіп көріңіз.", "❌ {reason}. Havolani botga bevosita chatda yuborib koʻring.", "❌ {reason}. Шилтемени ботко түздөн-түз чатка жөнөтүп көрүңүз."),
        ("Видео слишком тяжёлое для инлайна", "The video is too heavy for inline mode", "Відео надто важке для inline", "Бейне inline үшін тым ауыр", "Video inline uchun juda ogʻir", "Видео inline үчүн өтө оор"),
        ("Это фото-слайдшоу — в инлайне только видео", "This is a photo slideshow — inline supports video only", "Це фото-слайдшоу — в inline лише відео", "Бұл фото-слайдшоу — inline-да тек бейне", "Bu foto-slayd — inline’da faqat video", "Бул фото-слайдшоу — inline’да видео гана"),
        ("Открой бота @tiksavesbot и нажми /start, затем повтори", "Open the bot @tiksavesbot and press /start, then try again", "Відкрий бота @tiksavesbot і натисни /start, потім повтори", "@tiksavesbot ботын ашып, /start басыңыз, содан кейін қайталаңыз", "@tiksavesbot botini oching va /start bosing, soʻng qayta urining", "@tiksavesbot ботун ачып, /start басыңыз, анан кайра аракет кылыңыз"),
        ("Не удалось скачать (приватное/недоступное видео?)", "Couldn't download (private/unavailable video?)", "Не вдалося завантажити (приватне/недоступне відео?)", "Жүктеу мүмкін болмады (жеке/қолжетімсіз бейне ме?)", "Yuklab boʻlmadi (maxfiy/mavjud boʻlmagan video?)", "Жүктөө мүмкүн болгон жок (жеке/жеткиликсиз видео?)"),
    ]
    for r in rows:
        _reg(*r)
