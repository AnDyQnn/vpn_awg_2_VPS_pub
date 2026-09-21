# -*- coding: utf-8 -*-
"""В незакавыченном heredoc обратные кавычки ВЫПОЛНЯЮТСЯ.

Это не теория. В скрипте установки служб стояла строка комментария:

    # видно через `journalctl -u vpn-cleanup`. Ничего не меняет, только читает.

Она лежала внутри heredoc, открытого как <<EOF — без кавычек, потому что рядом
подставляются пути. А раз без кавычек, оболочка выполнила и обратные кавычки:
вывод journalctl целиком уехал в файл службы systemd.

Дальше петля кормила сама себя. systemd ругался на мусорные строки, ругань шла
в журнал, при следующей установке журнал вписывался в файл снова. На боевых
узлах файл службы дорос до 41 МБ и 204 тысяч строк, а журнал systemd — до
194 МБ на диске в десять гигабайт. Со стороны это выглядело как «сборщик мусора
не работает»: место таяло, а виновата была одна пара кавычек.

Поэтому проверка смотрит не на конкретный файл, а на весь класс: любой
незакавыченный heredoc, внутри которого есть обратные кавычки.

Подстановки $(...) при этом разрешены намеренно — ими собирают JSON с датой и
именем узла, и это осознанный приём. Запрет только на обратные кавычки: в
комментарии они оказываются случайно, а как приём их никто не пишет.
"""
import io
import os
import re

ROOT = "/repo"
if not os.path.isdir(ROOT):
    # Вне контейнера — ищем корень от самого теста.
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

SKIP_DIRS = {".git", "node_modules", "__pycache__", "volumes"}
OPEN = re.compile(r"<<-?\s*([\"']?)([A-Za-z_][A-Za-z0-9_]*)\1")

found = []
scanned = 0

for root, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for name in sorted(files):
        if not name.endswith(".sh"):
            continue
        path = os.path.join(root, name)
        try:
            lines = io.open(path, encoding="utf-8", errors="replace").read().split("\n")
        except Exception:
            continue
        scanned += 1
        inside = None          # (метка, закавычена ли, строка открытия)
        for num, line in enumerate(lines, 1):
            if inside is None:
                m = OPEN.search(line)
                if m:
                    inside = (m.group(2), bool(m.group(1)), num)
                continue
            if line.strip() == inside[0]:
                inside = None
                continue
            if not inside[1] and "`" in line:
                rel = os.path.relpath(path, ROOT)
                found.append((rel, num, inside[2], line.strip()[:100]))

print(f"просмотрено скриптов: {scanned}")
assert scanned > 5, "скрипты не нашлись — проверка ничего не проверила"

if found:
    print("\nнайдено выполняемое в heredoc:")
    for rel, num, start, text in found:
        print(f"  {rel}:{num} (heredoc открыт на {start})")
        print(f"      {text}")

assert not found, (
    "в незакавыченном heredoc есть обратные кавычки — оболочка выполнит их "
    "при записи файла. Либо закройте heredoc кавычками (<<'EOF'), либо "
    "уберите обратные кавычки из текста")
print("обратных кавычек в незакавыченных heredoc нет: ок")

print("\nВСЁ ПРОШЛО")
