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
f._load_domains()

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

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
