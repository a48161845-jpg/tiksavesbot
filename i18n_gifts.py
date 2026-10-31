"""Переводы для подарков владельцу бота (owner_gifts.py). Подгружается из i18n._ensure_loaded()."""

SEP = "━━━━━━━━━━━━━━━━━━━━"


def register_gifts(_reg) -> None:
    import owner_gifts as og

    _reg(og.B_GIFT_MENU, "🎁 Send a gift", "🎁 Подарувати подарунок", "🎁 Сыйлық жасау", "🎁 Sovg‘a qilish", "🎁 Белек берүү")

    _reg(og.S_LIST,
         f"🎁 <b>Gift to the bot owner</b>\n{SEP}\n\nWant to make the author happy? Pick a gift — it's paid with Stars ⭐ and will arrive in the owner's private messages.\n\nℹ️ Bot administration may see the sender in service logs, even if you choose «anonymous».\n\nPick a gift 👇",
         f"🎁 <b>Подарунок власнику бота</b>\n{SEP}\n\nХочеш потішити автора? Обери подарунок — він оплачується зірками ⭐ і прийде власнику в особисті повідомлення.\n\nℹ️ Адміністрація бота може бачити відправника в службових логах, навіть якщо ти обереш «анонімно».\n\nОбери подарунок 👇",
         f"🎁 <b>Бот иесіне сыйлық</b>\n{SEP}\n\nАвторды қуантқыңыз келе ме? Сыйлық таңдаңыз — ол жұлдыздармен ⭐ төленеді және иесіне жеке хабарламамен жетеді.\n\nℹ️ «Анонимді» таңдасаңыз да, бот әкімшілігі қызметтік логтарда жіберушіні көре алады.\n\nСыйлық таңдаңыз 👇",
         f"🎁 <b>Bot egasiga sovg‘a</b>\n{SEP}\n\nMuallifni xursand qilmoqchimisiz? Sovg‘ani tanlang — u yulduzlar ⭐ bilan to‘lanadi va egasiga shaxsiy xabarda yetib boradi.\n\nℹ️ «Anonim»ni tanlasangiz ham, bot ma’muriyati xizmat loglarida jo‘natuvchini ko‘rishi mumkin.\n\nSovg‘ani tanlang 👇",
         f"🎁 <b>Бот ээсине белек</b>\n{SEP}\n\nАвторду кубандыргыңыз келеби? Белек тандаңыз — ал жылдыздар ⭐ менен төлөнөт жана ээсине жеке билдирүү менен жетет.\n\nℹ️ «Анонимдүү» тандасаңыз да, бот администрациясы кызматтык логдордо жөнөтүүчүнү көрүшү мүмкүн.\n\nБелек тандаңыз 👇")

    _reg(og.S_EMPTY,
         "🎁 No gifts have been added yet — check back later.",
         "🎁 Подарунків поки немає — зазирни пізніше.",
         "🎁 Сыйлықтар әлі қосылмаған — кейінірек кіріңіз.",
         "🎁 Sovg‘alar hali qo‘shilmagan — keyinroq kiring.",
         "🎁 Белектер азырынча кошула элек — кийинчерээк кириңиз.")

    _reg(og.S_ANON,
         "{emoji} <b>{name}</b> — {price} ⭐\n\nHow do you want to send the gift?\n\n🕶 <b>Anonymously</b> — your name won't be shown in the gift\n👤 <b>From my name</b> — the owner will see who sent it",
         "{emoji} <b>{name}</b> — {price} ⭐\n\nЯк надіслати подарунок?\n\n🕶 <b>Анонімно</b> — ім’я не буде вказано в подарунку\n👤 <b>Від мого імені</b> — власник побачить, хто подарував",
         "{emoji} <b>{name}</b> — {price} ⭐\n\nСыйлықты қалай жіберу керек?\n\n🕶 <b>Анонимді</b> — сыйлықта атыңыз көрсетілмейді\n👤 <b>Өз атымнан</b> — иесі кім сыйлағанын көреді",
         "{emoji} <b>{name}</b> — {price} ⭐\n\nSovg‘ani qanday yuborasiz?\n\n🕶 <b>Anonim</b> — sovg‘ada ismingiz ko‘rsatilmaydi\n👤 <b>Mening ismimdan</b> — egasi kim sovg‘a qilganini ko‘radi",
         "{emoji} <b>{name}</b> — {price} ⭐\n\nБелекти кантип жөнөтөсүз?\n\n🕶 <b>Анонимдүү</b> — белекте атыңыз көрсөтүлбөйт\n👤 <b>Өз атымдан</b> — ээси ким белек бергенин көрөт")

    _reg(og.S_TEXT, "💌 <b>Add a message to the gift?</b>", "💌 <b>Додати повідомлення до подарунка?</b>",
         "💌 <b>Сыйлыққа хабарлама қосасыз ба?</b>", "💌 <b>Sovg‘aga xabar qo‘shasizmi?</b>", "💌 <b>Белекке билдирүү кошосузбу?</b>")

    _reg(og.S_ASK_TEXT,
         "✍️ Write the text for the gift in one message (up to {n} characters).\n\nTo cancel, use the button below.",
         "✍️ Напиши текст до подарунка одним повідомленням (до {n} символів).\n\nСкасувати — кнопка нижче.",
         "✍️ Сыйлыққа мәтінді бір хабарламамен жазыңыз ({n} таңбаға дейін).\n\nБолдырмау — төмендегі түйме.",
         "✍️ Sovg‘a uchun matnni bitta xabarda yozing ({n} belgigacha).\n\nBekor qilish — pastdagi tugma.",
         "✍️ Белекке текстти бир билдирүү менен жазыңыз ({n} белгиге чейин).\n\nЖокко чыгаруу — төмөнкү баскыч.")

    _reg(og.S_TEXT_LONG,
         "❌ Too long: {n} characters maximum. Shorten it and send again.",
         "❌ Занадто довго: максимум {n} символів. Скороти й надішли ще раз.",
         "❌ Тым ұзын: ең көбі {n} таңба. Қысқартып, қайта жіберіңіз.",
         "❌ Juda uzun: ko‘pi bilan {n} belgi. Qisqartirib, qayta yuboring.",
         "❌ Өтө узун: эң көбү {n} белги. Кыскартып, кайра жөнөтүңүз.")

    _reg(og.S_CONFIRM,
         "🎁 <b>Check your gift</b>\n" + SEP + "\n\n{emoji} <b>{name}</b> — {price} ⭐\n👤 From: <b>{sender}</b>\n💌 Text: {text}\n\nAll correct? Tap «Pay».",
         "🎁 <b>Перевір подарунок</b>\n" + SEP + "\n\n{emoji} <b>{name}</b> — {price} ⭐\n👤 Від кого: <b>{sender}</b>\n💌 Текст: {text}\n\nВсе вірно? Натисни «Сплатити».",
         "🎁 <b>Сыйлықты тексеріңіз</b>\n" + SEP + "\n\n{emoji} <b>{name}</b> — {price} ⭐\n👤 Кімнен: <b>{sender}</b>\n💌 Мәтін: {text}\n\nБәрі дұрыс па? «Төлеу» түймесін басыңыз.",
         "🎁 <b>Sovg‘ani tekshiring</b>\n" + SEP + "\n\n{emoji} <b>{name}</b> — {price} ⭐\n👤 Kimdan: <b>{sender}</b>\n💌 Matn: {text}\n\nHammasi to‘g‘rimi? «To‘lash»ni bosing.",
         "🎁 <b>Белегиңизди текшериңиз</b>\n" + SEP + "\n\n{emoji} <b>{name}</b> — {price} ⭐\n👤 Кимден: <b>{sender}</b>\n💌 Текст: {text}\n\nБардыгы туурабы? «Төлөө» баскычын басыңыз.")

    _reg(og.S_WHO_ANON, "🕶 anonymously", "🕶 анонімно", "🕶 анонимді", "🕶 anonim", "🕶 анонимдүү")
    _reg(og.S_WHO_NAMED, "👤 from my name", "👤 від мого імені", "👤 өз атымнан", "👤 mening ismimdan", "👤 өз атымдан")
    _reg(og.S_NO_TEXT, "— no text —", "— без тексту —", "— мәтінсіз —", "— matnsiz —", "— тексти жок —")
    _reg(og.S_CANCELLED, "❌ Cancelled.", "❌ Скасовано.", "❌ Болдырылмады.", "❌ Bekor qilindi.", "❌ Жокко чыгарылды.")
    _reg(og.S_EXPIRED,
         "⌛ The gift selection has expired — open /donate and start again.",
         "⌛ Вибір подарунка застарів — відкрий /donate і почни знову.",
         "⌛ Сыйлық таңдау мерзімі өтті — /donate ашып, қайта бастаңыз.",
         "⌛ Sovg‘a tanlash eskirdi — /donate ni ochib, qaytadan boshlang.",
         "⌛ Белек тандоо эскирди — /donate ачып, кайра баштаңыз.")
    _reg(og.S_PAID_OK,
         "✅ <b>Gift sent!</b> 🎁\n\nThank you — the owner will be happy 💛",
         "✅ <b>Подарунок надіслано!</b> 🎁\n\nДякуємо — власнику буде приємно 💛",
         "✅ <b>Сыйлық жіберілді!</b> 🎁\n\nРахмет — иесі қуанады 💛",
         "✅ <b>Sovg‘a yuborildi!</b> 🎁\n\nRahmat — egasi xursand bo‘ladi 💛",
         "✅ <b>Белек жөнөтүлдү!</b> 🎁\n\nРахмат — ээси кубанат 💛")
    _reg(og.S_PAID_LOST,
         "⚠️ Payment received, but the gift data was lost. Write to /support and we'll sort it out.",
         "⚠️ Оплату отримано, але дані подарунка втрачено. Напиши в /support — розберемося.",
         "⚠️ Төлем алынды, бірақ сыйлық деректері жоғалды. /support бөліміне жазыңыз — анықтаймыз.",
         "⚠️ To‘lov olindi, lekin sovg‘a ma’lumotlari yo‘qolgan. /support ga yozing — hal qilamiz.",
         "⚠️ Төлөм алынды, бирок белек маалыматы жоголгон. /support бөлүмүнө жазыңыз — чечебиз.")
    _reg(og.S_OWNER_CARD,
         "🎁 <b>You have a gift!</b>\n" + SEP + "\n\n{emoji} <b>{name}</b> · {price} ⭐\n👤 From: {sender}",
         "🎁 <b>Вам подарунок!</b>\n" + SEP + "\n\n{emoji} <b>{name}</b> · {price} ⭐\n👤 Від: {sender}",
         "🎁 <b>Сізге сыйлық!</b>\n" + SEP + "\n\n{emoji} <b>{name}</b> · {price} ⭐\n👤 Кімнен: {sender}",
         "🎁 <b>Sizga sovg‘a!</b>\n" + SEP + "\n\n{emoji} <b>{name}</b> · {price} ⭐\n👤 Kimdan: {sender}",
         "🎁 <b>Сизге белек!</b>\n" + SEP + "\n\n{emoji} <b>{name}</b> · {price} ⭐\n👤 Кимден: {sender}")
    _reg(og.S_OWNER_ANON, "🕶 Anonymous", "🕶 Анонім", "🕶 Аноним", "🕶 Anonim", "🕶 Аноним")
    _reg(og.S_INV_DESC, "A gift for the bot owner", "Подарунок власнику бота", "Бот иесіне сыйлық", "Bot egasiga sovg‘a", "Бот ээсине белек")

    _reg(og.B_ANON, "🕶 Anonymously", "🕶 Анонімно", "🕶 Анонимді", "🕶 Anonim", "🕶 Анонимдүү")
    _reg(og.B_NAMED, "👤 From my name", "👤 Від мого імені", "👤 Өз атымнан", "👤 Mening ismimdan", "👤 Өз атымдан")
    _reg(og.B_ADD_TEXT, "✍️ Add text", "✍️ Додати текст", "✍️ Мәтін қосу", "✍️ Matn qo‘shish", "✍️ Текст кошуу")
    _reg(og.B_NO_TEXT, "➡️ No text", "➡️ Без тексту", "➡️ Мәтінсіз", "➡️ Matnsiz", "➡️ Текстсиз")
    _reg(og.B_BACK, "⬅️ Back", "⬅️ Назад", "⬅️ Артқа", "⬅️ Orqaga", "⬅️ Артка")
    _reg(og.B_CANCEL, "❌ Cancel", "❌ Скасувати", "❌ Болдырмау", "❌ Bekor qilish", "❌ Жокко чыгаруу")
    _reg(og.B_PAY, "⭐ Pay {price}", "⭐ Сплатити {price}", "⭐ Төлеу {price}", "⭐ To‘lash {price}", "⭐ Төлөө {price}")
    _reg("❌ Не получилось открыть оплату. Попробуй позже.",
         "❌ Couldn't open the payment. Try again later.",
         "❌ Не вдалося відкрити оплату. Спробуй пізніше.",
         "❌ Төлемді ашу мүмкін болмады. Кейінірек қайталаңыз.",
         "❌ To‘lovni ochib bo‘lmadi. Keyinroq urinib ko‘ring.",
         "❌ Төлөмдү ачуу мүмкүн болгон жок. Кийинчерээк аракет кылыңыз.")
