# -*- coding: utf-8 -*-
"""Номер инцидента на странице совпадает с записанным в журнал.

Номер человек копирует со страницы и присылает в поддержку, а владелец ищет по
нему инцидент. Значит он обязан быть одним и тем же в двух местах: в журнале
узла и на странице.

Ловушка в том, что это разные моменты времени. Браузер спрашивает адрес, узел
записывает попытку — а страницу человек открывает секундой позже, иногда уже в
следующей минуте. Номер считается из адреса, домена и минуты, поэтому пересчёт
на странице дал бы ДРУГОЙ номер, которого нет ни в одном журнале.

Проверяется:
  • номер, выданный при записи, переживает смену минуты;
  • он же лежит в журнале;
  • для разных пар «адрес + домен» номера разные;
  • номер не зависит от запуска процесса — иначе кэш и база разошлись бы после
    перезапуска.
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, "/app")

import dnsfilter                                   # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


dnsfilter.HITS_FILE = "/tmp/hits_test.jsonl"
for path in (dnsfilter.HITS_FILE,):
    if os.path.exists(path):
        os.unlink(path)
dnsfilter._hit_seen.clear()
dnsfilter._hit_refs.clear()

print("=== номер переживает смену минуты ===")
dnsfilter.record_hit("10.13.13.7", "vk.com", "social")
saved = dnsfilter._hit_refs.get(("10.13.13.7", "vk.com"))
check("номер выдан", bool(saved), str(saved))

# Пересчёт «сейчас», как делала бы страница, открытая в следующую минуту.
later = dnsfilter.hit_ref("10.13.13.7", "vk.com", time.time() + 120)
check("пересчёт даёт другой номер", later != saved,
      "%s против %s" % (later, saved))
check("страница возьмёт сохранённый",
      dnsfilter._hit_refs.get(("10.13.13.7", "vk.com")) == saved)

print()
print("=== он же в журнале ===")
rows = [json.loads(l) for l in io.open(dnsfilter.HITS_FILE, encoding="utf-8")
        if l.strip()]
check("запись одна", len(rows) == 1, str(len(rows)))
check("номер тот же", rows and rows[0].get("ref") == saved,
      rows[0].get("ref") if rows else "—")

print()
print("=== разные пары — разные номера ===")
dnsfilter.record_hit("10.13.13.8", "vk.com", "social")
other = dnsfilter._hit_refs.get(("10.13.13.8", "vk.com"))
check("у другого человека свой", other != saved, "%s / %s" % (saved, other))
dnsfilter.record_hit("10.13.13.7", "ok.ru", "social")
another = dnsfilter._hit_refs.get(("10.13.13.7", "ok.ru"))
check("у другого домена свой", another not in (saved, other))

print()
print("=== номер не зависит от запуска процесса ===")
# Считается устойчивым хешем, а не встроенным: встроенный меняется от запуска
# к запуску, и кэш разошёлся бы с базой после перезапуска узла.
again = dnsfilter.hit_ref("10.13.13.7", "vk.com", 1757930400)
expect = dnsfilter.hit_ref("10.13.13.7", "vk.com", 1757930400)
check("одинаковый при тех же данных", again == expect, again)
check("вид пригоден для переписывания вручную",
      len(again) == 9 and again[4] == "-", again)

print()
print("=== повтор в течение минуты не плодит записей ===")
before = len(io.open(dnsfilter.HITS_FILE, encoding="utf-8").readlines())
dnsfilter.record_hit("10.13.13.7", "vk.com", "social")
after = len(io.open(dnsfilter.HITS_FILE, encoding="utf-8").readlines())
check("записей столько же", before == after,
      "одну страницу браузер спрашивает пачкой поддоменов")

os.unlink(dnsfilter.HITS_FILE)
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
