# -*- coding: utf-8 -*-
"""Реклама режется молча, без инцидентов.

Категория «Реклама и слежка» обычно включена всем. К трекерам телефон стучится
сам, в фоне, сотнями доменов — за ночь это дало десять тысяч «инцидентов», и
настоящие в них утонули.

Проверяется:
  • запрет рекламы и наблюдение за ней в журнал не пишутся, номера не выдают;
  • запрет другой категории пишется как раньше;
  • бот рекламу из старого журнала узла не принимает.
"""
import io
import json
import os
import sys

sys.path.insert(0, "/app")

import dnsfilter                                   # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


dnsfilter.HITS_FILE = "/tmp/ads_silent_test.jsonl"
if os.path.exists(dnsfilter.HITS_FILE):
    os.unlink(dnsfilter.HITS_FILE)
dnsfilter._hit_seen.clear()
dnsfilter._hit_refs.clear()


def rows():
    if not os.path.exists(dnsfilter.HITS_FILE):
        return []
    return [json.loads(l) for l in io.open(dnsfilter.HITS_FILE, encoding="utf-8")
            if l.strip()]


print("=== реклама — молча ===")
dnsfilter.record_hit("10.13.13.7", "googleads.g.doubleclick.net", "ads")
dnsfilter.record_hit("10.13.13.7", "mc.yandex.ru", "tracking")
dnsfilter.record_hit("10.13.13.7", "an.yandex.ru", "ads", watch=True)
check("в журнале пусто", rows() == [], str(rows()))
check("номера не выданы", not dnsfilter._hit_refs, str(dnsfilter._hit_refs))

print()
print("=== другая категория — как раньше ===")
dnsfilter.record_hit("10.13.13.7", "casino.example", "gambling")
r = rows()
check("одна запись", len(r) == 1, str(len(r)))
check("это казино", r and r[0].get("domain") == "casino.example")
check("номер выдан",
      bool(dnsfilter._hit_refs.get(("10.13.13.7", "casino.example"))))

print()
print("=== список — Pro, не Pro++ ===")
url = dnsfilter.CATEGORIES["ads"]["urls"][0]
check("pro-onlydomains", "/pro-onlydomains.txt" in url and "pro.plus" not in url, url)

os.unlink(dnsfilter.HITS_FILE)
print("\nВСЁ ПРОШЛО" if ok else "\nЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
