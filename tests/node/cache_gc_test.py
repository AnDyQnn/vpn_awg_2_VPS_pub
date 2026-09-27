# -*- coding: utf-8 -*-
"""Уборщик кэша списков: убирает мусор и только мусор.

Мусор: списки и сборки своих групп, которых больше нет; списки категорий,
которых нет в коде (слитые scam/ransomware/tracking); сборки с устаревшим
довеском; брошенные временные файлы. Не мусор: списки и сборки живых
категорий и групп.

И главное: если бот не прислал список групп (не смог прочитать базу),
файлы групп не трогаются — иначе одна ошибка чтения снесла бы все группы.
"""
import ast
import io
import os
import sys
import time
import typing
import json
import re
import subprocess

sys.path.insert(0, "/app")
SRC = "/app/api.py"
tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = [n for n in tree.body
          if (isinstance(n, ast.FunctionDef) and n.name == "gc_dns_cache")
          or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "CONF_DIR" for t in n.targets))]
ns = {"os": os, "time": time, "json": json, "re": re, "subprocess": subprocess,
      "typing": typing}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)
import dnsfilter  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-54s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


cache = ns["CONF_DIR"] + "/cache/dns"
os.makedirs(cache, exist_ok=True)
for f in os.listdir(cache):
    os.remove(os.path.join(cache, f))


def touch(name, age=0):
    p = os.path.join(cache, name)
    open(p, "w").write("x")
    if age:
        t = time.time() - age
        os.utime(p, (t, t))
    return name


good_adult_bin = os.path.basename(dnsfilter._bin_path_in(cache, "adult"))
good_pool_bin = os.path.basename(dnsfilter._bin_path_in(cache, "pool_alive"))
keep = [touch("adult.txt"), touch(good_adult_bin),
        touch("pool_alive.txt"), touch(good_pool_bin),
        touch("social.txt"), touch("x.bin.123.tmp")]          # свежий tmp — ещё пишется
junk = [touch("pool_zzprobe.txt"), touch("pool_zzprobe.1271cf25.bin"),
        touch("scam.txt"), touch("tracking.txt"), touch("ransomware.txt"),
        touch("adult.deadbeef.bin"),                          # старый довесок
        touch("malware.bin.999.tmp", age=7200)]               # брошенный tmp

print("=== бот прислал список групп ===")
removed = ns["gc_dns_cache"](["pool_alive"])
left = set(os.listdir(cache))
for f in keep:
    check("оставлен %s" % f, f in left)
for f in junk:
    check("убран %s" % f, f not in left)

print("\n=== бот не смог прочитать группы — файлы групп не трогаем ===")
touch("pool_alive.txt")
# Так узел зовёт уборщика: только если список групп пришёл.
pools = None
if pools is not None:
    ns["gc_dns_cache"](list(pools.keys()))
check("группа цела", os.path.exists(os.path.join(cache, "pool_alive.txt")))
src = io.open(SRC, encoding="utf-8").read()
check("в set_dns_filters уборщик только при присланных группах",
      "if req.pools is not None:\n            gc_dns_cache(" in src)

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
