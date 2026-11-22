import unittest
import stubs

stubs.install()
from downloaders.providers import TikTokPageProvider, TikWMClient  # noqa: E402


class _M:
    def __init__(self, v): self.value = v


class _Jar:
    def filter_cookies(self, url): return {"tt_chain_token": _M("abc"), "other": _M("1")}


class _Sess:
    cookie_jar = _Jar()


class _Resp:
    url = "https://www.tiktok.com/@u/video/1"
    cookies = {"tt_csrf_token": _M("xyz"), "other": _M("2")}


class PageDownload(unittest.TestCase):
    def setUp(self):
        TikTokPageProvider._ctx.clear()
        self.p = TikTokPageProvider(_Sess())

    def test_cookie_header_merges_jar_and_response(self):
        h = TikTokPageProvider._cookie_header(_Resp(), _Sess())
        self.assertIn("tt_chain_token=abc", h)
        self.assertIn("tt_csrf_token=xyz", h)
        self.assertIn("other=2", h)  # свежее значение из ответа перекрывает jar

    def test_media_urls_get_browser_headers(self):
        hdr = {"User-Agent": "UA", "Referer": "https://www.tiktok.com/", "Cookie": "tt_chain_token=abc"}
        TikTokPageProvider._remember(["https://v16-webapp-prime.tiktok.com/v.mp4", None, "https://p/1.jpeg"], hdr, "http://proxy:1")
        got = self.p._dl_headers("https://v16-webapp-prime.tiktok.com/v.mp4")
        self.assertEqual(got["Referer"], "https://www.tiktok.com/")
        self.assertEqual(got["Cookie"], "tt_chain_token=abc")
        self.assertEqual(self.p._dl_proxy("https://p/1.jpeg"), "http://proxy:1")

    def test_unknown_url_uses_plain_headers(self):
        self.assertEqual(self.p._dl_headers("https://x/y.mp4"), TikWMClient._dl_headers(self.p, "https://x/y.mp4"))
        self.assertIsNone(self.p._dl_proxy("https://x/y.mp4"))

    def test_context_is_bounded(self):
        urls = [f"https://v/{i}.mp4" for i in range(TikTokPageProvider._CTX_MAX + 50)]
        TikTokPageProvider._remember(urls, {"User-Agent": "UA"}, None)
        self.assertEqual(len(TikTokPageProvider._ctx), TikTokPageProvider._CTX_MAX)
        self.assertNotIn(urls[0], TikTokPageProvider._ctx)
        self.assertIn(urls[-1], TikTokPageProvider._ctx)


if __name__ == "__main__":
    unittest.main()


class PageLanguage(unittest.TestCase):
    def test_no_forced_language_header_by_default(self):
        h = TikTokPageProvider._page_headers("UA")
        self.assertNotIn("Accept-Language", h)       # раньше было en-US -> TikTok мог отдать переведённую версию

    def test_language_can_be_set_explicitly(self):
        old = TikTokPageProvider.ACCEPT_LANGUAGE
        try:
            TikTokPageProvider.ACCEPT_LANGUAGE = "ru-RU,ru;q=0.9"
            self.assertEqual(TikTokPageProvider._page_headers("UA")["Accept-Language"], "ru-RU,ru;q=0.9")
        finally:
            TikTokPageProvider.ACCEPT_LANGUAGE = old

    def test_ytdlp_prefers_original_audio_track(self):
        from downloaders import youtube_provider as yp
        self.assertEqual(yp._FORMAT_SORT[0], "lang")
