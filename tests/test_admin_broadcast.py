import asyncio
import unittest
import stubs

stubs.install()
from core import broadcast as bc  # noqa: E402
from core import stats  # noqa: E402
from handlers import admin_callbacks as ac  # noqa: E402
from ui import keyboards as K  # noqa: E402


class FakeStore:
    data = {"stats": {"d": {}}}
    def get_all_user_ids(self): return [1, 2, 3, 4]
    def get_users_count(self): return 4
    def premium_active_ids(self): return [1]
    def list_bans(self): return []
    def is_maintenance(self): return False


class FakeStatus:
    def __init__(self): self.texts = []
    async def edit_text(self, text, **kw): self.texts.append(text)


class FakeBot:
    def __init__(self, behaviour): self.behaviour, self.sent = behaviour, []
    async def send_message(self, uid, text, **kw):
        act = self.behaviour.get(uid)
        if act == "blocked":
            raise RuntimeError("Forbidden: bot was blocked by the user")
        if act == "fail":
            raise RuntimeError("boom")
        self.sent.append((uid, text, kw.get("reply_markup")))


class FakeMessage:
    def __init__(self, bot): self.bot, self.status = bot, FakeStatus()
    async def answer(self, text, **kw): return self.status


class Broadcast(unittest.TestCase):
    def setUp(self):
        bc.store = FakeStore()
        bc.BROADCAST_DELAY_SEC = 0
        async def noop(*a, **k): return None
        bc.log_event = noop
        bc.log_admin = lambda *a, **k: None
        async def variants(users, raw, html, already_html=False): return {}
        bc.build_lang_variants = variants

    def test_summary_counts_blocked_and_failed(self):
        bot = FakeBot({2: "blocked", 3: "fail"})
        msg = FakeMessage(bot)
        asyncio.run(bc.do_broadcast(msg, 9, "admin", "<b>hi</b>", already_html=True, kb_kind="donate"))
        self.assertEqual([u for u, _t, _m in bot.sent], [1, 4])
        self.assertTrue(all(m is not None for _u, _t, m in bot.sent))     # кнопки приклеены
        final = msg.status.texts[-1]
        self.assertIn("Рассылка завершена", final)
        self.assertIn("Доставлено: <b>2</b> из <b>4</b>", final)
        self.assertIn("Заблокировали бота: <b>1</b>", final)
        self.assertIn("Ошибки: <b>1</b>", final)

    def test_no_buttons_when_kind_not_given(self):
        bot = FakeBot({})
        asyncio.run(bc.do_broadcast(FakeMessage(bot), 9, "admin", "x", already_html=True))
        self.assertTrue(all(m is None for _u, _t, m in bot.sent))

    def test_progress_bar(self):
        self.assertEqual(bc._progress_bar(0, 10), "░" * 12)
        self.assertEqual(bc._progress_bar(10, 10), "▓" * 12)


class AdminPanel(unittest.TestCase):
    def test_dashboard_renders(self):
        stats.store = FakeStore()
        text = stats.admin_dashboard_text()
        for part in ("Админ-панель", "Сегодня", "Пользователей: <b>4</b>", "Premium: <b>1</b>", "Тех. режим"):
            self.assertIn(part, text)

    def test_menu_buttons(self):
        datas = [b.callback_data for r in K.admin_menu_kb(False).inline_keyboard for b in r]
        for d in ("ad:stats", "ad:top", "ad:bc", "ad:prem", "ad:errors", "ad:tex", "ad:back", "ad:close"):
            self.assertIn(d, datas)
        self.assertTrue(all(len(d.encode()) <= 64 for d in datas))

    def test_every_preset_has_button_and_text(self):
        from core.nudge_texts import BROADCAST_PRESETS
        datas = [b.callback_data for r in K.admin_broadcast_menu_kb().inline_keyboard for b in r]
        for pid in BROADCAST_PRESETS:
            self.assertIn(f"ad:bp:{pid}", datas)
            self.assertTrue(ac._broadcast_raw(f"p_{pid}").strip())
            self.assertIn(ac._broadcast_kb_kind(f"p_{pid}"), ("donate", "premium"))
        self.assertIn("ad:bp:support", datas)
        self.assertEqual(ac._broadcast_kb_kind("reminder"), "support")

    def test_confirm_callback_fits_telegram_limit(self):
        for kind in ("p_donate", "p_premium", "p_support", "custom"):
            kb = K.admin_broadcast_confirm_kb(kind)
            self.assertTrue(all(len(b.callback_data.encode()) <= 64 for r in kb.inline_keyboard for b in r))


if __name__ == "__main__":
    unittest.main()
