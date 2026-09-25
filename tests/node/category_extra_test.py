# -*- coding: utf-8 -*-
"""Встроенные дополнения категорий работают и без скачанных списков.

Внешние списки собраны под западный интернет: во «Соцсетях» не было ни
ВКонтакте, ни Одноклассников, в «Торрентах» — rutor и nnmclub, в «Видео» —
rutube и даже самого youtube.com, в «Крипте» — Bybit. Владелец закрывал
категорию, а сайт открывался. Дополнение лежит в коде и действует всегда.
"""
import sys
import tempfile

sys.path.insert(0, "/app")
import dnsfilter  # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-44s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


dnsfilter.CACHE_DIR = tempfile.mkdtemp()     # списков нет вовсе
f = dnsfilter.Filters()
IP = "10.13.13.7"
f.clients = {IP: ["social", "torrent", "streaming", "crypto"]}
f._load_domains(sync=True)

for name, cat in (("vk.com", "social"), ("m.vk.com", "social"), ("ok.ru", "social"),
                  ("sun9-1.userapi.com", "social"), ("x.com", "social"),
                  ("twitter.com", "social"), ("instagram.com", "social"),
                  ("rutor.info", "torrent"), ("nnmclub.to", "torrent"),
                  ("hdrezka.ag", "torrent"), ("rutube.ru", "streaming"),
                  ("www.youtube.com", "streaming"), ("vkvideo.ru", "streaming"),
                  ("bybit.com", "crypto"), ("www.binance.com", "crypto")):
    got = f.blocked(IP, name)
    check("%s → %s" % (name, cat), got == cat, got)

print("\n=== лишнего не закрывают ===")
for name in ("ya.ru", "gosuslugi.ru", "web.telegram.org", "t.me", "mail.ru",
             "e.mail.ru", "wikipedia.org"):
    got = f.blocked(IP, name)
    check("%s открыт" % name, got is None, got)

print("\n=== у кого категорий нет — ничего не закрыто ===")
check("vk.com другому", f.blocked("10.13.13.8", "vk.com") is None)

print("\n=== Twitter — в соцсетях, а не в видео ===")
urls = " ".join(dnsfilter.CATEGORIES["streaming"]["urls"])
check("в «Видео» нет списка twitter", "twitter" not in urls, urls)
check("в «Соцсетях» есть список twitter",
      "twitter" in " ".join(dnsfilter.CATEGORIES["social"]["urls"]))

print("\n=== загрузчик: построчно, по корзинам — и находит всё ===")
import os  # noqa: E402
import random  # noqa: E402
names = ["s%d-%d.example" % (i, random.randint(0, 9)) for i in range(20000)]
path = os.path.join(dnsfilter.CACHE_DIR, "adult.txt")
with open(path, "w") as fh:
    fh.write("# комментарий\n\n")
    for i, n in enumerate(names):
        fh.write(("0.0.0.0 %s\n" if i % 2 else "%s\n") % n)
    fh.write("0.0.0.0 %s\n" % names[0])          # повтор
g = dnsfilter.Filters()
g.clients = {IP: ["adult"]}
g._load_domains(sync=True)
arr = g.domains["adult"]
check("все домены найдены", all(g.blocked(IP, n) == "adult" for n in names[:3000]))
check("повторов нет", len(arr) == len(set(names)), "%d / %d" % (len(arr), len(set(names))))
check("массив упорядочен", all(arr[i] < arr[i + 1] for i in range(len(arr) - 1)))
check("чужое не найдено", g.blocked(IP, "not-in-list.example") is None)

print("\n=== в фоне: DNS не ждёт загрузки, обновлённый список подхватывается ===")
import time  # noqa: E402
h = dnsfilter.Filters()
h.clients = {IP: ["adult"]}
t0 = time.time()
h._load_domains()                       # фоном
check("вызов не ждёт загрузки", time.time() - t0 < 0.5, "%.2f с" % (time.time() - t0))
for _ in range(100):
    if "adult" in h.domains and not h._loading:
        break
    time.sleep(0.1)
check("список загрузился в фоне", h.blocked(IP, names[5]) == "adult")
with open(path, "a") as fh:
    fh.write("fresh-after-refresh.example\n")
os.utime(path, (time.time() + 5, time.time() + 5))
h._load_domains()
for _ in range(100):
    if not h._loading and h.blocked(IP, "fresh-after-refresh.example"):
        break
    time.sleep(0.1)
check("обновлённый файл подхвачен без перезапуска",
      h.blocked(IP, "fresh-after-refresh.example") == "adult")
check("старое при этом на месте", h.blocked(IP, names[7]) == "adult")

print("\n=== прежние категории понимаются: слиты в новые ===")
check("scam → опасные", dnsfilter._canon(["scam"]) == ["malware"])
check("ransomware + malware → одна", dnsfilter._canon(["ransomware", "malware"]) == ["malware"])
check("tracking → реклама", dnsfilter._canon(["tracking"]) == ["ads"])
for gone in ("scam", "ransomware", "tracking"):
    check("«%s» больше не отдельная категория" % gone, gone not in dnsfilter.CATEGORIES)
urls = " ".join(dnsfilter.CATEGORIES["malware"]["urls"])
check("в опасных — все семь источников",
      all(x in urls for x in ("malware", "phishing", "ransomware", "scam",
                              "fraud", "redirect", "abuse")))

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
