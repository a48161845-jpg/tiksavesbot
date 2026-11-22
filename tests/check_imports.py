"""
Статическая проверка импортов проекта (без запуска и без зависимостей):
каждый `from X import a, b` / `import X`, где X — модуль проекта, должен существовать,
а имена a, b — быть определены в нём (или быть подмодулями пакета).
Ловит и «ленивые» импорты внутри функций, которые smoke-импорт bot.py не видит.
Запуск: python tests/check_imports.py   (код возврата 1, если есть проблемы)
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"__pycache__", ".git", "tests", "legacy"}  # legacy — отключённый архив


def _module_files():
    mods = {}
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for f in fns:
            if not f.endswith(".py"):
                continue
            path = os.path.join(dp, f)
            rel = os.path.relpath(path, ROOT)[:-3].replace(os.sep, ".")
            if rel.endswith(".__init__"):
                mods[rel[: -len(".__init__")]] = path
            else:
                mods[rel] = path
    return mods


def _top_level_names(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    names, star = set(), False
    for n in tree.body:
        for sub in ast.walk(n) if isinstance(n, (ast.If, ast.Try)) else [n]:
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(sub.name)
            elif isinstance(sub, ast.Assign):
                for t in sub.targets:
                    for x in ast.walk(t):
                        if isinstance(x, ast.Name):
                            names.add(x.id)
            elif isinstance(sub, (ast.AnnAssign, ast.AugAssign)) and isinstance(sub.target, ast.Name):
                names.add(sub.target.id)
            elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                for a in sub.names:
                    if a.name == "*":
                        star = True
                    names.add((a.asname or a.name).split(".")[0])
    return names, star


def check(root_filter=None):
    mods = _module_files()
    cache, problems = {}, []
    for name, path in sorted(mods.items()):
        tree = ast.parse(open(path, encoding="utf-8").read())
        is_pkg = os.path.basename(path) == "__init__.py"
        pkg = name if is_pkg else name.rpartition(".")[0]
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                if n.level:
                    parts = pkg.split(".") if pkg else []
                    base = ".".join(parts[: len(parts) - (n.level - 1)]) if n.level > 1 else pkg
                    target = f"{base}.{n.module}" if n.module else base
                else:
                    target = n.module or ""
                head = target.split(".")[0]
                local = any(m == head or m.startswith(head + ".") for m in mods)
                if not local:
                    continue
                if target not in mods:
                    problems.append(f"{name}:{n.lineno}: нет модуля {target}")
                    continue
                if target not in cache:
                    cache[target] = _top_level_names(mods[target])
                names, star = cache[target]
                for a in n.names:
                    if a.name == "*" or star:
                        continue
                    if a.name not in names and f"{target}.{a.name}" not in mods:
                        problems.append(f"{name}:{n.lineno}: в {target} нет имени {a.name}")
            elif isinstance(n, ast.Import):
                for a in n.names:
                    head = a.name.split(".")[0]
                    if any(m == head or m.startswith(head + ".") for m in mods) and a.name not in mods:
                        problems.append(f"{name}:{n.lineno}: нет модуля {a.name}")
    return problems


if __name__ == "__main__":
    probs = check()
    print("\n".join(probs) if probs else "imports OK")
    sys.exit(1 if probs else 0)
