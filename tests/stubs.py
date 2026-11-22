"""
Заглушки для aiogram / aiohttp / dotenv — чтобы гонять чистые функции (парсеры, клавиатуры)
без установки зависимостей и без сети. Используются только в tests/.
"""
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("BOT_TOKEN", "123456:ABCdefGhIJKlmNoPQRsTUVwxyZ0123456789")


class _Any:
    """Универсальный объект: принимает любые аргументы, хранит kwargs как атрибуты."""

    def __init__(self, *a, **k):
        self.__dict__.update(k)

    def __call__(self, *a, **k):
        return _Any(*a, **k)

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _Any()


_EXC_HINTS = ("Error", "Exception", "BadRequest", "RetryAfter", "Forbidden", "NotFound", "SkipHandler", "Conflict")


class _Deco:
    """dp.message(...), dp.callback_query(...), dp.message.outer_middleware(...) — декоратор, возвращающий функцию как есть."""

    def __call__(self, *a, **k):
        return lambda f: f

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _Deco()


class _Dispatcher(_Deco):
    def __init__(self, *a, **k):
        pass


class _Mod(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name == "F":
            obj = _Any()
        elif name == "Dispatcher" and self.__name__ == "aiogram":
            obj = _Dispatcher
        elif name.endswith(_EXC_HINTS):
            obj = type(name, (Exception,), {})
        else:
            obj = type(name, (_Any,), {})
        setattr(self, name, obj)
        return obj


class _Finder:
    """Любой импорт aiogram.* / aiohttp.* / asyncpg.* / yt_dlp.* -> модуль-заглушка."""
    PREFIXES = ("aiogram", "aiohttp", "asyncpg", "yt_dlp")

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in self.PREFIXES:
            import importlib.machinery
            return importlib.machinery.ModuleSpec(name, self, is_package=True)
        return None

    def create_module(self, spec):
        m = _Mod(spec.name)
        m.__path__ = []
        return m

    def exec_module(self, module):
        pass


def install() -> None:
    sys.path.insert(0, ROOT)
    if not any(isinstance(f, _Finder) for f in sys.meta_path):
        sys.meta_path.insert(0, _Finder())
    d = types.ModuleType("dotenv")
    d.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = d
    import aiohttp
    aiohttp.ClientError = type("ClientError", (Exception,), {})
