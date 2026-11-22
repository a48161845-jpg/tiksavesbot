"""
Переводы экранов и коротких строк в новом оформлении.

Экраны (старт, помощь, донат, поддержка, ...) собирает ui/screens_text.build(<язык>) — тем же кодом, что и русские
оригиналы, поэтому разметка совпадает всегда. Здесь же — короткие строки (подписи, антиспам, предупреждение),
строки выбора формата фото и inline-режима. Подключается последним в i18n._ensure_loaded() и перекрывает
старые записи с теми же ключами.
"""
from ui.screens_text import PHRASES, build

# ------------------------------------------------------------------ короткие строки по языкам
SMALL = {'en': {'done': 'Done',
        'audio': 'Audio ready',
        'spam': "🛡 <b>Not so fast</b>\nRequests are coming too often. Wait ~{n} sec. and try again — it's flood protection.",
        'w_t': 'Before you download',
        'w_b': "Download only your own content or content you have the author's permission for. Respect other people's work 🙏"},
 'uk': {'done': 'Готово',
        'audio': 'Звук готовий',
        'spam': '🛡 <b>Не так швидко</b>\nЗапити надходять надто часто. Зачекай ~{n} сек. і спробуй знову — це захист від флуду.',
        'w_t': 'Перед завантаженням',
        'w_b': 'Завантажуй лише власний контент або той, на який є дозвіл автора. Поважай чужу працю 🙏'},
 'kk': {'done': 'Дайын',
        'audio': 'Дыбыс дайын',
        'spam': '🛡 <b>Тым жылдам</b>\nСұраныстар тым жиі келіп жатыр. ~{n} сек. күтіп, қайта көріңіз — бұл флудтан қорғау.',
        'w_t': 'Жүктемес бұрын',
        'w_b': 'Тек өз контентіңізді немесе автор рұқсат берген контентті жүктеңіз. Басқалардың еңбегін құрметтеңіз 🙏'},
 'uz': {'done': 'Tayyor',
        'audio': 'Ovoz tayyor',
        'spam': '🛡 <b>Shoshilmang</b>\n'
                'Soʻrovlar juda tez-tez kelyapti. ~{n} soniya kuting va qayta urinib koʻring — bu fluddan himoya.',
        'w_t': 'Yuklashdan oldin',
        'w_b': 'Faqat oʻzingizning yoki muallif ruxsat bergan kontentni yuklang. Boshqalarning mehnatini hurmat qiling 🙏'},
 'ky': {'done': 'Даяр',
        'audio': 'Үн даяр',
        'spam': '🛡 <b>Ашыкпаңыз</b>\n'
                'Суроолор өтө тез-тез келип жатат. ~{n} сек. күтүп, кайра аракет кылыңыз — бул флуддан коргонуу.',
        'w_t': 'Жүктөөдөн мурун',
        'w_b': 'Өзүңүздүн же автор уруксат берген контентти гана жүктөңүз. Башкалардын эмгегин сыйлаңыз 🙏'}}

# «📐 Оригинал» и подсказка при выборе формата фото
RATIO_STRINGS = {'en': ['📐 Original', '📐 Format: {r}'],
 'uk': ['📐 Оригінал', '📐 Формат: {r}'],
 'kk': ['📐 Түпнұсқа', '📐 Формат: {r}'],
 'uz': ['📐 Asl', '📐 Format: {r}'],
 'ky': ['📐 Оригинал', '📐 Формат: {r}']}

# Строки inline-режима: (ru, en, uk, kk, uz, ky)
EXTRA_ROWS = [('🔗 Вставь ссылку на видео или фото',
  '🔗 Paste a link to a video or photo',
  '🔗 Встав посилання на відео або фото',
  '🔗 Бейне немесе фото сілтемесін қойыңыз',
  '🔗 Video yoki rasm havolasini qoʻying',
  '🔗 Видео же сүрөткө шилтеме коюңуз'),
 ('TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube, Reddit. Для фото добавь формат: 1:1, 4:3, 3:4, 16:9, 9:16',
  'TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube, Reddit. For photos add a format: 1:1, 4:3, 3:4, 16:9, 9:16',
  'TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube, Reddit. Для фото додай формат: 1:1, 4:3, 3:4, 16:9, 9:16',
  'TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube, Reddit. Фото үшін форматты қосыңыз: 1:1, 4:3, 3:4, 16:9, 9:16',
  'TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube, Reddit. Rasm uchun format qoʻshing: 1:1, 4:3, 3:4, 16:9, 9:16',
  'TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube, Reddit. Сүрөт үчүн форматты кошуңуз: 1:1, 4:3, 3:4, 16:9, 9:16'),
 ('📎 Пришли мне ссылку на TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube или Reddit — скачаю видео и фото без водяных '
  'знаков.\n'
  '\n'
  'В inline-режиме: @tiksavesbot ссылка. Для фото можно добавить формат кадра: 1:1, 4:3, 3:4, 16:9 или 9:16.',
  "📎 Send me a link to TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube or Reddit — I'll download the video and photos "
  'without watermarks.\n'
  '\n'
  'In inline mode: @tiksavesbot link. For photos you can add a frame format: 1:1, 4:3, 3:4, 16:9 or 9:16.',
  '📎 Надішли мені посилання на TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube або Reddit — завантажу відео та фото без '
  'водяних знаків.\n'
  '\n'
  'В inline-режимі: @tiksavesbot посилання. Для фото можна додати формат кадру: 1:1, 4:3, 3:4, 16:9 або 9:16.',
  '📎 TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube немесе Reddit сілтемесін жіберіңіз — бейне мен фотоны су белгісінсіз '
  'жүктеп беремін.\n'
  '\n'
  'Inline-режимде: @tiksavesbot сілтеме. Фото үшін кадр форматын қосуға болады: 1:1, 4:3, 3:4, 16:9 немесе 9:16.',
  '📎 TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube yoki Reddit havolasini yuboring — video va rasmlarni suv belgisisiz '
  'yuklab beraman.\n'
  '\n'
  'Inline-rejimda: @tiksavesbot havola. Rasm uchun kadr formatini qoʻshish mumkin: 1:1, 4:3, 3:4, 16:9 yoki 9:16.',
  '📎 TikTok, YouTube, Instagram, VK, Pinterest, X, Rutube же Reddit шилтемесин жөнөтүңүз — видео жана сүрөттөрдү суу белгисиз '
  'жүктөп берем.\n'
  '\n'
  'Inline-режимде: @tiksavesbot шилтеме. Сүрөт үчүн кадр форматын кошсо болот: 1:1, 4:3, 3:4, 16:9 же 9:16.'),
 ('🖼 Фото {i} из {n}', '🖼 Photo {i} of {n}', '🖼 Фото {i} з {n}', '🖼 Фото {i} / {n}', '🖼 Rasm {i} / {n}', '🖼 Сүрөт {i} / {n}'),
 ('Нажми — кадр отправится в чат',
  'Tap to send this frame to the chat',
  'Натисни — кадр надійде в чат',
  'Басыңыз — кадр чатқа жіберіледі',
  'Bosing — kadr chatga yuboriladi',
  'Басыңыз — кадр чатка жөнөтүлөт'),
 ('⏳ Скачиваю…', '⏳ Downloading…', '⏳ Завантажую…', '⏳ Жүктеп жатырмын…', '⏳ Yuklayapman…', '⏳ Жүктөп жатам…'),
 ('Подожди ~10 сек и поменяй запрос (добавь/убери пробел) — всё будет готово мгновенно',
  'Wait ~10 sec and change the query (add/remove a space) — everything will be ready instantly',
  'Зачекай ~10 сек і змін запит (додай/прибери пробіл) — усе буде готово миттєво',
  '~10 сек күтіп, сұранысты өзгертіңіз (бос орын қосыңыз/алыңыз) — бәрі лезде дайын болады',
  '~10 soniya kuting va soʻrovni oʻzgartiring (boʻshliq qoʻshing/olib tashlang) — hammasi bir zumda tayyor boʻladi',
  '~10 сек күтүп, сурамды өзгөртүңүз (боштук кошуңуз/алыңыз) — баары заматта даяр болот'),
 ('⏳ Ещё скачивается. Повтори запрос через несколько секунд — результат уже будет в кэше и отправится мгновенно. Или пришли '
  'ссылку боту в чат.',
  '⏳ Still downloading. Repeat the request in a few seconds — the result will already be cached and will be sent instantly. Or '
  'send the link to the bot in chat.',
  '⏳ Ще завантажується. Повтори запит за кілька секунд — результат уже буде в кеші й надійде миттєво. Або надішли посилання боту '
  'в чат.',
  '⏳ Әлі жүктелуде. Бірнеше секундтан соң сұранысты қайталаңыз — нәтиже кэште болады да, лезде жіберіледі. Немесе сілтемені '
  'ботқа чатта жіберіңіз.',
  '⏳ Hali yuklanmoqda. Bir necha soniyadan keyin soʻrovni takrorlang — natija keshda boʻladi va bir zumda yuboriladi. Yoki '
  'havolani botga chatda yuboring.',
  '⏳ Дагы жүктөлүүдө. Бир нече секундадан кийин сурамды кайталаңыз — жыйынтык кэште болуп, заматта жөнөтүлөт. Же шилтемени ботко '
  'чатта жөнөтүңүз.'),
 ('❌ Не получилось скачать',
  '❌ Download failed',
  '❌ Не вдалося завантажити',
  '❌ Жүктеу мүмкін болмады',
  '❌ Yuklab boʻlmadi',
  '❌ Жүктөө мүмкүн болбоду'),
 ('Не удалось скачать (приватный или недоступный пост?)',
  "Couldn't download (private or unavailable post?)",
  'Не вдалося завантажити (приватний або недоступний пост?)',
  'Жүктеу мүмкін болмады (жабық немесе қолжетімсіз пост?)',
  'Yuklab boʻlmadi (yopiq yoki mavjud boʻlmagan post?)',
  'Жүктөө мүмкүн болбоду (жабык же жеткиликсиз пост?)'),
 ('Не удалось скачать фото',
  "Couldn't download the photos",
  'Не вдалося завантажити фото',
  'Фотоны жүктеу мүмкін болмады',
  'Rasmlarni yuklab boʻlmadi',
  'Сүрөттөрдү жүктөө мүмкүн болбоду'),
 ('В посте нет видео',
  'The post has no video',
  'У пості немає відео',
  'Постта бейне жоқ',
  'Postda video yoʻq',
  'Постто видео жок')]

# Premium, «любой банк», оплата (ru, en, uk, kk, uz, ky)
EXTRA_ROWS += [
    ("🏦 Любой банк (СБП)", "🏦 Any bank (SBP)", "🏦 Будь-який банк (СБП)", "🏦 Кез келген банк (СБП)", "🏦 Istalgan bank (SBP)", "🏦 Каалаган банк (СБП)"),
    ("💎 Premium активен до {date}", "💎 Premium is active until {date}", "💎 Premium активний до {date}", "💎 Premium {date} дейін белсенді", "💎 Premium {date} gacha faol", "💎 Premium {date} чейин иштейт"),
    ("💎 {days} дн. — {stars} ⭐", "💎 {days} days — {stars} ⭐", "💎 {days} дн. — {stars} ⭐", "💎 {days} күн — {stars} ⭐", "💎 {days} kun — {stars} ⭐", "💎 {days} күн — {stars} ⭐"),
    ("💎 TikSaves Premium", "💎 TikSaves Premium", "💎 TikSaves Premium", "💎 TikSaves Premium", "💎 TikSaves Premium", "💎 TikSaves Premium"),
    ("Premium на {days} дн.: лимиты ×{m}, без напоминаний о донате, значок 💎",
     "Premium for {days} days: limits ×{m}, no donation reminders, 💎 badge",
     "Premium на {days} дн.: ліміти ×{m}, без нагадувань про донат, значок 💎",
     "{days} күнге Premium: лимиттер ×{m}, донат туралы еске салусыз, 💎 белгісі",
     "{days} kunlik Premium: limitlar ×{m}, xayriya eslatmalarisiz, 💎 belgisi",
     "{days} күнгө Premium: лимиттер ×{m}, донат эскертмесиз, 💎 белгиси"),
    ("Premium", "Premium", "Premium", "Premium", "Premium", "Premium"),
    ("💳 <b>Вопросы по оплате</b>\nЕсли платёж не прошёл или нужен возврат — напиши в /support и укажи сумму и время платежа.",
     "💳 <b>Payment questions</b>\nIf a payment failed or you need a refund — write to /support and include the amount and time of the payment.",
     "💳 <b>Питання щодо оплати</b>\nЯкщо платіж не пройшов або потрібне повернення — напиши в /support і вкажи суму та час платежу.",
     "💳 <b>Төлем бойынша сұрақтар</b>\nТөлем өтпесе немесе қайтару керек болса — /support-қа жазып, соманы және төлем уақытын көрсетіңіз.",
     "💳 <b>Toʻlov boʻyicha savollar</b>\nToʻlov oʻtmagan yoki qaytarish kerak boʻlsa — /support ga yozing va summa hamda toʻlov vaqtini koʻrsating.",
     "💳 <b>Төлөм боюнча суроолор</b>\nТөлөм өтпөсө же кайтарып берүү керек болсо — /support'ка жазып, сумманы жана төлөм убактысын көрсөтүңүз."),
    ("✖️ Обращение отменено. Если понадобится помощь — /support.", "✖️ Request cancelled. If you need help — /support.", "✖️ Звернення скасовано. Якщо потрібна допомога — /support.", "✖️ Өтініш болдырылмады. Көмек керек болса — /support.", "✖️ Murojaat bekor qilindi. Yordam kerak boʻlsa — /support.", "✖️ Кайрылуу жокко чыгарылды. Жардам керек болсо — /support."),
    ("📩 <b>Сообщение от администрации</b>", "📩 <b>Message from the administration</b>", "📩 <b>Повідомлення від адміністрації</b>", "📩 <b>Әкімшіліктен хабарлама</b>", "📩 <b>Ma’muriyatdan xabar</b>", "📩 <b>Администрациядан кабар</b>"),
    ("💬 Ответить", "💬 Reply", "💬 Відповісти", "💬 Жауап беру", "💬 Javob berish", "💬 Жооп берүү"),
    ("🔎 Найти песню", "🔎 Find the song", "🔎 Знайти пісню", "🔎 Әнді табу", "🔎 Qoʻshiqni topish", "🔎 Ырды табуу"),
    ("⬇️ Скачать аудио", "⬇️ Download audio", "⬇️ Завантажити аудіо", "⬇️ Аудионы жүктеу", "⬇️ Audioni yuklash", "⬇️ Аудионы жүктөө"),
    ("Нет данных о песне для этого видео.", "No song data for this video.", "Немає даних про пісню для цього відео.", "Бұл бейне үшін ән туралы дерек жоқ.", "Bu video uchun qoʻshiq maʼlumoti yoʻq.", "Бул видео үчүн ыр жөнүндө маалымат жок."),
    ("🎵 <b>Песня из видео</b>\n<b>{title}</b>\n{author}\n\nНайди её в любимом сервисе или скачай звук 👇",
     "🎵 <b>Song from the video</b>\n<b>{title}</b>\n{author}\n\nFind it in your favorite service or download the sound 👇",
     "🎵 <b>Пісня з відео</b>\n<b>{title}</b>\n{author}\n\nЗнайди її в улюбленому сервісі або завантаж звук 👇",
     "🎵 <b>Бейнедегі ән</b>\n<b>{title}</b>\n{author}\n\nОны сүйікті сервисте табыңыз немесе дыбысты жүктеңіз 👇",
     "🎵 <b>Videodagi qoʻshiq</b>\n<b>{title}</b>\n{author}\n\nUni sevimli xizmatingizda toping yoki ovozni yuklab oling 👇",
     "🎵 <b>Видеодогу ыр</b>\n<b>{title}</b>\n{author}\n\nАны жактырган сервисиңизден табыңыз же үндү жүктөп алыңыз 👇"),
    ("🎤 <b>Оригинальный звук</b>\nАвтор: <b>{author}</b>\n\nЭто звук самого автора видео — в музыкальных сервисах его, скорее всего, нет. Можно скачать как аудио 👇",
     "🎤 <b>Original sound</b>\nAuthor: <b>{author}</b>\n\nThis is the video author's own sound — it's most likely not in music services. You can download it as audio 👇",
     "🎤 <b>Оригінальний звук</b>\nАвтор: <b>{author}</b>\n\nЦе звук самого автора відео — у музичних сервісах його, найімовірніше, немає. Можна завантажити як аудіо 👇",
     "🎤 <b>Түпнұсқа дыбыс</b>\nАвтор: <b>{author}</b>\n\nБұл бейне авторының өз дыбысы — музыкалық сервистерде ол, ықтимал, жоқ. Аудио ретінде жүктеуге болады 👇",
     "🎤 <b>Asl ovoz</b>\nMuallif: <b>{author}</b>\n\nBu video muallifining oʻz ovozi — musiqa xizmatlarida u, ehtimol, yoʻq. Audio sifatida yuklab olish mumkin 👇",
     "🎤 <b>Түпнуска үн</b>\nАвтор: <b>{author}</b>\n\nБул видеонун автору өзү жазган үн — музыкалык сервистерде ал, кыязы, жок. Аудио катары жүктөп алса болот 👇"),
]

LANGS = ("en", "uk", "kk", "uz", "ky")


def build_translations(lang: str) -> dict:
    """{русский ключ: перевод} для языка lang."""
    from core.config import CAPTION_VIDEO, CAPTION_PHOTO, CAPTION_AUDIO, MSG_SPAM, PHOTO_WARNING_TEXT
    from ui import keyboards as K
    ru, tr_ = build("ru"), build(lang)
    s = SMALL[lang]
    out = {
        K.START_TEXT: tr_["start"], K.HELP_TEXT: tr_["help"], K.DONATE_TEXT: tr_["donate"],
        K.STARS_MENU_TEXT: tr_["stars"], K.RUB_DONATE_TEXT: tr_["rub"], K.SUPPORT_TEXT: tr_["support"],
        K.SUPPORT_SENT_TEXT: tr_["sent"], K.SUPPORT_TIMEOUT_TEXT: tr_["timeout"],
        K.PHOTO_CHOICE_TEXT: tr_["photo_choice"], K.QUALITY_CHOICE_TEXT: tr_["quality"],
        K.PREMIUM_TEXT: tr_["premium"], K.PREMIUM_OK_TEXT: tr_["premium_ok"],
        CAPTION_VIDEO: f"🎬 <b>{s['done']}</b> · @tiksavesbot",
        CAPTION_PHOTO: f"🖼 <b>{s['done']}</b> · @tiksavesbot",
        CAPTION_AUDIO: f"🎵 <b>{s['audio']}</b> · @tiksavesbot",
        MSG_SPAM: s["spam"],
        PHOTO_WARNING_TEXT: f"<b>⚠️ {s['w_t']}</b>\n<blockquote>{s['w_b']}</blockquote>",
    }
    for key in K.HELP_SECTIONS:
        out[K.HELP_SECTIONS[key]] = tr_[f"help_{key}"]
    for ru_btn, tx in zip(PHRASES["ru"]["btn"], PHRASES[lang]["btn"]):
        out[ru_btn] = tx
    out["📐 Оригинал"], out["📐 Формат: {r}"] = RATIO_STRINGS[lang]
    idx = LANGS.index(lang) + 1
    for row in EXTRA_ROWS:
        out[row[0]] = row[idx]
    # «кричащие» напоминания после скачивания и шаблоны рассылок
    from core.nudge_texts import ALL_TRANSLATED
    for d in ALL_TRANSLATED:
        out[d["ru"]] = d[lang]
    return out


def register_screens(_reg) -> None:
    from i18n import TRANSLATIONS
    for lang in LANGS:
        TRANSLATIONS[lang].update(build_translations(lang))
