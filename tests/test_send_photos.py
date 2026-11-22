import asyncio
import unittest
import stubs

stubs.install()
from ui import send_helpers as sh  # noqa: E402


class FakeMessage:
    """Запоминает, что и как отправили."""
    def __init__(self):
        self.calls = []
        self.bot = object()
        class _C: id = 1  # noqa: E306
        self.chat = _C()
        class _U: id = 5  # noqa: E306
        self.from_user = _U()

    async def answer_media_group(self, media):
        self.calls.append(("group", [(m.__dict__.get("media"), m.__dict__.get("caption")) for m in media]))

    async def answer_photo(self, src, **kw):
        self.calls.append(("photo", src, kw.get("caption"), kw.get("reply_markup")))

    async def answer_video(self, src, **kw):
        self.calls.append(("video", src, kw.get("caption"), kw.get("reply_markup")))


MARKUP = object()


def run(urls, markup=None, live=None, caption="CAP"):
    sh.ALBUM_PAUSE_MIN = sh.ALBUM_PAUSE_MAX = 0
    msg = FakeMessage()
    asyncio.run(sh.send_photos(msg, urls, caption_html=caption, live=live, reply_markup=markup))
    return msg.calls


class ButtonsOnPhoto(unittest.TestCase):
    def test_album_with_buttons_last_frame_is_separate(self):
        calls = run(["a", "b", "c"], MARKUP)
        self.assertEqual(calls[0], ("group", [("a", None), ("b", None)]))          # альбом без подписи
        self.assertEqual(calls[1], ("photo", "c", "CAP", MARKUP))                  # подпись и кнопки — на фото
        self.assertEqual(len(calls), 2)

    def test_single_photo_gets_buttons_directly(self):
        self.assertEqual(run(["a"], MARKUP), [("photo", "a", "CAP", MARKUP)])

    def test_two_photos_album_plus_single(self):
        calls = run(["a", "b"], MARKUP)
        self.assertEqual(calls, [("photo", "a", None, None), ("photo", "b", "CAP", MARKUP)])

    def test_eleven_photos_buttons_on_the_very_last(self):
        urls = [str(i) for i in range(11)]
        calls = run(urls, MARKUP)
        self.assertEqual(calls[0][0], "group")
        self.assertEqual(len(calls[0][1]), 10)
        self.assertTrue(all(cap is None for _m, cap in calls[0][1]))               # подпись не на первом альбоме
        self.assertEqual(calls[1], ("photo", "10", "CAP", MARKUP))

    def test_without_markup_caption_on_last_of_album(self):
        calls = run(["a", "b", "c"])
        self.assertEqual(calls, [("group", [("a", None), ("b", None), ("c", "CAP")])])

    def test_single_photo_without_markup_is_not_a_media_group(self):
        self.assertEqual(run(["a"]), [("photo", "a", "CAP", None)])

    def test_live_frame_sent_as_video_with_buttons(self):
        calls = run(["a", "b"], MARKUP, live={"b": "clip.mp4"})
        self.assertEqual(calls[-1][0], "video")
        self.assertEqual(calls[-1][1], "clip.mp4")
        self.assertIs(calls[-1][3], MARKUP)
        self.assertIn("CAP", calls[-1][2])


if __name__ == "__main__":
    unittest.main()
