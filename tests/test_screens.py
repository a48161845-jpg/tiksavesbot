import re
import unittest
import stubs

stubs.install()
import i18n  # noqa: E402
from ui import keyboards as K  # noqa: E402
from core import config as C  # noqa: E402

LANGS = ("en", "uk", "kk", "uz", "ky")


def _shape(t: str):
    """Разметка и подстановки, которые обязаны совпасть у оригинала и перевода."""
    return (
        t.count("<b>"), t.count("</b>"), t.count("<blockquote>"), t.count("</blockquote>"),
        t.count("<code>"), t.count("\n"), sorted(re.findall(r"\{\w+\}", t)),
        re.findall(r"^\W*", t.replace("<b>", "").replace("<blockquote>", ""))[0],  # стартовый эмодзи
    )


def _screens():
    items = [K.START_TEXT, K.HELP_TEXT, K.DONATE_TEXT, K.STARS_MENU_TEXT, K.RUB_DONATE_TEXT, K.SUPPORT_TEXT,
             K.SUPPORT_SENT_TEXT, K.SUPPORT_TIMEOUT_TEXT, K.PHOTO_CHOICE_TEXT, K.QUALITY_CHOICE_TEXT,
             C.CAPTION_VIDEO, C.CAPTION_PHOTO, C.CAPTION_AUDIO, C.MSG_SPAM, C.PHOTO_WARNING_TEXT]
    items += list(K.HELP_SECTIONS.values())
    return items


class Screens(unittest.TestCase):
    def test_every_screen_translated_with_same_markup(self):
        i18n._ensure_loaded()
        for lang in LANGS:
            for ru in _screens():
                tx = i18n.TRANSLATIONS[lang].get(ru)
                self.assertTrue(tx, f"{lang}: нет перевода для {ru[:40]!r}")
                self.assertEqual(_shape(ru), _shape(tx), f"{lang}: разметка не совпала для {ru[:40]!r}")

    def test_help_buttons_translated(self):
        i18n._ensure_loaded()
        for lang in LANGS:
            for ru in ("🎬 Видео", "🖼 Фото", "👥 Группы", "📳 Inline", "⏱ Лимиты"):
                self.assertIn(ru, i18n.TRANSLATIONS[lang])

    def test_help_has_groups_section_and_button(self):
        self.assertIn("groups", K.HELP_SECTIONS)
        datas = [b.callback_data for row in K.help_kb("ru").inline_keyboard for b in row]
        self.assertIn("help:groups", datas)
        for key in K.HELP_SECTIONS:
            self.assertIn(f"help:{key}", datas)

    def test_screens_fit_telegram_message_limit(self):
        from ui.screens_text import PHRASES, build
        for lang in PHRASES:
            for sid, text in build(lang).items():
                self.assertLess(len(text), 3900, f"{lang}/{sid}: {len(text)} символов")

    def test_screens_are_informative(self):
        """Экраны не должны снова «пустеть»: минимальная длина русских текстов."""
        self.assertGreater(len(K.START_TEXT), 600)
        for key, minimum in (("video", 450), ("photo", 600), ("groups", 350), ("limits", 400), ("inline", 450)):
            self.assertGreater(len(K.HELP_SECTIONS[key]), minimum, key)
        for ru in (K.DONATE_TEXT, K.STARS_MENU_TEXT, K.RUB_DONATE_TEXT, K.SUPPORT_TEXT):
            self.assertGreater(len(ru), 250)

    def test_no_heavy_dividers_left(self):
        for ru in _screens():
            self.assertNotIn("━━", ru)

    def test_format_placeholders_work(self):
        self.assertIn("5", i18n.tr("en", C.MSG_SPAM, n=5))
        self.assertIn("100", i18n.tr("uk", K.STARS_MENU_TEXT, a=100, b=5000))


if __name__ == "__main__":
    unittest.main()
