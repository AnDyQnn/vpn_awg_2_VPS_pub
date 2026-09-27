# -*- coding: utf-8 -*-
"""В текстах бота нет буквальных «\\n» — только настоящие переносы строк.

Экран выдачи ключа показывал человеку «Имя: SerEga_1\\n\\n🔷 Будет выдан…»:
при правке в строку попал обратный слеш с буквой вместо переноса. Питон это
не ловит — это обычная строка. Ловим здесь: обратный слеш с «n» допустим
только в регулярных выражениях.
"""
import ast
import glob

BS_N = chr(92) + "n"
bad = []
for path in sorted(glob.glob("/app/*.py")):
    name = path.rsplit("/", 1)[1]
    # Сам тест и подмонтированные рядом файлы узла — не тексты бота.
    if name.endswith("_test.py") or name.startswith("node_") or name.endswith("test.py"):
        continue
    try:
        tree = ast.parse(open(path, encoding="utf-8").read())
    except SyntaxError:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and BS_N in node.value:
            v = node.value
            # Регулярка: рядом другие экранирования или классы символов.
            if any(t in v for t in (chr(92) + "s", "[^", chr(92) + "d", "(?")):
                continue
            bad.append("%s:%d %r" % (path.rsplit("/", 1)[1], node.lineno, v[:60]))

for b in bad:
    print("  ", b)
assert not bad, "буквальный \\n в тексте: человек увидит слеш вместо переноса"
print("буквальных переносов нет: ок")
print("\nВСЁ ПРОШЛО")
