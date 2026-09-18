# -*- coding: utf-8 -*-
"""Подписи кнопок берутся из плоского конфига проекта.

Переименовать кнопку значило залезть в код: найти нужный
`InlineKeyboardButton` среди восьмисот, поправить строку, собрать образ. А слово
на кнопке — это весь разговор бота с человеком, и менять его хочется ровно
тогда, когда видишь, что оно неудачное.

Теперь между этим стоит одна строка в `config/buttons.json`. Ключ —
`callback_data`: он постоянный и не зависит от того, на каком экране кнопка
нарисована. Значит и переименование действует везде разом — это не побочный
эффект, а смысл.

Проверяем главное: что подмена накрывает ВСЕ кнопки, а не те, о которых мы
вспомнили. Она и сделана подменой конструктора именно поэтому — обойти двадцать
файлов руками значит забыть половину и не заметить.

И отдельно — что сломанный конфиг не роняет бота. Без подписей он живой, без
бота не живёт ничего.
"""
import io
import json
import os
import sys

sys.path.insert(0, "/app")

from telegram import InlineKeyboardButton                # noqa: E402
import button_names                                      # noqa: E402

ok = True
CFG = "/tmp/buttons_test.json"


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def write(obj):
    with io.open(CFG, "w", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False))


print("=== конфига нет — всё как в коде ===")
try:
    os.remove(CFG)
except OSError:
    pass
button_names.PATH = CFG
check("читается без ошибки", button_names.load() == 0)
check("подпись не тронута",
      button_names.label_for("gen_key", "🔑 Создать ключ") == "🔑 Создать ключ")

print()
print("=== заданное имя подставляется ===")
write({"_": "пояснение для человека", "gen_key": "🔑 Новый ключ"})
n = button_names.load()
check("прочитано одно имя", n == 1, "пояснение с подчёркиванием не в счёт")
check("имя подставлено",
      button_names.label_for("gen_key", "🔑 Создать ключ") == "🔑 Новый ключ")
check("чужую кнопку не трогает",
      button_names.label_for("svc_menu", "⚙️ Админка") == "⚙️ Админка")

print()
print("=== подмена накрывает сам конструктор ===")
button_names.apply()
b = InlineKeyboardButton("🔑 Создать ключ", callback_data="gen_key")
check("кнопка создана с новым именем", b.text == "🔑 Новый ключ", b.text)
b2 = InlineKeyboardButton("📊 Дашборд", callback_data="start_dashboard")
check("ненастроенная — как была", b2.text == "📊 Дашборд", b2.text)
b3 = InlineKeyboardButton("Открыть", url="https://example.com")
check("ссылка без callback_data не падает", b3.text == "Открыть")

print()
print("=== повторное применение безвредно ===")
before = InlineKeyboardButton("🔑 Создать ключ", callback_data="gen_key").text
button_names.apply()
button_names.apply()
after = InlineKeyboardButton("🔑 Создать ключ", callback_data="gen_key").text
check("подпись не наслаивается", before == after == "🔑 Новый ключ", after)

print()
print("=== сломанный конфиг не роняет бота ===")
with io.open(CFG, "w", encoding="utf-8") as f:
    f.write("{это не json")
check("разбор пережит", button_names.load() == 0)
check("и подписи вернулись к коду",
      button_names.label_for("gen_key", "🔑 Создать ключ") == "🔑 Создать ключ")
write(["список", "а не словарь"])
check("чужая форма пережита", button_names.load() == 0)
write({"gen_key": ""})
check("пустое имя не применяется", button_names.load() == 0,
      "иначе кнопка осталась бы без подписи вовсе")

print()
print("=== конфиг проекта на месте и разбирается ===")
real = "/app/buttons.json"
if os.path.exists(real):
    try:
        with io.open(real, encoding="utf-8") as f:
            data = json.load(f)
        check("config/buttons.json — плоский словарь", isinstance(data, dict))
        check("значения — строки",
              all(isinstance(v, str) for v in data.values()))
    except Exception as e:
        check("config/buttons.json разбирается", False, str(e))
else:
    check("config/buttons.json примонтирован", False,
          "без него настройка не доедет до бота")

try:
    os.remove(CFG)
except OSError:
    pass

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
