import unittest
import stubs

stubs.install()
from ui import keyboards  # noqa: E402
import i18n  # noqa: E402


class DonateTests(unittest.TestCase):
    def test_rub_screen_translated_everywhere(self):
        i18n._ensure_loaded()
        for lang in ("en", "uk", "kk", "uz", "ky"):
            tr = i18n.TRANSLATIONS[lang]
            self.assertIn(keyboards.RUB_DONATE_TEXT, tr, lang)
            self.assertIn("🇷🇺 Донат рублями (для РФ)", tr, lang)
            self.assertIn("🏦 Ozon Банк (СБП)", tr, lang)

    def test_main_menu_has_rub_tab(self):
        kb = keyboards.donate_main_kb("ru")
        datas = [getattr(b, "callback_data", None) for row in kb.inline_keyboard for b in row]
        self.assertIn("donate:rub", datas)

    def test_rub_kb_ozon_link_and_back(self):
        kb = keyboards.rub_donate_kb("ru")
        urls = [getattr(b, "url", None) for row in kb.inline_keyboard for b in row]
        self.assertTrue(any(u and u.startswith("https://finance.ozon.ru/apps/sbp/ozonbankpay/") for u in urls))
        datas = [getattr(b, "callback_data", None) for row in kb.inline_keyboard for b in row]
        self.assertIn("donate:back", datas)


if __name__ == "__main__":
    unittest.main()


class OwnerGifts(unittest.TestCase):
    def test_gift_list_loaded_and_menu_is_two_columns(self):
        from core import owner_gifts as og
        gifts = og.gifts()
        self.assertEqual(len(gifts), 16)
        self.assertEqual(len([g for g in gifts if g["gift_id"]]), 11)
        kb = og.list_kb("ru")
        self.assertTrue(all(len(r) <= 2 for r in kb.inline_keyboard))
        datas = [b.callback_data for r in kb.inline_keyboard for b in r]
        self.assertIn("og:pick:tg_champagne", datas)
        self.assertTrue(all(len(d.encode()) <= 64 for d in datas))
