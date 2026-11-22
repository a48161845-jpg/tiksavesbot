"""Аудит переводов: каждая пользовательская строка из tr("...") и каждый экран есть на всех языках."""
import ast
import collections
import os
import unittest
import stubs

stubs.install()
import i18n  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMIN_ONLY = ("admin", "stats", "db_report", "owner_gift", "broadcast")  # админские экраны только на русском
LANGS = ("en", "uk", "kk", "uz", "ky")


def _literals():
    found = collections.OrderedDict()
    for dp, _dn, fn in os.walk(ROOT):
        if any(x in dp for x in ("tests", "__pycache__", "legacy", ".git")):
            continue
        for f in fn:
            if not f.endswith(".py") or any(a in f for a in ADMIN_ONLY):
                continue
            p = os.path.join(dp, f)
            with open(p, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) == "tr" and len(n.args) >= 2:
                    a = n.args[1]
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        found.setdefault(a.value, p)
    return found


class Coverage(unittest.TestCase):
    def test_every_tr_literal_is_translated(self):
        i18n._ensure_loaded()
        lits = _literals()
        self.assertGreater(len(lits), 100)
        for lang in LANGS:
            missing = [k for k in lits if k not in i18n.TRANSLATIONS[lang]]
            self.assertEqual(missing, [], f"{lang}: нет перевода для {len(missing)} строк, например {missing[:2]}")

    def test_translations_keep_format_placeholders(self):
        import re
        i18n._ensure_loaded()
        for lang in LANGS:
            for ru, tx in i18n.TRANSLATIONS[lang].items():
                self.assertEqual(sorted(re.findall(r"\{\w+\}", ru)), sorted(re.findall(r"\{\w+\}", tx)),
                                 f"{lang}: плейсхолдеры разошлись в {ru[:50]!r}")

    def test_no_empty_translations(self):
        i18n._ensure_loaded()
        for lang in LANGS:
            empty = [k for k, v in i18n.TRANSLATIONS[lang].items() if not (v or "").strip()]
            self.assertEqual(empty, [], lang)


if __name__ == "__main__":
    unittest.main()
