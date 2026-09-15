# -*- coding: utf-8 -*-
"""Из сообщения должен быть выход. Всегда.

Владелец нашёл тупик руками: переименовал имя, получил «✅ готово» и упёрся —
ни кнопки, ни экрана, только листать чат вверх. Сказал: плохо проверял. Верно,
проверял выборочно и глазами.

Проверил как следует — по всему боту таких мест оказалось девятнадцать.
Чинить их по одному, по мере того как на них натыкаются, бессмысленно: на
следующей неделе появится двадцатое.

Поэтому проверка на весь исходник сразу. Сообщение считается тупиком, если:
  • отправлено владельцу (клиенту хватает его собственного меню),
  • без клавиатуры,
  • и сразу за ним не открывается никакой экран.

Два исключения записаны поимённо и объяснены. Любое новое такое место обрушит
эту проверку с указанием файла и строки.
"""
import io
import os
import re
import sys

BOT = "/app"

# Единственные законные сообщения без выхода. Каждое — с причиной.
ALLOWED = {
    # Сообщение о ходе дела: редактируется в «готово» и удаляется через 4 сек.
    ("handlers_admin.py", "Создаю архив"),
    # Одна только ссылка: её выделяют и копируют, кнопка мешает попасть по
    # тексту. Выход даёт следующее сообщение, идущее сразу за ним.
    ("handlers_xray.py", "text=link"),
    # Ссылка подписки — её тоже выделяют и копируют. Идёт сразу за
    # объяснением, у которого кнопки есть.
    # Сообщение с одной только ссылкой: её выделяют целиком одним касанием,
    # и кнопки под ней мешают попасть по тексту. Выход даёт подсказка,
    # которая идёт сразу следом.
    ("handlers_client.py", "text=link"),
}

SCREEN = re.compile(r"(_screen|_menu|show_screen|return_to_main|handout|_picker)\s*\(")
CALL = re.compile(r"await (?:context|app|self)\.bot\.send_message\((?:[^()]|\([^()]*\))*\)")
TO_CLIENT = re.compile(r"chat_id=(tid|tg_id|user_id)\b|send_message\((tid|user_id)\b")

files = sorted(f for f in os.listdir(BOT)
               if f.startswith(("handlers", "filters")) and f.endswith(".py"))
print("=== проверено файлов:", len(files), "===")

dead = []
excused = 0
for name in files:
    text = io.open(os.path.join(BOT, name), encoding="utf-8").read()
    lines = text.split("\n")
    for m in CALL.finditer(text):
        call = m.group(0)
        if "reply_markup" in call:
            continue
        start = text[:m.start()].count("\n")
        end = start + call.count("\n")
        if SCREEN.search("\n".join(lines[end + 1:end + 7])):
            continue
        if TO_CLIENT.search(call):
            continue
        flat = re.sub(r"\s+", " ", call)
        if any(name == f and mark in flat for f, mark in ALLOWED):
            excused += 1
            continue
        dead.append((name, start + 1, flat[:90]))

print("  сообщений без выхода по уважительной причине:", excused)
if dead:
    print()
    print("НАЙДЕНЫ ТУПИКИ — сообщение приходит, а нажать нечего:")
    for name, line, snippet in dead:
        print("  %s:%d" % (name, line))
        print("      %s" % snippet)
    print()
    print("Добавьте клавиатуру (utils.exit_kb) или откройте экран сразу после.")
    print("Если выход действительно не нужен — впишите место в ALLOWED с причиной.")
    sys.exit(1)


# --- переходы, которых нет ------------------------------------------------
# Кнопка с несуществующим переходом молча ничего не делает. Это тот же тупик,
# только хуже: он выглядит как рабочая кнопка. Сверяем каждый переход в
# экранах с разбором нажатий в bot.py.
print()
print("=== кнопки ведут туда, где кто-то есть ===")
router = io.open(os.path.join(BOT, "bot.py"), encoding="utf-8").read()
STATIC = re.compile(r'callback_data="([a-z_]+)"')
# Часть нажатий разбирается не по точному совпадению, а по началу строки:
# startswith("proto_off_") ловит и proto_off_awg, и proto_off_xray. Без этого
# сторож ругался бы на исправные кнопки — а проверка, которая ругается зря,
# приучает себя не читать.
PREFIXES = tuple(re.findall(r'startswith\("([a-z_]+)"\)', router))
unknown = []
for name in files:
    text = io.open(os.path.join(BOT, name), encoding="utf-8").read()
    for m in STATIC.finditer(text):
        target = m.group(1)
        if f'"{target}"' in router or f"'{target}'" in router:
            continue
        if target.startswith(PREFIXES):
            continue
        # Переходы, собираемые из кусков, проверить статически нельзя —
        # их ловит разбор с префиксами в самом боте.
        unknown.append((name, text[:m.start()].count(chr(10)) + 1, target))

if unknown:
    print("  НАЙДЕНЫ КНОПКИ В НИКУДА:")
    for name, line, target in unknown:
        print("    %s:%d -> %s" % (name, line, target))
    print("  Такая кнопка выглядит рабочей и молча ничего не делает.")
    sys.exit(1)
print("  все переходы разбираются: ок")

print()
print("ВСЁ ПРОШЛО")
