import json
import unittest
import stubs

stubs.install()
from downloaders import tiktok_live as tl  # noqa: E402


class LiveDetection(unittest.TestCase):
    def test_plain_string_photos_are_not_live(self):
        photos, live = tl.photos_and_live(["https://p16.tiktokcdn.com/a.jpeg", "https://p16.tiktokcdn.com/b.jpeg"])
        self.assertEqual(len(photos), 2)
        self.assertEqual(live, {})

    def test_dict_frame_with_mp4(self):
        items = [
            {"url": "https://p/a.jpeg", "play": "https://v/clip.mp4?x=1"},
            {"url": "https://p/b.jpeg"},
        ]
        photos, live = tl.photos_and_live(items)
        self.assertEqual(photos, ["https://p/a.jpeg", "https://p/b.jpeg"])
        self.assertEqual(live, {"https://p/a.jpeg": "https://v/clip.mp4?x=1"})

    def test_nested_live_key_without_extension(self):
        items = [{"imageURL": {"urlList": ["https://p/a~tplv-x-image.jpeg"]},
                  "livePhoto": {"url_list": ["https://v.tiktokcdn.com/obj/abc123"]}}]
        photos, live = tl.photos_and_live(items)
        self.assertEqual(live, {"https://p/a~tplv-x-image.jpeg": "https://v.tiktokcdn.com/obj/abc123"})

    def test_cover_and_thumbnail_are_not_live(self):
        items = [{"url": "https://p/a.jpeg", "thumbnail": "https://p/t", "cover": "https://p/c"}]
        self.assertEqual(tl.photos_and_live(items)[1], {})

    def test_live_numbers(self):
        self.assertEqual(tl.live_note(["a", "b", "c"], {"b": "x"}), [2])


class PageParsing(unittest.TestCase):
    def _html(self, item):
        data = {"__DEFAULT_SCOPE__": {"webapp.video-detail": {"itemInfo": {"itemStruct": item}}}}
        return '<html><script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">%s</script></html>' % json.dumps(data)

    def test_photo_post_with_live_frame(self):
        item = {"desc": "hi", "imagePost": {"images": [
            {"imageURL": {"urlList": ["https://p/1.jpeg"]}, "livePhotoURL": {"urlList": ["https://v/1.mp4"]}},
            {"imageURL": {"urlList": ["https://p/2.jpeg"]}},
        ]}, "music": {"playUrl": "https://m/a.mp3"}, "video": {"playAddr": ""}}
        got = tl.parse_page_html(self._html(item))
        self.assertEqual(got["photos"], ["https://p/1.jpeg", "https://p/2.jpeg"])
        self.assertEqual(got["live"], {"https://p/1.jpeg": "https://v/1.mp4"})
        self.assertIsNone(got["video"])
        self.assertEqual(got["music"], "https://m/a.mp3")
        self.assertEqual(got["description"], "hi")

    def test_video_post(self):
        item = {"desc": "v", "video": {"playAddr": "https://v/play.mp4"}}
        got = tl.parse_page_html(self._html(item))
        self.assertEqual(got["video"], "https://v/play.mp4")
        self.assertEqual(got["photos"], [])

    def test_unavailable_post(self):
        data = {"__DEFAULT_SCOPE__": {"webapp.video-detail": {"statusCode": 10204, "statusMsg": "item doesn't exist"}}}
        html = '<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">%s</script>' % json.dumps(data)
        with self.assertRaises(RuntimeError):
            tl.parse_page_html(html)

    def test_no_data(self):
        with self.assertRaises(RuntimeError):
            tl.parse_page_html("<html>captcha</html>")


class OEmbed(unittest.TestCase):
    def test_full_url(self):
        js = {"embed_product_id": "7705899224126262546", "author_unique_id": "xibirr"}
        self.assertEqual(tl.url_from_oembed(js), "https://www.tiktok.com/@xibirr/video/7705899224126262546")

    def test_from_html_field(self):
        js = {"html": '<blockquote cite="https://www.tiktok.com/@abc/video/7704697999137574162">', "author_url": "https://www.tiktok.com/@abc"}
        self.assertEqual(tl.url_from_oembed(js), "https://www.tiktok.com/@abc/video/7704697999137574162")

    def test_garbage(self):
        self.assertIsNone(tl.url_from_oembed({"error": "x"}))
        self.assertIsNone(tl.url_from_oembed(None))


if __name__ == "__main__":
    unittest.main()
