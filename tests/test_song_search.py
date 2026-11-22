import asyncio
import unittest
import stubs

stubs.install()
import i18n  # noqa: E402
from downloaders import song_search as ss  # noqa: E402
from downloaders import providers  # noqa: E402
from downloaders import tiktok_live as tl  # noqa: E402
from handlers import donate_callbacks as dc  # noqa: E402
from ui import keyboards as K  # noqa: E402
from ui import send_helpers as sh  # noqa: E402

SONG = {"title": "Blinding Lights", "author": "The Weeknd", "original": False, "cover": None}
ORIG = {"title": "оригинальный звук - dancer", "author": "dancer", "original": True, "cover": None}


class SongData(unittest.TestCase):
    def test_original_sound_detection(self):
        self.assertTrue(ss.is_original_sound("original sound - user"))
        self.assertTrue(ss.is_original_sound("Оригинальный звук - user"))
        self.assertTrue(ss.is_original_sound("anything", original=True))
        self.assertFalse(ss.is_original_sound("Blinding Lights"))

    def test_make_song(self):
        self.assertIsNone(ss.make_song("", None))
        self.assertIsNone(ss.make_song("  ", "\u200b"))
        s = ss.make_song("  Blinding\u200b   Lights ", "The Weeknd", False, "https://c/x.jpg")
        self.assertEqual((s["title"], s["author"], s["original"], s["cover"]), ("Blinding Lights", "The Weeknd", False, "https://c/x.jpg"))

    def test_from_tikwm(self):
        data = {"music_info": {"title": "Song", "author": "Artist", "original": False, "cover": "https://c/1.jpg", "play": "https://m/a.mp3"}}
        self.assertEqual(ss.song_from_tikwm(data)["title"], "Song")
        self.assertIsNone(ss.song_from_tikwm({}))
        self.assertIsNone(ss.song_from_tikwm({"music_info": "junk"}))

    def test_from_page(self):
        s = ss.song_from_page({"title": "T", "authorName": "A", "original": True, "coverLarge": "https://c/l.jpg"})
        self.assertTrue(s["original"])
        self.assertEqual(s["cover"], "https://c/l.jpg")
        self.assertIsNone(ss.song_from_page(None))

    def test_search_links(self):
        links = ss.search_links(SONG)
        self.assertEqual([l for l, _u in links], ["🎵 YouTube Music", "🟢 Spotify", "🍎 Apple Music", "🟡 Яндекс Музыка"])
        urls = dict(links)
        self.assertEqual(urls["🎵 YouTube Music"], "https://music.youtube.com/search?q=Blinding+Lights+The+Weeknd")
        self.assertEqual(urls["🟢 Spotify"], "https://open.spotify.com/search/Blinding%20Lights%20The%20Weeknd")
        self.assertTrue(all(u.startswith("https://") for u in urls.values()))

    def test_search_links_are_url_safe(self):
        s = ss.make_song("Tom & Jerry? #1", "Мы / Они")
        for _l, u in ss.search_links(s):
            self.assertNotIn(" ", u)
            self.assertNotIn("&1", u.split("?", 1)[-1].replace("%26", ""))   # & из названия не ломает параметры
            self.assertLess(u.count("?"), 2)

    def test_original_sound_only_youtube_by_author(self):
        links = ss.search_links(ORIG)
        self.assertEqual(len(links), 1)
        self.assertIn("search_query=dancer", links[0][1])

    def test_caption_line_is_html_safe(self):
        self.assertEqual(ss.song_caption(SONG), "\n🎵 <i>Blinding Lights — The Weeknd</i>")
        self.assertEqual(ss.song_caption(None), "")
        evil = ss.make_song("<b>x</b> & y", "a<i>")
        line = ss.song_caption(evil)
        self.assertNotIn("<b>x", line)
        self.assertIn("&lt;b&gt;x", line)
        self.assertEqual(ss.song_caption(ss.make_song("Same", "Same")), "\n🎵 <i>Same</i>")   # без «Same — Same»

    def test_audio_tags_limits(self):
        t = ss.audio_tags(ss.make_song("T" * 100, "A" * 100))
        self.assertEqual((len(t["title"]), len(t["performer"])), (64, 64))
        self.assertEqual(ss.audio_tags(None), {})


class ProvidersCarrySong(unittest.TestCase):
    def test_tikwm_music_info_reaches_media(self):
        d = {"play": "https://v/x.mp4", "music": "https://m/a.mp3",
             "music_info": {"title": "Song", "author": "Artist", "original": False, "cover": "https://c/1.jpg"}}
        m = providers.TikWMClient._media_from_data(d)
        self.assertEqual((m.music_title, m.music_author, m.music_original), ("Song", "Artist", False))

    def test_media_without_song_info(self):
        m = providers.TikWMClient._media_from_data({"play": "https://v/x.mp4", "music": "https://m/a.mp3"})
        self.assertIsNone(m.music_title)

    def test_page_music_block(self):
        import json
        item = {"desc": "d", "video": {"playAddr": "https://v/p.mp4"},
                "music": {"title": "Page Song", "authorName": "Page Artist", "original": False, "playUrl": "https://m/p.mp3"}}
        data = {"__DEFAULT_SCOPE__": {"webapp.video-detail": {"itemInfo": {"itemStruct": item}}}}
        html = '<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">%s</script>' % json.dumps(data)
        got = tl.parse_page_html(html)
        self.assertEqual(got["song"]["title"], "Page Song")
        self.assertEqual(got["song"]["author"], "Page Artist")


class Keyboards(unittest.TestCase):
    def test_find_song_button_only_when_song_known(self):
        def datas(has_song):
            kb = K.under_video_kb(True, True, "rid", "ru", has_song=has_song)
            return [b.callback_data for r in kb.inline_keyboard for b in r if b.__dict__.get("callback_data")]
        self.assertIn("dl:song:rid", datas(True))
        self.assertNotIn("dl:song:rid", datas(False))
        self.assertIn("dl:audio:rid", datas(True))

    def test_song_card_buttons(self):
        kb = K.song_kb("ru", SONG, req_id="rid", can_download=True)
        urls = [b.url for r in kb.inline_keyboard for b in r if b.__dict__.get("url")]
        self.assertEqual(len(urls), 4)
        self.assertTrue(all(len(r) <= 2 for r in kb.inline_keyboard))
        self.assertEqual(kb.inline_keyboard[-1][0].__dict__.get("callback_data"), "dl:audio:rid")
        kb2 = K.song_kb("ru", SONG, req_id="rid", can_download=False)
        self.assertFalse(any(b.__dict__.get("callback_data") for r in kb2.inline_keyboard for b in r))


class FakeMsg:
    def __init__(self):
        self.bot = object(); self.out = []
        class _C: id = 1  # noqa: E306
        self.chat = _C()
        class _U: id = 3  # noqa: E306
        self.from_user = _U()
    async def answer(self, text, **kw): self.out.append(("text", text, kw))
    async def answer_audio(self, audio, **kw): self.out.append(("audio", audio, kw))
    async def edit_reply_markup(self, **kw): self.out.append(("edit", kw))


class FakeCall:
    def __init__(self, data, uid=3):
        self.data = data; self.message = FakeMsg(); self.toasts = []
        class _U: pass  # noqa: E306
        self.from_user = _U(); self.from_user.id = uid; self.bot = object()
    async def answer(self, text=None, **kw): self.toasts.append((text, kw))


class Flow(unittest.TestCase):
    def setUp(self):
        i18n._ensure_loaded()
        async def label(bot, uid): return "u"
        async def gate(*a, **k): return True
        async def noop(*a, **k): return None
        class FS:
            def set_user_label(self, *a): pass
        dc.resolve_user_label, dc.gate_callback, dc.store = label, gate, FS()
        self.audio_calls = []
        async def fake_music(msg, prov, url, **kw): self.audio_calls.append((url, kw))
        dc.send_music_if_any = fake_music
        dc.video_extras.clear()

    def test_song_card_is_sent_and_extras_survive(self):
        dc.video_extras["r1"] = {"music": "https://m/a.mp3", "song": SONG, "src": "u", "uid": 3}
        call = FakeCall("dl:song:r1")
        asyncio.run(dc.dl_cb(call))
        kind, text, kw = call.message.out[0]
        self.assertTrue("Blinding Lights" in text and "The Weeknd" in text)
        self.assertIsNotNone(kw["reply_markup"])
        self.assertIn("r1", dc.video_extras)                                  # карточку можно открыть снова

    def test_original_sound_card(self):
        dc.video_extras["r2"] = {"music": None, "song": ORIG, "uid": 3}
        call = FakeCall("dl:song:r2")
        asyncio.run(dc.dl_cb(call))
        text = call.message.out[0][1]
        self.assertTrue("Оригинальный звук" in text or "Original sound" in text)

    def test_no_song_shows_alert(self):
        dc.video_extras["r3"] = {"music": "https://m/a.mp3", "uid": 3}
        call = FakeCall("dl:song:r3")
        asyncio.run(dc.dl_cb(call))
        self.assertTrue(call.toasts[0][1].get("show_alert"))
        self.assertEqual(call.message.out, [])

    def test_audio_gets_song_and_keeps_find_button(self):
        dc.video_extras["r4"] = {"music": "https://m/a.mp3", "song": SONG, "src": "s", "uid": 3}
        call = FakeCall("dl:audio:r4")
        asyncio.run(dc.dl_cb(call))
        url, kw = self.audio_calls[0]
        self.assertEqual(url, "https://m/a.mp3")
        self.assertEqual(kw["song"], SONG)
        edit = [o for o in call.message.out if o[0] == "edit"][0][1]["reply_markup"]
        datas = [b.callback_data for r in edit.inline_keyboard for b in r if b.__dict__.get("callback_data")]
        self.assertIn("dl:song:r4", datas)                                     # «Найти песню» осталась
        self.assertNotIn("dl:audio:r4", datas)                                 # «Музыка» убрана (уже отправлена)
        self.assertIn("r4", dc.video_extras)

    def test_extras_removed_when_nothing_left(self):
        dc.video_extras["r5"] = {"music": "https://m/a.mp3", "uid": 3}
        asyncio.run(dc.dl_cb(FakeCall("dl:audio:r5")))
        self.assertNotIn("r5", dc.video_extras)

    def test_audio_file_has_tags_caption_and_search_buttons(self):
        i18n._ensure_loaded()
        msg = FakeMsg()
        asyncio.run(_real_send_music(msg, SONG))
        kind, audio, kw = msg.out[0]
        self.assertEqual(kind, "audio")
        self.assertEqual((kw["title"], kw["performer"]), ("Blinding Lights", "The Weeknd"))
        self.assertIn("Blinding Lights — The Weeknd", kw["caption"])
        self.assertEqual(len([b for r in kw["reply_markup"].inline_keyboard for b in r]), 4)

    def test_audio_without_song_is_unchanged(self):
        msg = FakeMsg()
        asyncio.run(_real_send_music(msg, None))
        kw = msg.out[0][2]
        self.assertNotIn("title", kw)
        self.assertNotIn("reply_markup", kw)

    def test_translations_for_song_ui(self):
        i18n._ensure_loaded()
        for lang in ("en", "uk", "kk", "uz", "ky"):
            tr = i18n.TRANSLATIONS[lang]
            for key in ("🔎 Найти песню", "⬇️ Скачать аудио", "Нет данных о песне для этого видео."):
                self.assertIn(key, tr, (lang, key))
            self.assertEqual(sorted(__import__("re").findall(r"\{\w+\}", tr["🎵 <b>Песня из видео</b>\n<b>{title}</b>\n{author}\n\nНайди её в любимом сервисе или скачай звук 👇"])), ["{author}", "{title}"])


async def _real_send_music(msg, song):
    from core import globals_state
    sh.store = type("S", (), {"inc_audio": lambda *a, **k: None, "inc_error": lambda *a, **k: None})()
    await sh.send_music_if_any(msg, globals_state.g_provider, "https://m/a.mp3", song=song)


if __name__ == "__main__":
    unittest.main()
