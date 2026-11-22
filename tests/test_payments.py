import asyncio
import os
import tempfile
import time
import unittest
import stubs

stubs.install()
from core import config as C  # noqa: E402
from core.storage import Storage  # noqa: E402
from handlers import donate_callbacks as dc  # noqa: E402
from handlers import premium as pm  # noqa: E402


class _Obj:
    def __init__(self, **k): self.__dict__.update(k)


class FakeMsg:
    def __init__(self, payload, amount, uid=5):
        self.from_user = _Obj(id=uid)
        self.bot = object()
        self.successful_payment = _Obj(invoice_payload=payload, total_amount=amount, telegram_payment_charge_id="c1")
        self.answers = []
    async def answer(self, text, **kw): self.answers.append(text)


class FakePre:
    def __init__(self, payload, amount, uid=5):
        self.invoice_payload, self.total_amount, self.from_user = payload, amount, _Obj(id=uid)
        self.result = None
    async def answer(self, ok, error_message=None): self.result = (ok, error_message)


class Payments(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self._cwd = os.getcwd(); os.chdir(self.d.name)
        self.st = Storage()
        dc.store = self.st
        async def label(bot, uid): return "u"
        async def gate(*a, **k): return True
        self.events = []
        async def log_event(bot, kind, lines): self.events.append((kind, lines))
        dc.resolve_user_label, dc.gate_message, dc.log_event = label, gate, log_event

    def tearDown(self):
        os.chdir(self._cwd); self.d.cleanup()

    def test_premium_payment_grants_subscription(self):
        days, price = C.PREMIUM_PLANS[0]
        m = FakeMsg(f"premium:{days}", price)
        asyncio.run(dc.payment_ok(m))
        self.assertTrue(self.st.is_premium(5))
        self.assertAlmostEqual(self.st.premium_until(5), time.time() + days * 86400, delta=10)
        self.assertEqual(len(m.answers), 1)
        self.assertIn(self.events[0][0], ("stars",))
        self.assertTrue(any("Premium" in l for l in self.events[0][1]))

    def test_second_payment_extends(self):
        days, price = C.PREMIUM_PLANS[0]
        asyncio.run(dc.payment_ok(FakeMsg(f"premium:{days}", price)))
        first = self.st.premium_until(5)
        asyncio.run(dc.payment_ok(FakeMsg(f"premium:{days}", price)))
        self.assertAlmostEqual(self.st.premium_until(5) - first, days * 86400, delta=2)

    def test_pre_checkout_accepts_correct_price_only(self):
        days, price = C.PREMIUM_PLANS[1]
        ok = FakePre(f"premium:{days}", price)
        asyncio.run(dc.pre_checkout(ok)); self.assertTrue(ok.result[0])
        wrong = FakePre(f"premium:{days}", price - 1)
        asyncio.run(dc.pre_checkout(wrong)); self.assertFalse(wrong.result[0])
        unknown = FakePre("premium:7", 10)
        asyncio.run(dc.pre_checkout(unknown)); self.assertFalse(unknown.result[0])
        junk = FakePre("premium:abc", 10)
        asyncio.run(dc.pre_checkout(junk)); self.assertFalse(junk.result[0])

    def test_plain_donation_does_not_grant_premium(self):
        m = FakeMsg("stars:100", 100)
        asyncio.run(dc.payment_ok(m))
        self.assertFalse(self.st.is_premium(5))

    def test_premium_screen_shows_active_date(self):
        self.st.grant_premium(5, 30)
        pm.store = self.st
        text = pm.premium_screen(5)
        self.assertIn("Premium", text)
        self.assertIn(pm.fmt_date(self.st.premium_until(5)), text)


if __name__ == "__main__":
    unittest.main()
