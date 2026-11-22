import asyncio
import os
import tempfile
import time
import unittest
import stubs

stubs.install()
import i18n  # noqa: E402
from core import helpers  # noqa: E402
from core.storage import Storage  # noqa: E402
from handlers import support_handler as sh  # noqa: E402
from handlers import admin_commands as ac  # noqa: E402
from ui import support_state as ss  # noqa: E402
from ui import keyboards as K  # noqa: E402


# ------------------------------------------------------------------ источники статистики
class Sources(unittest.TestCase):
    def test_internal_names_map_to_platform(self):
        n = helpers.normalize_source
        self.assertEqual(n("tiktok_ytdlp_fallback"), "tiktok")
        self.assertEqual(n("instagram-mirror"), "instagram")
        self.assertEqual(n("twitter-fx"), "twitter")
        self.assertEqual(n("reddit-json"), "reddit")
        self.assertEqual(n("X"), "twitter")
        self.assertEqual(n("youtube"), "youtube")
        self.assertEqual(n(""), "unknown")
        self.assertEqual(n(None), "unknown")

    def test_inc_download_and_migration(self):
        d = tempfile.TemporaryDirectory()
        cwd = os.getcwd(); os.chdir(d.name)
        try:
            st = Storage()
            st.inc_download(1, "video", source="tiktok_ytdlp_fallback")
            st.inc_download(1, "video", source="tiktok")
            self.assertEqual(st.data["stats"]["all"]["downloads"]["by_source"], {"tiktok": 2})
            # старые «грязные» данные: вливаются в платформы везде
            st.data["stats"]["all"]["downloads"]["by_source"] = {"tiktok": 5, "tiktok_ytdlp_fallback": 3, "instagram-mirror": 2}
            st.data["user_stats"]["downloads"]["1"]["by_source"] = {"tiktok_ytdlp_fallback": 4}
            changed = st.merge_legacy_sources()
            self.assertEqual(changed, 3)
            self.assertEqual(st.data["stats"]["all"]["downloads"]["by_source"], {"tiktok": 8, "instagram": 2})
            self.assertEqual(st.data["user_stats"]["downloads"]["1"]["by_source"], {"tiktok": 4})
            self.assertEqual(st.merge_legacy_sources(), 0)  # повторный запуск ничего не меняет
        finally:
            os.chdir(cwd); d.cleanup()

    def test_no_internal_source_names_left_in_code(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bad = []
        for dp, _dn, fn in os.walk(root):
            if any(x in dp for x in ("tests", "__pycache__", "legacy", ".git")):
                continue
            for f in fn:
                if f.endswith(".py"):
                    with open(os.path.join(dp, f), encoding="utf-8") as fh:
                        if 'source="tiktok_ytdlp_fallback"' in fh.read():
                            bad.append(f)
        self.assertEqual(bad, [])


# ------------------------------------------------------------------ поддержка: отмена
class FakeMsg:
    def __init__(self, uid=7):
        self.deleted = False; self.answers = []
        class _U: pass  # noqa: E306
        self.from_user = _U(); self.from_user.id = uid
        self.bot = object()
    async def delete(self): self.deleted = True
    async def answer(self, text, **kw): self.answers.append((text, kw))


class FakeCall:
    def __init__(self, data, uid=7):
        self.data, self.message = data, FakeMsg(uid)
        class _U: pass  # noqa: E306
        self.from_user = _U(); self.from_user.id = uid
        self.bot = object(); self.toasts = []
    async def answer(self, text=None, **kw): self.toasts.append(text)


class SupportCancel(unittest.TestCase):
    def setUp(self):
        async def label(bot, uid): return "u"
        async def gate(*a, **k): return True
        async def noop(*a, **k): return None
        sh.resolve_user_label, sh.gate_message, sh.log_event = label, gate, noop
        class FS:
            def set_user_label(self, *a): pass
        sh.store = FS()
        ss.waiting_support_message.clear(); ss.pending_admin_msg.clear()

    def test_support_screen_has_cancel_button(self):
        datas = [b.callback_data for r in K.support_kb("ru").inline_keyboard for b in r]
        self.assertEqual(datas, ["support:cancel"])

    def test_open_then_cancel(self):
        msg = FakeMsg()
        asyncio.run(sh.open_support(msg, 7, "u"))
        self.assertIn(7, ss.waiting_support_message)
        self.assertIsNotNone(msg.answers[0][1]["reply_markup"])          # кнопка «Отмена» приклеена
        call = FakeCall("support:cancel")
        asyncio.run(sh.support_cb(call))
        self.assertNotIn(7, ss.waiting_support_message)
        self.assertTrue(call.message.deleted)
        self.assertIn("отменено", call.toasts[0])

    def test_cancel_when_nothing_open_is_quiet(self):
        call = FakeCall("support:cancel")
        asyncio.run(sh.support_cb(call))
        self.assertEqual(call.toasts, [None])

    def test_cancel_command(self):
        ss.waiting_support_message[7] = time.time()
        msg = FakeMsg()
        asyncio.run(sh.cancel_cmd(msg))
        self.assertNotIn(7, ss.waiting_support_message)
        self.assertEqual(len(msg.answers), 1)

    def test_reply_button_opens_support(self):
        call = FakeCall("support:open")
        asyncio.run(sh.support_cb(call))
        self.assertIn(7, ss.waiting_support_message)


# ------------------------------------------------------------------ админ пишет пользователю
class FakeBot:
    def __init__(self, fail=None): self.sent, self.fail = [], fail
    async def send_message(self, uid, text, **kw):
        if self.fail:
            raise RuntimeError(self.fail)
        self.sent.append((uid, text, kw.get("reply_markup")))


class FakeAdminMsg:
    def __init__(self, text, uid=1, html=None):
        self.text, self.html_text, self.answers = text, html or text, []
        class _U: pass  # noqa: E306
        self.from_user = _U(); self.from_user.id = uid
        self.bot = FakeBot(); self.content_type = "text"
    async def answer(self, text, **kw): self.answers.append(text)


class AdminMessaging(unittest.TestCase):
    def setUp(self):
        i18n._ensure_loaded()
        async def label(bot, uid): return "adm"
        async def gate(*a, **k): return True
        async def noop(*a, **k): return None
        async def resolve(bot, arg): return {"42": 42, "@bob": 42}.get(arg)
        ac.resolve_user_label, ac.gate_message, ac.log_admin_action_to_channel, ac.resolve_uid_from_arg = label, gate, noop, resolve
        ac.is_admin = lambda uid: uid == 1
        class FS:
            def set_user_label(self, *a): pass
            def get_user_label(self, uid): return "bob"
        ac.store = FS()
        ss.pending_admin_msg.clear()

    def test_msg_command_by_id_and_username(self):
        for target in ("42", "@bob"):
            m = FakeAdminMsg(f"/msg {target} Привет, <b>как дела</b>?", html=f"/msg {target} Привет, <b>как дела</b>?")
            asyncio.run(ac.msg_cmd(m))
            uid, text, kb = m.bot.sent[0] if m.bot.sent else (None, None, None)
            self.assertEqual(uid, 42)
            self.assertTrue("Сообщение от администрации" in text or "Message from the administration" in text)  # язык получателя
            self.assertIn("Привет, <b>как дела</b>?", text)
            self.assertNotIn("/msg", text)
            self.assertIsNotNone(kb)                                     # кнопка «💬 Ответить»
            self.assertIn("Отправлено", m.answers[-1])

    def test_msg_usage_and_unknown_user(self):
        m = FakeAdminMsg("/msg 42")
        asyncio.run(ac.msg_cmd(m))
        self.assertIn("/msg ID текст", m.answers[0])
        m = FakeAdminMsg("/msg 999 привет")
        asyncio.run(ac.msg_cmd(m))
        self.assertIn("не найден", m.answers[0])

    def test_non_admin_is_ignored(self):
        m = FakeAdminMsg("/msg 42 hi", uid=5)
        asyncio.run(ac.msg_cmd(m))
        self.assertEqual((m.bot.sent, m.answers), ([], []))

    def test_blocked_user_reported(self):
        bot = FakeBot(fail="Forbidden: bot was blocked by the user")
        ok, info = asyncio.run(ac.deliver_admin_message(bot, 1, "adm", 42, html_body="hi"))
        self.assertFalse(ok)
        self.assertIn("заблокировал", info)

    def test_panel_flow_target_then_text(self):
        ss.pending_admin_msg[1] = {"step": "target", "uid": None, "ts": time.time()}
        self.assertTrue(ac._admin_msg_pending(FakeAdminMsg("@bob")))
        self.assertFalse(ac._admin_msg_pending(FakeAdminMsg("/start")))        # команды не перехватываем
        self.assertFalse(ac._admin_msg_pending(FakeAdminMsg("x", uid=5)))      # чужие — тоже
        m = FakeAdminMsg("@bob")
        asyncio.run(ac.admin_msg_capture(m))
        self.assertEqual(ss.pending_admin_msg[1]["uid"], 42)
        self.assertEqual(ss.pending_admin_msg[1]["step"], "text")
        m2 = FakeAdminMsg("Здравствуйте!")
        asyncio.run(ac.admin_msg_capture(m2))
        self.assertEqual(m2.bot.sent[0][0], 42)
        self.assertNotIn(1, ss.pending_admin_msg)

    def test_panel_flow_unknown_target_keeps_waiting(self):
        ss.pending_admin_msg[1] = {"step": "target", "uid": None, "ts": time.time()}
        m = FakeAdminMsg("@nobody")
        asyncio.run(ac.admin_msg_capture(m))
        self.assertEqual(ss.pending_admin_msg[1]["step"], "target")
        self.assertIn("Не нашёл", m.answers[0])

    def test_translations_exist(self):
        for lang in ("en", "uk", "kk", "uz", "ky"):
            for key in (ac.ADMIN_MSG_HEADER, "💬 Ответить", "✖️ Обращение отменено. Если понадобится помощь — /support."):
                self.assertIn(key, i18n.TRANSLATIONS[lang], (lang, key))

    def test_admin_menu_has_message_button(self):
        datas = [b.callback_data for r in K.admin_menu_kb(False).inline_keyboard for b in r]
        self.assertIn("ad:msg", datas)


# ------------------------------------------------------------------ диагностика Bot API
class BotApiDiagnostics(unittest.TestCase):
    def test_state_and_reasons(self):
        from core import local_bot_api as lba
        lba.set_state("cloud", "причина")
        self.assertEqual(lba.STATE, {"mode": "cloud", "reason": "причина"})
        saved = (lba.API_ID, lba.API_HASH)
        try:
            lba.API_ID, lba.API_HASH = "", ""
            text = lba.diagnose_config()
            self.assertIn("API_ID", text)
            self.assertIn("API_HASH", text)
            self.assertIn(".env", text)
        finally:
            lba.API_ID, lba.API_HASH = saved


if __name__ == "__main__":
    unittest.main()
