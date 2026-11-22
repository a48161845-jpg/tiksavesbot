import asyncio
import unittest
import stubs

stubs.install()
from handlers import group_links as gl  # noqa: E402


class Ent:
    def __init__(self, type, url=None):
        self.type, self.url = type, url


class Chat:
    def __init__(self, t): self.type = t


class Msg:
    def __init__(self, chat="supergroup", text=None, caption=None, entities=None, caption_entities=None, user=1):
        self.chat, self.text, self.caption = Chat(chat), text, caption
        self.entities, self.caption_entities = entities, caption_entities
        self.from_user = object() if user else None

    def model_copy(self, update=None):
        m = Msg.__new__(Msg); m.__dict__.update(self.__dict__); m.__dict__.update(update or {}); return m


def run(msg):
    seen = []

    async def handler(ev, data):
        seen.append(ev.text)
        return "ok"
    asyncio.run(gl.GroupLinksMiddleware()(handler, msg, {}))
    return seen


class Collect(unittest.TestCase):
    def test_multiple_and_dedupe(self):
        t = "смотри https://vt.tiktok.com/ZSabc/ и https://www.instagram.com/reel/Abc123/?x=1. ещё https://vt.tiktok.com/ZSabc/ и https://example.com/x"
        self.assertEqual(gl.collect_links(t), ["https://vt.tiktok.com/ZSabc/", "https://www.instagram.com/reel/Abc123/?x=1"])

    def test_text_link_entity(self):
        self.assertEqual(gl.collect_links("тык", [Ent("text_link", "https://youtu.be/abcdefghijk")]), ["https://youtu.be/abcdefghijk"])

    def test_limit(self):
        t = " ".join(f"https://www.tiktok.com/@u/video/{7000000000000000000 + i}" for i in range(6))
        self.assertEqual(len(gl.collect_links(t)), gl.MAX_LINKS_PER_MESSAGE)


class Middleware(unittest.TestCase):
    def test_caption_link_in_group(self):
        self.assertEqual(run(Msg(caption="лови https://www.tiktok.com/@u/video/7704697999137574162")),
                         ["https://www.tiktok.com/@u/video/7704697999137574162"])

    def test_each_link_handled(self):
        self.assertEqual(len(run(Msg(text="https://youtu.be/abcdefghijk https://www.instagram.com/reel/Abc123/"))), 2)

    def test_chat_without_links_passes_through(self):
        self.assertEqual(run(Msg(text="привет всем")), ["привет всем"])

    def test_private_and_commands_untouched(self):
        self.assertEqual(run(Msg(chat="private", text="a https://youtu.be/abcdefghijk b")), ["a https://youtu.be/abcdefghijk b"])
        self.assertEqual(run(Msg(text="/start https://youtu.be/abcdefghijk")), ["/start https://youtu.be/abcdefghijk"])

    def test_unsupported_link_ignored(self):
        self.assertEqual(run(Msg(text="https://example.com/page")), ["https://example.com/page"])


if __name__ == "__main__":
    unittest.main()
