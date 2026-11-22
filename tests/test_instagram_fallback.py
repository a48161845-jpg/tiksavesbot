import unittest
import stubs

stubs.install()
from downloaders import platform_fallbacks as pf  # noqa: E402
from i18n import error_explain as ee  # noqa: E402


class InstagramParsing(unittest.TestCase):
    def test_shortcode(self):
        self.assertEqual(pf.instagram_shortcode("https://www.instagram.com/reel/DfMb5u8Kg1a/?exln=M2NkcTNzM25zMXMx"), ("reel", "DfMb5u8Kg1a"))
        self.assertEqual(pf.instagram_shortcode("https://www.instagram.com/reels/DeauKOmv4qw/?srtk=x"), ("reel", "DeauKOmv4qw"))
        self.assertEqual(pf.instagram_shortcode("https://www.instagram.com/p/DfjCwVUCBRn/?srtk=MWpt"), ("p", "DfjCwVUCBRn"))
        self.assertEqual(pf.instagram_shortcode("https://instagram.com/someuser/reel/AbC_d-1/"), ("reel", "AbC_d-1"))
        self.assertIsNone(pf.instagram_shortcode("https://www.instagram.com/someuser/"))

    def test_has_fallback(self):
        self.assertTrue(pf.has_fallback("https://www.instagram.com/reel/DfMb5u8Kg1a/"))

    def test_video_url_double_escaped_json(self):
        html = r'<script>x = "{\"shortcode_media\":{\"video_url\":\"https:\/\/scontent.cdninstagram.com\/v\/t50\/a.mp4?efg=abc\u0026oe=1\",\"x\":1}}";</script>'
        self.assertEqual(pf.ig_video_from_html(html), "https://scontent.cdninstagram.com/v/t50/a.mp4?efg=abc&oe=1")

    def test_video_url_plain_json(self):
        html = '{"video_url":"https:\\/\\/a.example\\/v.mp4?x=1\\u0026y=2","other":1}'
        self.assertEqual(pf.ig_video_from_html(html), "https://a.example/v.mp4?x=1&y=2")

    def test_og_video_mirror(self):
        html = '<meta property="og:video" content="https://cdn.example/v.mp4?a=1&amp;b=2">'
        self.assertEqual(pf.ig_video_from_html(html), "https://cdn.example/v.mp4?a=1&b=2")

    def test_video_tag(self):
        html = '<video class="Video" src="https://cdn.example/clip.mp4?z=1&amp;q=2"></video>'
        self.assertEqual(pf.ig_video_from_html(html), "https://cdn.example/clip.mp4?z=1&q=2")

    def test_photo_post_has_no_video(self):
        self.assertIsNone(pf.ig_video_from_html('<meta property="og:image" content="https://cdn.example/p.jpg">'))

    def test_rate_limit_beats_login_hint(self):
        reason = ("ERROR: [Instagram] X: Unable to download webpage: HTTP Error 429: Too Many Requests "
                  "| fallback: Instagram fallback не сработал: embed: HTTP 429; use --cookies")
        self.assertEqual(ee.classify(reason, "instagram", "https://www.instagram.com/reel/X/"), "rate_limit")


if __name__ == "__main__":
    unittest.main()
