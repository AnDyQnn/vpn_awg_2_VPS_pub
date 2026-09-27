# -*- coding: utf-8 -*-
"""Мягкий режим: категория не режется, но обращение отмечается.

Проверяется:
  • сайт из watch-категории НЕ блокируется (blocked() = None), но watched()
    его находит;
  • запись обращения помечена watch=true и не мешает записи запрета;
  • что уже режется общей категорией, в наблюдение не попадает (там запрет);
  • разрешённое владельцем не наблюдается.
"""
import os
import sys
import tempfile

sys.path.insert(0, "/app")
import dnsfilter  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


dnsfilter.CACHE_DIR = tempfile.mkdtemp()
dnsfilter.HITS_FILE = os.path.join(dnsfilter.CACHE_DIR, "hits.jsonl")
open(os.path.join(dnsfilter.CACHE_DIR, "social.txt"), "w").write("vk.com\nok.ru\n")
open(os.path.join(dnsfilter.CACHE_DIR, "gambling.txt"), "w").write("1xbet.com\n")

f = dnsfilter.Filters()
IP = "10.13.13.50"
# social — под мягким контролем; gambling — обычный общий запрет.
f.clients = {}
f.common = ["gambling"]
f.watch = ["social"]
f.allow_common = {"ok.ru"}      # ok.ru владелец открыл вручную
f._load_domains(sync=True)

print("=== мягкая категория не блокируется, но видна ===")
check("vk.com не заблокирован", f.blocked(IP, "vk.com") is None)
check("vk.com попадает под наблюдение", f.watched(IP, "vk.com") == "social")
check("поддомен тоже виден", f.watched(IP, "m.vk.com") == "social")

print("\n=== запрет остаётся запретом ===")
check("1xbet.com заблокирован", f.blocked(IP, "1xbet.com") == "gambling")
check("под наблюдение не дублируется", f.watched(IP, "1xbet.com") is None)

print("\n=== разрешённое не наблюдаем, чужое не трогаем ===")
check("ok.ru открыт владельцем — не наблюдаем", f.watched(IP, "ok.ru") is None)
check("ya.ru вне списков", f.watched(IP, "ya.ru") is None)

print("\n=== запись обращения помечена watch ===")
dnsfilter._hit_seen.clear()
dnsfilter.record_hit(IP, "vk.com", "social", watch=True)
dnsfilter.record_hit(IP, "1xbet.com", "gambling")
import json  # noqa: E402
rows = [json.loads(l) for l in open(dnsfilter.HITS_FILE, encoding="utf-8")]
watch_rows = [r for r in rows if r.get("watch")]
block_rows = [r for r in rows if not r.get("watch")]
check("обращение записано как наблюдение", len(watch_rows) == 1 and watch_rows[0]["domain"] == "vk.com")
check("запрет записан без watch", len(block_rows) == 1 and block_rows[0]["domain"] == "1xbet.com")

print("\n=== наблюдение и запрет одного домена не глушат друг друга ===")
dnsfilter._hit_seen.clear()
dnsfilter.record_hit(IP, "dual.example", "social", watch=True)
dnsfilter.record_hit(IP, "dual.example", "gambling", watch=False)
rows = [json.loads(l) for l in open(dnsfilter.HITS_FILE, encoding="utf-8")]
dual = [r for r in rows if r["domain"] == "dual.example"]
check("обе записи есть", {r["watch"] for r in dual} == {True, False}, [r["watch"] for r in dual])

print("\n=== без watch-категорий метод молчит ===")
g = dnsfilter.Filters()
g.watch = []
check("watched пуст", g.watched(IP, "vk.com") is None)

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
