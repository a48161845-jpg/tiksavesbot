import asyncio
import tempfile
import unittest
from pathlib import Path
import stubs

stubs.install()
from downloaders import photo_crop as pc  # noqa: E402

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None


class CropBox(unittest.TestCase):
    def test_portrait_to_square_cuts_top_and_bottom(self):
        self.assertEqual(pc.crop_box(1080, 1920, 1, 1), (0, 420, 1080, 1500))

    def test_portrait_to_landscape(self):
        l, t, r, b = pc.crop_box(1080, 1920, 16, 9)
        self.assertEqual((l, r), (0, 1080))
        self.assertAlmostEqual((r - l) / (b - t), 16 / 9, delta=0.01)

    def test_landscape_to_portrait_cuts_sides(self):
        l, t, r, b = pc.crop_box(1920, 1080, 9, 16)
        self.assertEqual((t, b), (0, 1080))
        self.assertAlmostEqual((r - l) / (b - t), 9 / 16, delta=0.01)
        self.assertEqual(l, 1920 - r)  # по центру

    def test_already_matching_is_untouched(self):
        self.assertEqual(pc.crop_box(1080, 1920, 9, 16), (0, 0, 1080, 1920))

    def test_bad_size(self):
        with self.assertRaises(ValueError):
            pc.crop_box(0, 10, 1, 1)

    def test_normalize(self):
        self.assertEqual(pc.normalize_ratio("1x1"), "1x1")
        self.assertEqual(pc.normalize_ratio("evil"), "orig")
        self.assertEqual(pc.normalize_ratio(None), "orig")


@unittest.skipIf(Image is None, "Pillow не установлен")
class CropFiles(unittest.TestCase):
    def _make(self, d, w, h, mode="RGB", ext=".jpg"):
        p = Path(d) / f"src{ext}"
        Image.new(mode, (w, h), (200, 30, 30) if mode == "RGB" else (200, 30, 30, 128)).save(p)
        return p

    def test_every_ratio(self):
        with tempfile.TemporaryDirectory() as d:
            src = self._make(d, 1080, 1920)
            for code, (rw, rh) in ((c, v) for c, v in pc.RATIOS.items() if v):
                dst = Path(d) / f"out_{code}.jpg"
                asyncio.run(pc.crop_image(src, dst, code))
                with Image.open(dst) as im:
                    self.assertEqual(im.format, "JPEG")
                    self.assertAlmostEqual(im.width / im.height, rw / rh, delta=0.01, msg=code)

    def test_png_with_alpha_becomes_jpeg(self):
        with tempfile.TemporaryDirectory() as d:
            src = self._make(d, 800, 600, mode="RGBA", ext=".png")
            dst = Path(d) / "o.jpg"
            asyncio.run(pc.crop_image(src, dst, "1x1"))
            with Image.open(dst) as im:
                self.assertEqual(im.size, (600, 600))
                self.assertEqual(im.mode, "RGB")

    def test_huge_image_fits_telegram_limit(self):
        with tempfile.TemporaryDirectory() as d:
            src = self._make(d, 9000, 9000)
            dst = Path(d) / "o.jpg"
            asyncio.run(pc.crop_image(src, dst, "1x1"))
            with Image.open(dst) as im:
                self.assertLessEqual(im.width + im.height, 10000)

    def test_orig_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            src = self._make(d, 100, 100)
            with self.assertRaises(ValueError):
                asyncio.run(pc.crop_image(src, Path(d) / "o.jpg", "orig"))

    def test_cropped_sources_falls_back_to_url_on_failure(self):
        from ui import send_helpers as sh

        class Msg:
            bot = object()
            class chat: id = 1

        async def fake_download(urls, kinds, bot=None, chat_id=None):
            return [None for _ in urls]          # скачать не удалось

        sh._download_media_files = fake_download
        sources, tmp = asyncio.run(sh._cropped_sources([("https://p/1.jpg", "photo"), ("https://v/1.mp4", "video")], "1x1", Msg()))
        self.assertEqual(sources, ["https://p/1.jpg", "https://v/1.mp4"])
        self.assertEqual(tmp, [])

    def test_cropped_sources_crops_downloaded_photo(self):
        from ui import send_helpers as sh

        class Msg:
            bot = object()
            class chat: id = 1

        with tempfile.TemporaryDirectory() as d:
            src = self._make(d, 1080, 1920)

            async def fake_download(urls, kinds, bot=None, chat_id=None):
                return [src for _ in urls]

            sh._download_media_files = fake_download
            sources, tmp = asyncio.run(sh._cropped_sources([("https://p/1.jpg", "photo"), ("https://v/1.mp4", "video")], "16x9", Msg()))
            self.assertEqual(len(tmp), 2)
            self.assertEqual(sources[1], "https://v/1.mp4")      # live-клип идёт как есть
            with Image.open(tmp[1]) as im:
                self.assertAlmostEqual(im.width / im.height, 16 / 9, delta=0.01)


class PickerKeyboard(unittest.TestCase):
    def test_ratio_buttons(self):
        from ui import picker_state as ps
        ps.pending["rid"] = {"uid": 1, "photos": ["a", "b", "c"], "selected": set(), "page": 0, "ratio": "4x3"}
        kb = ps.picker_kb("rid")
        rows = [[(b.text, b.callback_data) for b in r] for r in kb.inline_keyboard]
        ratio_rows = [r for r in rows if r and r[0][1].startswith("pk:r:")]
        self.assertEqual([len(r) for r in ratio_rows], [3, 3])
        flat = [x for r in ratio_rows for x in r]
        self.assertEqual([c for _t, c in flat], [f"pk:r:rid:{c}" for c in pc.RATIO_CODES])
        self.assertEqual([t for t, _c in flat if t.startswith("✅")], ["✅ 4:3"])
        self.assertTrue(all(len(c.encode()) <= 64 for _t, c in flat))
        ps.pending.pop("rid")


if __name__ == "__main__":
    unittest.main()
