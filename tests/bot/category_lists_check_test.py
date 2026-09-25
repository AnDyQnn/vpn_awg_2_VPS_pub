# -*- coding: utf-8 -*-
"""Сверка видит незагруженный список категории — из контейнера бота.

Сверка запускается в боте, а папка узла видна там как /volumes/wireguard.
Раньше проверка искала файлы по пути узла, не находила их и всегда отвечала
«фильтры никому не включены». Категория без списка ничего не фильтрует, и
именно это она должна была поймать.
"""
import json
import os
import shutil

import node_contract as nc

BASE = "/volumes/wireguard"
CACHE = os.path.join(BASE, "cache", "dns")
os.makedirs(CACHE, exist_ok=True)
STATE = os.path.join(BASE, "dns_filter.json")


def run(state, files):
    shutil.rmtree(CACHE)
    os.makedirs(CACHE)
    for cat, body in files.items():
        open(os.path.join(CACHE, cat + ".txt"), "w").write(body)
    json.dump(state, open(STATE, "w"))
    nc.LINES.clear()
    nc.check_category_lists()
    return nc.LINES[-1]


line = run({"clients": {"10.13.13.5": ["social"]}, "common": ["adult"]},
           {"adult": "0.0.0.0 x.com\n" * 50})
print(" ", line)
assert line.startswith("error") and "social" in line and "adult" not in line, line
print("личная категория без списка — ошибка: ок")

line = run({"clients": {}, "common": ["adult"]}, {})
print(" ", line)
assert line.startswith("error") and "adult" in line, line
print("общая категория без списка — ошибка: ок")

line = run({"clients": {"10.13.13.5": ["social"]}, "common": ["adult"]},
           {"adult": "0.0.0.0 x.com\n" * 50, "social": "0.0.0.0 y.com\n" * 50})
print(" ", line)
assert line.startswith("ok") and "(2)" in line, line
print("всё загружено — ок: ок")

line = run({"clients": {}, "common": []}, {})
assert line.startswith("ok") and "не включены" in line, line
os.remove(STATE)
print("\nВСЁ ПРОШЛО")
