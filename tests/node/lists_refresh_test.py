# -*- coding: utf-8 -*-
"""Раз в 12 часов узел перекачивает списки всех включённых категорий.

И личных, и общих. Общие сюда раньше не попадали: их список качался один раз,
при раскладке, и если та загрузка срывалась, категория оставалась пустой
навсегда — включённой на экране и ничего не фильтрующей.

Берём ровно тот кусок run_api.sh, который решает, что качать, и прогоняем его
на настоящем файле состояния.
"""
import io
import json
import os
import re
import subprocess

src = io.open("/run_api.sh", encoding="utf-8").read()
m = re.search(r"CATS=\"\$\(/opt/venv/bin/python3 - <<'PY'\n(.*?)\nPY\n", src, re.S)
assert m, "в run_api.sh не нашёлся выбор категорий для перекачки"
picker = m.group(1)

STATE = "/etc/amnezia/amneziawg/dns_filter.json"
os.makedirs(os.path.dirname(STATE), exist_ok=True)


def cats(state):
    json.dump(state, open(STATE, "w"))
    return subprocess.run(["/opt/venv/bin/python3", "-c", picker],
                          capture_output=True, text=True).stdout.split()


got = cats({"clients": {"10.13.13.5": ["social", "ads"]}, "common": ["adult"]})
print(" ", got)
assert got == ["ads", "adult", "social"], got
print("личные и общие — все в перекачке: ок")

got = cats({"clients": {}, "common": ["gambling"]})
assert got == ["gambling"], got
print("только общие — тоже качаются: ок")

got = cats({"clients": {}, "common": []})
assert got == [], got
print("ничего не включено — качать нечего: ок")

print("\nВСЁ ПРОШЛО")
