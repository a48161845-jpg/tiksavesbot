import unittest
import stubs

stubs.install()
from i18n import error_explain as ee  # noqa: E402

# Реальные формулировки из логов бота
CASES = [
    ("API error: {'type': 'https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-502/', 'title': 'Error 502: Bad gateway'", "provider_down"),
    ("API error: {'title': 'Error 522: Connection timed out', 'status': 522, 'detail': 'Cloudflare coul", "provider_down"),
    ("Download failed after retries: 403, message='Forbidden', url='https://v16-webapp-prime.tiktok.com/video/tos/x'", "cdn_forbidden"),
    ("ERROR: [TikTok] 1: Your IP address is blocked from accessing this post", "ip_blocked"),
    ("yt-dlp: нет видеоформатов (18+/закрытый пост?) | fallback: api.vxtwitter.com: HTTP 403", "restricted"),
]


class Classify(unittest.TestCase):
    def test_real_log_reasons(self):
        for text, code in CASES:
            self.assertEqual(ee.classify(text), code, text[:60])

    def test_new_codes_have_all_texts(self):
        for code in ("provider_down", "cdn_forbidden"):
            self.assertEqual(len(ee._TEXTS[code]), 4)

    def test_every_rule_has_texts(self):
        for code, _needles in ee._RULES:
            self.assertIn(code, ee._TEXTS, code)


if __name__ == "__main__":
    unittest.main()
