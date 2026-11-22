import asyncio
import tempfile
import unittest
from pathlib import Path
import stubs

stubs.install()
from handlers import inline_handler as ih  # noqa: E402
from core import globals_state  # noqa: E402

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

URL = "https://www.tiktok.com/@user/photo/7686493651941215509"


class FakeStore:
    def __init__(self): self.cache, self.downloads = {}, []
    def get_ban(self, uid): return None
    def get_inline_cache(self, k): return self.cache.get(k)
    def set_inline_cache(self, key, file_id, kind="video", ids=None): self.cache[key] = {"file_id": file_id, "kind": kind, "ids": ids}
    def inc_download(self, *a, **k): self.downloads.append((a, k))
    def set_user_label(self, *a): pass


class FakeMedia:
    def __init__(self, photos): self.photos, self.video, self.live = photos, None, None


class FakeProvider:
    def __init__(self, bot): self.bot = bot
    async def download_to_file(self, url, path, max_bytes, stage):
        Image.new("RGB", (1080, 1920), (10, 120, 200)).save(path, "JPEG")


class FakeSwitcher:
    def __init__(self, provider, n): self.provider, self.n = provider, n
    async def get_media(self, url, raw_url=None):
        return FakeMedia([f"https://p/{i}.jpeg" for i in range(self.n)]), self.provider


class FakeBot:
    def __init__(self): self.sent = []
    async def send_photo(self, chat, path, **kw):
        with Image.open(path) as im:
            self.sent.append(im.size)
        n = len(self.sent)
        class _P:  # noqa: E306
            file_id = f"FID{n}"
        class _M:  # noqa: E306
            photo = [_P()]
            message_id = n
        return _M()
    async def delete_message(self, *a): pass


class FakeQuery:
    def __init__(self, text):
        self.query, self.answers = text, []
        class _U: id = 42  # noqa: E306
        self.from_user = _U()
        self.bot = None
    async def answer(self, results, **kw): self.answers.append((results, kw))


@unittest.skipIf(Image is None, "Pillow не установлен")
class InlinePhotos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._cwd = Path.cwd()
        import os
        os.chdir(self.tmp.name)
        self.bot = FakeBot()
        self.store = FakeStore()
        ih.store = self.store
        ih.FSInputFile = lambda p: p
        ih.INLINE_CACHE_CHANNEL_ID = -1001
        async def label(bot, uid): return "u"
        async def hooks(*a, **k): return None
        ih.resolve_user_label, ih.after_download_hooks = label, hooks
        ih._inflight.clear(); ih._failed.clear()
        provider = FakeProvider(self.bot)
        globals_state.g_provider = provider
        globals_state.g_switcher = FakeSwitcher(provider, 3)

    def tearDown(self):
        import os
        os.chdir(self._cwd)
        self.tmp.cleanup()

    def _ask(self, text):
        q = FakeQuery(text)
        asyncio.run(ih.inline_handler(q))
        return q.answers[-1]

    def test_format_suffix_parsing(self):
        self.assertEqual(ih.split_format(f"{URL} 4:3"), (URL, "4x3"))
        self.assertEqual(ih.split_format(f"{URL} 16x9"), (URL, "16x9"))
        self.assertEqual(ih.split_format(f"{URL}   9:16  "), (URL, "9x16"))
        self.assertEqual(ih.split_format(URL), (URL, "orig"))
        self.assertEqual(ih.split_format("https://x.com/a/status/11:1"), ("https://x.com/a/status/11:1", "orig"))

    def test_photo_post_returns_one_result_per_frame(self):
        results, kw = self._ask(URL)
        self.assertEqual([r.photo_file_id for r in results], ["FID1", "FID2", "FID3"])
        self.assertIn("1 из 3", results[0].title)
        self.assertEqual(self.bot.sent, [(1080, 1920)] * 3)          # оригинал не тронут
        self.assertEqual(self.store.downloads[0][0][1], "photo")

    def test_ratio_crops_frames_and_has_own_cache(self):
        results, _ = self._ask(URL + " 1:1")
        self.assertEqual(self.bot.sent, [(1080, 1080)] * 3)
        self.assertTrue(all("1:1" in r.title for r in results))
        # оригинал в кэше не появился — у каждого формата свой набор
        self.assertIn(ih._photo_key(URL, "1x1"), self.store.cache)
        self.assertNotIn(ih._photo_key(URL, "orig"), self.store.cache)

    def test_second_request_comes_from_cache(self):
        self._ask(URL + " 4:3")
        sent_before = len(self.bot.sent)
        results, kw = self._ask(URL + " 4:3")
        self.assertEqual(len(self.bot.sent), sent_before)             # ничего не качали и не заливали заново
        self.assertEqual(len(results), 3)
        self.assertEqual(kw.get("cache_time"), 300)

    def test_frame_limit(self):
        globals_state.g_switcher = FakeSwitcher(globals_state.g_provider, 25)
        results, _ = self._ask(URL)
        self.assertEqual(len(results), ih.INLINE_PHOTO_LIMIT)

    def test_hint_mentions_formats(self):
        results, _ = self._ask("")
        self.assertIn("1:1", results[0].description)


if __name__ == "__main__":
    unittest.main()
