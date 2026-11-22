"""
Тексты напоминаний после скачивания и шаблонов рассылок — на всех языках.

Формат — готовый HTML для Telegram. Структура у всех языков одинаковая (проверяет tests/test_nudges.py).
В напоминаниях есть подстановка {m} (во сколько раз Premium увеличивает лимиты) — её заполняет tr(..., m=...);
в шаблонах рассылок {m} подставляется сразу при загрузке модуля.
"""
from core.config import PREMIUM_LIMIT_MULT

LANGS = ("ru", "en", "uk", "kk", "uz", "ky")


def _d(ru, en, uk, kk, uz, ky):
    return dict(zip(LANGS, (ru, en, uk, kk, uz, ky)))


# ------------------------------------------------------------------ напоминания про донат (кричащие)
DONATE_NUDGES = [
    _d(
        "🔥🔥🔥 <b>БОТ БЕСПЛАТНЫЙ — А СЕРВЕР НЕТ!</b> 🔥🔥🔥\n\nКаждое твоё скачивание — это трафик, место на диске и часы работы. Закинь хотя бы <b>10 ⭐</b> — и TikSaves будет жить дальше! 💛\n\n👇 <b>ЖМИ И ПОДДЕРЖИ ПРЯМО СЕЙЧАС</b>",
        "🔥🔥🔥 <b>THE BOT IS FREE — THE SERVER ISN'T!</b> 🔥🔥🔥\n\nEvery download you make costs traffic, disk space and server hours. Toss in at least <b>10 ⭐</b> — and TikSaves keeps going! 💛\n\n👇 <b>TAP AND SUPPORT IT RIGHT NOW</b>",
        "🔥🔥🔥 <b>БОТ БЕЗКОШТОВНИЙ — А СЕРВЕР НІ!</b> 🔥🔥🔥\n\nКожне твоє завантаження — це трафік, місце на диску й години роботи. Закинь хоча б <b>10 ⭐</b> — і TikSaves житиме далі! 💛\n\n👇 <b>НАТИСКАЙ І ПІДТРИМАЙ ПРЯМО ЗАРАЗ</b>",
        "🔥🔥🔥 <b>БОТ ТЕГІН — АЛ СЕРВЕР ЕМЕС!</b> 🔥🔥🔥\n\nӘр жүктеуіңіз — трафик, диск орны және жұмыс сағаттары. Кемінде <b>10 ⭐</b> тастаңыз — сонда TikSaves жұмысын жалғастырады! 💛\n\n👇 <b>БАСЫҢЫЗ ДА ДӘЛ ҚАЗІР ҚОЛДАҢЫЗ</b>",
        "🔥🔥🔥 <b>BOT TEKIN — SERVER ESA YOʻQ!</b> 🔥🔥🔥\n\nHar bir yuklashingiz — trafik, disk joyi va ishlash soatlari. Hech boʻlmasa <b>10 ⭐</b> tashlang — TikSaves ishlashda davom etadi! 💛\n\n👇 <b>BOSING VA HOZIROQ QOʻLLAB-QUVVATLANG</b>",
        "🔥🔥🔥 <b>БОТ АКЫСЫЗ — СЕРВЕР АКЫСЫЗ ЭМЕС!</b> 🔥🔥🔥\n\nЖүктөө сайын трафик, диск орду жана иштөө сааттары кетет. Жок дегенде <b>10 ⭐</b> таштаңыз — TikSaves иштей берет! 💛\n\n👇 <b>БАСЫҢЫЗ ЖАНА ДАЛ АЗЫР КОЛДОҢУЗ</b>",
    ),
    _d(
        "🚨 <b>ВНИМАНИЕ! ЭТОТ БОТ ЖИВЁТ НА ДОНАТАХ!</b> 🚨\n\nТы только что получил(а) файл без водяных знаков — бесплатно. Хостинг платный. Помоги проекту — это <b>10 секунд</b> и любая сумма! 💸\n\n👇 <b>ВЫБЕРИ СПОСОБ</b>",
        "🚨 <b>ATTENTION! THIS BOT LIVES ON DONATIONS!</b> 🚨\n\nYou just got a watermark-free file — for free. Hosting isn't free. Help the project — it takes <b>10 seconds</b> and any amount! 💸\n\n👇 <b>CHOOSE A METHOD</b>",
        "🚨 <b>УВАГА! ЦЕЙ БОТ ЖИВЕ НА ДОНАТАХ!</b> 🚨\n\nТи щойно отримав(ла) файл без водяних знаків — безкоштовно. Хостинг платний. Допоможи проєкту — це <b>10 секунд</b> і будь-яка сума! 💸\n\n👇 <b>ОБЕРИ СПОСІБ</b>",
        "🚨 <b>НАЗАР АУДАРЫҢЫЗ! БҰЛ БОТ ДОНАТТАРМЕН ТІРШІЛІК ЕТЕДІ!</b> 🚨\n\nСіз жаңа ғана су белгісіз файлды тегін алдыңыз. Хостинг ақылы. Жобаға көмектесіңіз — бұл <b>10 секунд</b> және кез келген сома! 💸\n\n👇 <b>ТӘСІЛДІ ТАҢДАҢЫЗ</b>",
        "🚨 <b>DIQQAT! BU BOT XAYRIYALAR HISOBIGA YASHAYDI!</b> 🚨\n\nSiz hozirgina suv belgisiz faylni tekinga oldingiz. Hosting esa pullik. Loyihaga yordam bering — bu <b>10 soniya</b> va istalgan summa! 💸\n\n👇 <b>USULNI TANLANG</b>",
        "🚨 <b>ЭСКЕРТҮҮ! БУЛ БОТ ДОНАТТАР МЕНЕН ЖАШАЙТ!</b> 🚨\n\nСиз жаңы эле суу белгисиз файлды акысыз алдыңыз. Хостинг акы төлөнөт. Долбоорго жардам бериңиз — бул <b>10 секунд</b> жана каалаган сумма! 💸\n\n👇 <b>ЫКМАНЫ ТАНДАҢЫЗ</b>",
    ),
    _d(
        "💥 <b>«СПАСИБО» НЕ ПЛАТИТ ЗА СЕРВЕР!</b> 💥\n\nЕсли TikSaves сэкономил тебе время — отблагодари донатом: ⭐ Stars, 🏦 любой банк по СБП или 💳 карта.\n\n❤️‍🔥 <b>ЛЮБАЯ СУММА ВАЖНА!</b>",
        "💥 <b>“THANKS” DOESN'T PAY FOR THE SERVER!</b> 💥\n\nIf TikSaves saved you time — say thanks with a donation: ⭐ Stars, 🏦 any bank via SBP or 💳 a card.\n\n❤️‍🔥 <b>EVERY AMOUNT MATTERS!</b>",
        "💥 <b>«ДЯКУЮ» НЕ ПЛАТИТЬ ЗА СЕРВЕР!</b> 💥\n\nЯкщо TikSaves заощадив тобі час — віддячи донатом: ⭐ Stars, 🏦 будь-який банк через СБП або 💳 картка.\n\n❤️‍🔥 <b>БУДЬ-ЯКА СУМА ВАЖЛИВА!</b>",
        "💥 <b>«РАХМЕТ» СЕРВЕРДІ ТӨЛЕМЕЙДІ!</b> 💥\n\nTikSaves уақытыңызды үнемдесе — донатпен алғыс айтыңыз: ⭐ Stars, 🏦 кез келген банк СБП арқылы немесе 💳 карта.\n\n❤️‍🔥 <b>ӘРБІР СОМА МАҢЫЗДЫ!</b>",
        "💥 <b>«RAHMAT» SERVER UCHUN TOʻLAMAYDI!</b> 💥\n\nTikSaves vaqtingizni tejagan boʻlsa — xayriya bilan minnatdorchilik bildiring: ⭐ Stars, 🏦 istalgan bank SBP orqali yoki 💳 karta.\n\n❤️‍🔥 <b>HAR BIR SUMMA MUHIM!</b>",
        "💥 <b>«РАХМАТ» СЕРВЕРДИ ТӨЛӨБӨЙТ!</b> 💥\n\nTikSaves убакытыңызды үнөмдөсө — донат менен ыраазычылык билдириңиз: ⭐ Stars, 🏦 каалаган банк СБП аркылуу же 💳 карта.\n\n❤️‍🔥 <b>КАЛААГАН СУММА МААНИЛҮҮ!</b>",
    ),
    _d(
        "⚡️ <b>СКАЧАЛ(А) БЕЗ ВОДЯНЫХ ЗНАКОВ?</b> ⚡️\n\nЗначит, бот работает для тебя. Помоги ему работать дальше — <b>донат от 10 ⭐</b> поможет оплатить серверы! 🖥💛\n\n👇 <b>ПОДДЕРЖАТЬ ПРОЕКТ</b>",
        "⚡️ <b>JUST DOWNLOADED WITHOUT WATERMARKS?</b> ⚡️\n\nThen the bot works for you. Help it keep working — a <b>donation from 10 ⭐</b> helps pay for the servers! 🖥💛\n\n👇 <b>SUPPORT THE PROJECT</b>",
        "⚡️ <b>ЗАВАНТАЖИВ(ЛА) БЕЗ ВОДЯНИХ ЗНАКІВ?</b> ⚡️\n\nЗначить, бот працює для тебе. Допоможи йому працювати далі — <b>донат від 10 ⭐</b> допоможе оплатити сервери! 🖥💛\n\n👇 <b>ПІДТРИМАТИ ПРОЄКТ</b>",
        "⚡️ <b>СУ БЕЛГІСІЗ ЖҮКТЕП АЛДЫҢЫЗ БА?</b> ⚡️\n\nДемек, бот сіз үшін жұмыс істейді. Оған жұмысын жалғастыруға көмектесіңіз — <b>10 ⭐-дан бастап донат</b> серверлерді төлеуге көмектеседі! 🖥💛\n\n👇 <b>ЖОБАНЫ ҚОЛДАУ</b>",
        "⚡️ <b>SUV BELGISIZ YUKLAB OLDINGIZMI?</b> ⚡️\n\nDemak, bot siz uchun ishlayapti. Unga ishlashda davom etishga yordam bering — <b>10 ⭐ dan boshlab xayriya</b> serverlar uchun toʻlashga yordam beradi! 🖥💛\n\n👇 <b>LOYIHANI QOʻLLAB-QUVVATLASH</b>",
        "⚡️ <b>СУУ БЕЛГИСИЗ ЖҮКТӨП АЛДЫҢЫЗБЫ?</b> ⚡️\n\nДемек, бот сиз үчүн иштеп жатат. Ага иштеп турууга жардам бериңиз — <b>10 ⭐дан баштап донат</b> серверлерди төлөөгө жардам берет! 🖥💛\n\n👇 <b>ДОЛБООРДУ КОЛДОО</b>",
    ),
    _d(
        "🔔 <b>ЭЙ, ТЫ! ДА, ТЫ!</b> 🔔\n\nТы пользуешься ботом — и это круто. Но серверы стоят денег, а бот остаётся <b>БЕЗ РЕКЛАМЫ</b>. Поддержи донатом — и так будет всегда! 🚫📢💛\n\n👇 <b>ЗАДОНАТИТЬ</b>",
        "🔔 <b>HEY, YOU! YES, YOU!</b> 🔔\n\nYou use the bot — and that's great. But servers cost money, and the bot stays <b>AD-FREE</b>. Support it with a donation — and it'll stay that way! 🚫📢💛\n\n👇 <b>DONATE</b>",
        "🔔 <b>ЕЙ, ТИ! ТАК, ТИ!</b> 🔔\n\nТи користуєшся ботом — і це круто. Але сервери коштують грошей, а бот залишається <b>БЕЗ РЕКЛАМИ</b>. Підтримай донатом — і так буде завжди! 🚫📢💛\n\n👇 <b>ЗАДОНАТИТИ</b>",
        "🔔 <b>ЭЙ, СІЗ! ИӘ, СІЗ!</b> 🔔\n\nСіз ботты пайдаланасыз — бұл тамаша. Бірақ серверлер ақшаға тұрады, ал бот <b>ЖАРНАМАСЫЗ</b> қалады. Донатпен қолдаңыз — солай болып қала береді! 🚫📢💛\n\n👇 <b>ДОНАТ ЖАСАУ</b>",
        "🔔 <b>HOY, SIZ! HA, SIZ!</b> 🔔\n\nSiz botdan foydalanasiz — bu ajoyib. Lekin serverlar pul turadi, bot esa <b>REKLAMASIZ</b> qoladi. Xayriya bilan qoʻllab-quvvatlang — shunday boʻlib qoladi! 🚫📢💛\n\n👇 <b>XAYRIYA QILISH</b>",
        "🔔 <b>ЭЙ, СИЗ! ООБА, СИЗ!</b> 🔔\n\nСиз ботту колдонуп жатасыз — бул сонун. Бирок серверлер акчага турат, ал эми бот <b>РЕКЛАМАСЫЗ</b> калат. Донат менен колдоңуз — ушундай боло берет! 🚫📢💛\n\n👇 <b>ДОНАТ ЖАСОО</b>",
    ),
    _d(
        "🏆 <b>СТАНЬ ЛЕГЕНДОЙ ПРОЕКТА!</b> 🏆\n\nТе, кто донатит, делают TikSaves быстрее и стабильнее. Присоединяйся: ⭐ Stars, 🏦 любой банк (СБП) или 💳 Donation Alerts! 🚀\n\n👇 <b>ЖМИ — ЭТО БЫСТРО</b>",
        "🏆 <b>BECOME A LEGEND OF THE PROJECT!</b> 🏆\n\nThose who donate make TikSaves faster and more stable. Join in: ⭐ Stars, 🏦 any bank (SBP) or 💳 Donation Alerts! 🚀\n\n👇 <b>TAP — IT'S QUICK</b>",
        "🏆 <b>СТАНЬ ЛЕГЕНДОЮ ПРОЄКТУ!</b> 🏆\n\nТі, хто донатить, роблять TikSaves швидшим і стабільнішим. Приєднуйся: ⭐ Stars, 🏦 будь-який банк (СБП) або 💳 Donation Alerts! 🚀\n\n👇 <b>НАТИСКАЙ — ЦЕ ШВИДКО</b>",
        "🏆 <b>ЖОБАНЫҢ ЖҰЛДЫЗЫНА АЙНАЛЫҢЫЗ!</b> 🏆\n\nДонат жасағандар TikSaves-ті жылдамырақ әрі тұрақтырақ етеді. Қосылыңыз: ⭐ Stars, 🏦 кез келген банк (СБП) немесе 💳 Donation Alerts! 🚀\n\n👇 <b>БАСЫҢЫЗ — БҰЛ ЖЫЛДАМ</b>",
        "🏆 <b>LOYIHA AFSONASIGA AYLANING!</b> 🏆\n\nXayriya qilganlar TikSaves-ni tezroq va barqarorroq qiladi. Qoʻshiling: ⭐ Stars, 🏦 istalgan bank (SBP) yoki 💳 Donation Alerts! 🚀\n\n👇 <b>BOSING — BU TEZ</b>",
        "🏆 <b>ДОЛБООРДУН ЛЕГЕНДАСЫНА АЙЛАНЫҢЫЗ!</b> 🏆\n\nДонат кылгандар TikSaves'ти ылдамыраак жана туруктуураак кылат. Кошулуңуз: ⭐ Stars, 🏦 каалаган банк (СБП) же 💳 Donation Alerts! 🚀\n\n👇 <b>БАСЫҢЫЗ — БУЛ ТЕЗ</b>",
    ),
]

# ------------------------------------------------------------------ промо Premium и напоминание про поддержку
PREMIUM_NUDGE = _d(
    "💎 <b>ХОЧЕШЬ БЕЗ ЭТИХ СООБЩЕНИЙ?</b> 💎\n\nБери <b>PREMIUM</b>: 🔕 никаких напоминаний, ⚡ лимиты ×{m}, 🛡 мягкий антифлуд и значок 💎 — всего за ⭐ Stars!\n\n👇 <b>ПОДРОБНЕЕ</b>",
    "💎 <b>WANT NO MORE OF THESE MESSAGES?</b> 💎\n\nGet <b>PREMIUM</b>: 🔕 no reminders, ⚡ limits ×{m}, 🛡 softer anti-flood and a 💎 badge — just for ⭐ Stars!\n\n👇 <b>LEARN MORE</b>",
    "💎 <b>ХОЧЕШ БЕЗ ЦИХ ПОВІДОМЛЕНЬ?</b> 💎\n\nБери <b>PREMIUM</b>: 🔕 жодних нагадувань, ⚡ ліміти ×{m}, 🛡 м’який антифлуд і значок 💎 — лише за ⭐ Stars!\n\n👇 <b>ДОКЛАДНІШЕ</b>",
    "💎 <b>БҰЛ ХАБАРЛАМАЛАРСЫЗ ҚАЛАЙСЫЗ БА?</b> 💎\n\n<b>PREMIUM</b> алыңыз: 🔕 еске салулар жоқ, ⚡ лимиттер ×{m}, 🛡 жұмсақ флудқа қарсы жүйе және 💎 белгісі — тек ⭐ Stars-қа!\n\n👇 <b>ТОЛЫҒЫРАҚ</b>",
    "💎 <b>BU XABARLARSIZ XOHLAYSIZMI?</b> 💎\n\n<b>PREMIUM</b> oling: 🔕 eslatmalarsiz, ⚡ limitlar ×{m}, 🛡 yumshoq antiflud va 💎 belgisi — faqat ⭐ Stars evaziga!\n\n👇 <b>BATAFSIL</b>",
    "💎 <b>БУЛ КАБАРЛАРСЫЗ КАЛАЙСЫЗБЫ?</b> 💎\n\n<b>PREMIUM</b> алыңыз: 🔕 эскертмелерсиз, ⚡ лимиттер ×{m}, 🛡 жумшак антифлуд жана 💎 белгиси — болгону ⭐ Stars үчүн!\n\n👇 <b>КЕҢИРИ</b>",
)

SUPPORT_NUDGE = _d(
    "📌 <b>НЕ ЗАБЫВАЙ!</b>\n\nЧто-то не работает или есть идея? Команда <b>/support</b> — и админ ответит прямо в чате. 🙌",
    "📌 <b>DON'T FORGET!</b>\n\nSomething broken or have an idea? The <b>/support</b> command — and the admin will reply right in the chat. 🙌",
    "📌 <b>НЕ ЗАБУВАЙ!</b>\n\nЩось не працює або є ідея? Команда <b>/support</b> — і адмін відповість прямо в чаті. 🙌",
    "📌 <b>ЕСТЕН ШЫҒАРМАҢЫЗ!</b>\n\nБір нәрсе жұмыс істемей ме немесе идеяңыз бар ма? <b>/support</b> командасы — әкімші чатта жауап береді. 🙌",
    "📌 <b>ESDAN CHIQARMANG!</b>\n\nNimadir ishlamayaptimi yoki gʻoyangiz bormi? <b>/support</b> buyrugʻi — administrator chatda javob beradi. 🙌",
    "📌 <b>УНУТПАҢЫЗ!</b>\n\nБир нерсе иштебей жатабы же идеяңыз барбы? <b>/support</b> буйругу — администратор чатта жооп берет. 🙌",
)

# ------------------------------------------------------------------ шаблоны рассылок для админ-меню
_DONATE_BROADCAST = _d(
    "🔥🔥🔥 <b>ВСЕМ, КТО КАЧАЕТ В TIKSAVES!</b> 🔥🔥🔥\n\nБот <b>БЕСПЛАТНЫЙ</b> — но серверы, хостинг и трафик стоят денег, и держатся они на донатах! 💸\n\n💛 Хочешь, чтобы бот работал быстро и без рекламы? <b>ЗАДОНАТЬ ПРЯМО СЕЙЧАС</b> — хоть <b>10 ⭐</b>:\n• ⭐ Telegram Stars\n• 🏦 Любой банк по СБП (для РФ)\n• 💳 Donation Alerts\n\n👉 Команда <b>/donate</b> — и готово за 10 секунд.\n<b>СПАСИБО, ЧТО ВЫ С НАМИ!</b> 🙏🚀",
    "🔥🔥🔥 <b>TO EVERYONE WHO DOWNLOADS WITH TIKSAVES!</b> 🔥🔥🔥\n\nThe bot is <b>FREE</b> — but servers, hosting and traffic cost money, and they're kept alive by donations! 💸\n\n💛 Want the bot to stay fast and ad-free? <b>DONATE RIGHT NOW</b> — even <b>10 ⭐</b>:\n• ⭐ Telegram Stars\n• 🏦 Any bank via SBP (for Russia)\n• 💳 Donation Alerts\n\n👉 The <b>/donate</b> command — and it's done in 10 seconds.\n<b>THANK YOU FOR BEING WITH US!</b> 🙏🚀",
    "🔥🔥🔥 <b>УСІМ, ХТО КАЧАЄ В TIKSAVES!</b> 🔥🔥🔥\n\nБот <b>БЕЗКОШТОВНИЙ</b> — але сервери, хостинг і трафік коштують грошей, і тримаються вони на донатах! 💸\n\n💛 Хочеш, щоб бот працював швидко й без реклами? <b>ЗАДОНАТЬ ПРЯМО ЗАРАЗ</b> — хоч <b>10 ⭐</b>:\n• ⭐ Telegram Stars\n• 🏦 Будь-який банк через СБП (для РФ)\n• 💳 Donation Alerts\n\n👉 Команда <b>/donate</b> — і готово за 10 секунд.\n<b>ДЯКУЄМО, ЩО ВИ З НАМИ!</b> 🙏🚀",
    "🔥🔥🔥 <b>TIKSAVES АРҚЫЛЫ ЖҮКТЕЙТІНДЕРДІҢ БӘРІНЕ!</b> 🔥🔥🔥\n\nБот <b>ТЕГІН</b> — бірақ серверлер, хостинг және трафик ақшаға тұрады, олар донаттармен ұсталады! 💸\n\n💛 Бот жылдам және жарнамасыз жұмыс істесін десеңіз? <b>ДӘЛ ҚАЗІР ДОНАТ ЖАСАҢЫЗ</b> — кем дегенде <b>10 ⭐</b>:\n• ⭐ Telegram Stars\n• 🏦 Кез келген банк СБП арқылы (РФ үшін)\n• 💳 Donation Alerts\n\n👉 <b>/donate</b> командасы — 10 секундта дайын.\n<b>БІЗБЕН БІРГЕ БОЛҒАНЫҢЫЗ ҮШІН РАХМЕТ!</b> 🙏🚀",
    "🔥🔥🔥 <b>TIKSAVES ORQALI YUKLAYDIGANLARNING HAMMASIGA!</b> 🔥🔥🔥\n\nBot <b>TEKIN</b> — lekin serverlar, hosting va trafik pul turadi, ular xayriyalar hisobiga ushlanadi! 💸\n\n💛 Bot tez va reklamasiz ishlashini xohlaysizmi? <b>HOZIROQ XAYRIYA QILING</b> — hech boʻlmasa <b>10 ⭐</b>:\n• ⭐ Telegram Stars\n• 🏦 Istalgan bank SBP orqali (RF uchun)\n• 💳 Donation Alerts\n\n👉 <b>/donate</b> buyrugʻi — 10 soniyada tayyor.\n<b>BIZ BILAN BOʻLGANINGIZ UCHUN RAHMAT!</b> 🙏🚀",
    "🔥🔥🔥 <b>TIKSAVES МЕНЕН ЖҮКТӨГӨНДӨРДҮН БААРЫНА!</b> 🔥🔥🔥\n\nБот <b>АКЫСЫЗ</b> — бирок серверлер, хостинг жана трафик акчага турат, алар донаттар менен кармалат! 💸\n\n💛 Бот ылдам жана рекламасыз иштесин десеңиз? <b>ДАЛ АЗЫР ДОНАТ КЫЛЫҢЫЗ</b> — жок дегенде <b>10 ⭐</b>:\n• ⭐ Telegram Stars\n• 🏦 Каалаган банк СБП аркылуу (РФ үчүн)\n• 💳 Donation Alerts\n\n👉 <b>/donate</b> буйругу — 10 секундда даяр.\n<b>БИЗ МЕНЕН БОЛГОНУҢУЗ ҮЧҮН РАХМАТ!</b> 🙏🚀",
)

_PREMIUM_BROADCAST = _d(
    "💎 <b>ВСТРЕЧАЙТЕ: TIKSAVES PREMIUM!</b> 💎\n\n🔕 Никаких напоминаний о донате\n⚡ Лимиты ×{m}\n🛡 Мягкий антифлуд\n💎 Значок в /me\n\nОплата Telegram Stars прямо в боте: <b>/donate</b> → <b>💎 Premium</b>. 🚀",
    "💎 <b>MEET TIKSAVES PREMIUM!</b> 💎\n\n🔕 No donation reminders\n⚡ Limits ×{m}\n🛡 Softer anti-flood\n💎 A badge in /me\n\nPay with Telegram Stars right in the bot: <b>/donate</b> → <b>💎 Premium</b>. 🚀",
    "💎 <b>ЗУСТРІЧАЙТЕ: TIKSAVES PREMIUM!</b> 💎\n\n🔕 Жодних нагадувань про донат\n⚡ Ліміти ×{m}\n🛡 М’який антифлуд\n💎 Значок у /me\n\nОплата Telegram Stars прямо в боті: <b>/donate</b> → <b>💎 Premium</b>. 🚀",
    "💎 <b>КЕЗДЕСІҢІЗ: TIKSAVES PREMIUM!</b> 💎\n\n🔕 Донат туралы еске салулар жоқ\n⚡ Лимиттер ×{m}\n🛡 Жұмсақ флудқа қарсы жүйе\n💎 /me ішінде белгі\n\nТөлем Telegram Stars арқылы тікелей ботта: <b>/donate</b> → <b>💎 Premium</b>. 🚀",
    "💎 <b>TANISHING: TIKSAVES PREMIUM!</b> 💎\n\n🔕 Xayriya haqida eslatmalarsiz\n⚡ Limitlar ×{m}\n🛡 Yumshoq antiflud\n💎 /me da belgi\n\nToʻlov Telegram Stars orqali bevosita botda: <b>/donate</b> → <b>💎 Premium</b>. 🚀",
    "💎 <b>ТАНЫШЫҢЫЗ: TIKSAVES PREMIUM!</b> 💎\n\n🔕 Донат жөнүндө эскертмелерсиз\n⚡ Лимиттер ×{m}\n🛡 Жумшак антифлуд\n💎 /me ичинде белги\n\nТөлөм Telegram Stars аркылуу түз ботто: <b>/donate</b> → <b>💎 Premium</b>. 🚀",
)


def _fill(d: dict) -> dict:
    return {lg: t.replace("{m}", str(PREMIUM_LIMIT_MULT)) for lg, t in d.items()}


# id -> (подпись кнопки в админ-меню, тексты по языкам)
BROADCAST_PRESETS = {
    "donate": ("🔥 Донат (кричащая)", _fill(_DONATE_BROADCAST)),
    "premium": ("💎 Premium", _fill(_PREMIUM_BROADCAST)),
}

# Все тексты, которым нужны переводы: [{ru, en, uk, kk, uz, ky}, ...]
ALL_TRANSLATED = [*DONATE_NUDGES, PREMIUM_NUDGE, SUPPORT_NUDGE, *(v[1] for v in BROADCAST_PRESETS.values())]
