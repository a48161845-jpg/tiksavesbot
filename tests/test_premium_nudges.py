import asyncio
import random
import tempfile
import time
import unittest
import stubs

stubs.install()
import i18n  # noqa: E402
from core import config as C  # noqa: E402
from core import nudge_texts as nt  # noqa: E402
from core.limiters import Limiters  # noqa: E402
from core.storage import Storage  # noqa: E402
from core import download_nudge as dn  # noqa: E402
from ui import keyboards as K  # noqa: E402

LANGS = ("en", "uk", "kk", "uz", "ky")


def _shape(t):
    import re
    return (t.count("<b>"), t.count("</b>"), t.count("\n"), sorted(re.findall(r"\{\w+\}", t)), t[:2])


class PremiumStorage(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        import os
        self._cwd = os.getcwd(); os.chdir(self.d.name)
        self.st = Storage()

    def tearDown(self):
        import os
        os.chdir(self._cwd); self.d.cleanup()

    def test_grant_extends_and_revoke(self):
        self.assertFalse(self.st.is_premium(1))
        u1 = self.st.grant_premium(1, 30)
        self.assertTrue(self.st.is_premium(1))
        self.assertAlmostEqual(u1, time.time() + 30 * 86400, delta=5)
        u2 = self.st.grant_premium(1, 30)                    # продление добавляется к остатку
        self.assertAlmostEqual(u2 - u1, 30 * 86400, delta=1)
        self.assertEqual(self.st.premium_active_ids(), [1])
        self.assertTrue(self.st.revoke_premium(1))
        self.assertFalse(self.st.is_premium(1))
        self.assertFalse(self.st.revoke_premium(1))

    def test_expired_is_not_premium(self):
        self.st.data.setdefault("premium", {})["7"] = int(time.time()) - 10
        self.assertFalse(self.st.is_premium(7))
        self.assertEqual(self.st.premium_active_ids(), [])


class PremiumLimits(unittest.TestCase):
    def test_multiplier_applies_only_to_premium(self):
        from core import storage
        lim = Limiters()
        free_cap = C.DL_MAX_ACTIONS
        orig = storage.store.is_premium
        try:
            storage.store.is_premium = lambda uid: uid == 2
            ok_free = sum(lim.dl_hit(1)[0] for _ in range(free_cap * 4))
            ok_prem = sum(lim.dl_hit(2)[0] for _ in range(free_cap * 4))
        finally:
            storage.store.is_premium = orig
        self.assertEqual(ok_free, free_cap)
        self.assertEqual(ok_prem, free_cap * C.PREMIUM_LIMIT_MULT)


class Nudges(unittest.TestCase):
    def test_all_texts_translated_with_same_markup(self):
        i18n._ensure_loaded()
        for d in nt.ALL_TRANSLATED:
            for lg in LANGS:
                self.assertEqual(_shape(d["ru"]), _shape(d[lg]), f"{lg}: {d['ru'][:40]!r}")
                self.assertEqual(i18n.TRANSLATIONS[lg][d["ru"]], d[lg])

    def test_texts_are_loud_and_present(self):
        self.assertGreaterEqual(len(nt.DONATE_NUDGES), 6)
        for d in nt.DONATE_NUDGES:
            self.assertIn("<b>", d["ru"])
            self.assertTrue(any(ch in d["ru"] for ch in "🔥🚨💥⚡️🔔🏆"))
            self.assertLess(len(d["ru"]), 700)

    def test_no_stale_ozon_or_crypto(self):
        for d in nt.ALL_TRANSLATED:
            for lg, t in d.items():
                self.assertNotIn("Ozon", t)
                self.assertNotIn("крипт", t.lower())

    def test_presets_have_no_unfilled_placeholders(self):
        for pid, (_title, texts) in nt.BROADCAST_PRESETS.items():
            for t in texts.values():
                self.assertNotIn("{m}", t, pid)
        self.assertIn(f"×{C.PREMIUM_LIMIT_MULT}", nt.BROADCAST_PRESETS["premium"][1]["ru"])
        self.assertNotIn("update", nt.BROADCAST_PRESETS)       # разовый «апдейт» в шаблонах не нужен

    def test_default_frequency_is_every_second_download(self):
        self.assertEqual(dn.NUDGE_EVERY, 2)

    def test_pick_distribution(self):
        rng = random.Random(1)
        kinds = [dn.pick_nudge(rng)[0] for _ in range(2000)]
        self.assertGreater(kinds.count("donate"), kinds.count("premium") > 0 and 1000)
        self.assertTrue(all(k in ("donate", "premium", "support") for k in kinds))

    def test_nudge_flow(self):
        sent = []

        class Bot:
            async def send_message(self, uid, text, **kw): sent.append((uid, text, kw))

        class FakeStore:
            def __init__(self): self.n = {}; self.prem = set()
            def bump_download_counter(self, uid): self.n[uid] = self.n.get(uid, 0) + 1; return self.n[uid]
            def is_premium(self, uid): return uid in self.prem

        fs = FakeStore(); fs.prem.add(9)
        dn.store = fs
        async def go():
            for _ in range(4): await dn.after_download_hooks(Bot(), 1, "u")   # 4 скачивания -> 2 напоминания
            for _ in range(4): await dn.after_download_hooks(Bot(), 9, "p")   # premium -> ни одного
        asyncio.run(go())
        self.assertEqual([u for u, _t, _k in sent], [1, 1])
        self.assertTrue(all(k.get("reply_markup") is not None for _u, _t, k in sent))
        self.assertTrue(all("{" not in t for _u, t, _k in sent))


class Keyboards(unittest.TestCase):
    def test_premium_kb_has_all_plans(self):
        datas = [b.callback_data for r in K.premium_kb("ru").inline_keyboard for b in r]
        for days, _st in C.PREMIUM_PLANS:
            self.assertIn(f"premium:buy:{days}", datas)
        self.assertIn("donate:back", datas)

    def test_donate_menu_has_premium_and_any_bank(self):
        datas = [getattr(b, "callback_data", None) for r in K.donate_main_kb("ru").inline_keyboard for b in r]
        self.assertIn("premium:open", datas)
        rub = [b.text for r in K.rub_donate_kb("ru").inline_keyboard for b in r]
        self.assertIn("🏦 Любой банк (СБП)", rub)
        self.assertFalse(any("Ozon" in t for t in rub))

    def test_buttons_directly_under_video_and_photo(self):
        v = [b.callback_data for r in K.under_video_kb(True, True, "rid", "ru").inline_keyboard for b in r if getattr(b, "callback_data", None)]
        self.assertIn("donate:open", v)
        self.assertIn("premium:open", v)
        p = [b.callback_data for r in K.post_download_kb("ru").inline_keyboard for b in r if getattr(b, "callback_data", None)]
        self.assertIn("donate:open", p)

    def test_nudge_keyboards(self):
        for kind in ("donate", "premium", "support"):
            kb = K.nudge_kb("ru", kind)
            self.assertTrue(kb.inline_keyboard)


if __name__ == "__main__":
    unittest.main()
