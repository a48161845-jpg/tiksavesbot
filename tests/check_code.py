"""
Статические проверки проекта без запуска (дополняют check_imports.py). Запуск: python tests/check_code.py
  1. обращения к store.* / lim.* — такие методы должны существовать;
  2. «забытый await»: вызов async-функции проекта отдельным оператором (корутина создаётся и не выполняется);
  3. плейсхолдеры в tr("... {n} ...") должны получать одноимённые аргументы;
  4. дубли функций-хендлеров в одном модуле (вторая перекрывает первую);
  5. ожидание задач через suppress(Exception) — CancelledError его не ловит (баг, из-за которого терялось «Бот остановлен»).
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = ("tests", "__pycache__", "legacy", ".git")


def files():
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP]
        for f in fns:
            if f.endswith(".py"):
                yield os.path.join(dp, f)


def parse(p):
    with open(p, encoding="utf-8") as fh:
        return ast.parse(fh.read())


def class_members(path, cls):
    for n in ast.walk(parse(path)):
        if isinstance(n, ast.ClassDef) and n.name == cls:
            names = {x.name for x in n.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for x in ast.walk(n):  # self.attr = ... в методах
                if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id == "self" and isinstance(x.ctx, ast.Store):
                    names.add(x.attr)
            return names
    return set()


def main() -> int:
    problems = []
    store_api = class_members(os.path.join(ROOT, "core", "storage.py"), "Storage")
    lim_api = class_members(os.path.join(ROOT, "core", "limiters.py"), "Limiters")
    trees = {p: parse(p) for p in files()}

    async_names = set()
    for t in trees.values():
        for n in ast.walk(t):
            if isinstance(n, ast.AsyncFunctionDef):
                async_names.add(n.name)

    for p, t in trees.items():
        rel = os.path.relpath(p, ROOT)
        # 1) store.* / lim.*
        for n in ast.walk(t):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                if n.value.id == "store" and store_api and n.attr not in store_api and not n.attr.startswith("__"):
                    problems.append(f"{rel}:{n.lineno}: store.{n.attr} — такого метода нет в Storage")
                if n.value.id == "lim" and lim_api and n.attr not in lim_api and not n.attr.startswith("__"):
                    problems.append(f"{rel}:{n.lineno}: lim.{n.attr} — такого метода нет в Limiters")
        # 2) забытый await (оператор-выражение, вызывающее async-функцию проекта)
        for n in ast.walk(t):
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
                f = n.value.func
                name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
                if name in async_names and name not in {"answer", "edit_text", "delete", "send_message", "reply", "copy_to"}:
                    # объект может быть не нашим (aiogram-метод с таким же именем) — отмечаем только функции проекта
                    if isinstance(f, ast.Name):
                        problems.append(f"{rel}:{n.lineno}: вызов async-функции {name}() без await")
        # 3) плейсхолдеры tr()
        for n in ast.walk(t):
            if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", "")) == "tr" and len(n.args) >= 2:
                a = n.args[1]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    need = set(re.findall(r"\{(\w+)\}", a.value))
                    got = {k.arg for k in n.keywords if k.arg}
                    has_star = any(k.arg is None for k in n.keywords)
                    if need - got and not has_star:
                        problems.append(f"{rel}:{n.lineno}: tr() не передаёт {sorted(need - got)} для {a.value[:40]!r}")
        # 4) дубли хендлеров
        seen = {}
        for n in t.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.decorator_list:
                if n.name in seen:
                    problems.append(f"{rel}:{n.lineno}: функция {n.name} определена повторно (строка {seen[n.name]}) — первая перекрыта")
                seen[n.name] = n.lineno
        # 5) suppress(Exception) вокруг await задачи
        for n in ast.walk(t):
            if isinstance(n, ast.With):
                for item in n.items:
                    c = item.context_expr
                    if isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "suppress" and any(
                            isinstance(a, ast.Name) and a.id == "Exception" for a in c.args):
                        for sub in ast.walk(n):
                            if isinstance(sub, ast.Await) and isinstance(sub.value, ast.Name) and re.search(r"task|_t$", sub.value.id):
                                problems.append(f"{rel}:{sub.lineno}: await задачи под suppress(Exception) — CancelledError пройдёт мимо")
    return problems


if __name__ == "__main__":
    probs = main()
    print("\n".join(probs) if probs else "code checks OK")
    sys.exit(1 if probs else 0)
