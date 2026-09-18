# -*- coding: utf-8 -*-
"""Гео-файлы для приложения раздаются со своего узла.

Владелец открыл Happ и увидел «Не удалось скачать файл» на geosite.dat и
geoip.dat, а на экране правил — «Гео-файлы повреждены или отсутствуют». Вместе
с ними не работало ничего: ни сплита, ни нашего DNS, ни фильтров, ни интернета
через Xray. Приложение считает профиль испорченным целиком.

Причина простая: по умолчанию оно тянет их с GitHub, а он из России не
открывается.

Нашим правилам эти файлы не нужны — у нас обычные домены и сети, никаких
geosite:/geoip:. Но требует их приложение, и спорить бесполезно. Поэтому качаем
мы (бот ходит наружу через Германию) и раздаём со своего узла.
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import subscription as S                           # noqa: E402
import happ_routing                                # noqa: E402
import monitor                                     # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


class Req:
    def __init__(self, name):
        self.match_info = {"name": name}
        self.headers = {"Accept": "*/*"}
        self.remote = "203.0.113.9"


async def main():
    await db.connect()

    print("=== профиль называет НАШ адрес, а не GitHub ===")
    await db.set_setting("xray_sub_base", "https://узел:2096")
    prof = await happ_routing.profile()
    check("указан адрес гео-сайтов", "Geositeurl" in prof, str(prof.get("Geositeurl")))
    check("указан адрес гео-айпи", "Geoipurl" in prof, str(prof.get("Geoipurl")))
    check("это наш узел, а не GitHub",
          "github" not in (prof.get("Geositeurl", "") + prof.get("Geoipurl", "")).lower(),
          "с GitHub из России не скачать")
    check("путь тот же, что раздаёт узел",
          prof.get("Geositeurl", "").endswith("/geo/geosite.dat") and
          prof.get("Geoipurl", "").endswith("/geo/geoip.dat"))

    print()
    print("=== узел отдаёт только эти два файла ===")
    S.GEO_DIR = "/tmp/geo_test"
    os.makedirs(S.GEO_DIR, exist_ok=True)
    with open(os.path.join(S.GEO_DIR, "geosite.dat"), "wb") as f:
        f.write(b"x" * 4096)

    check("готовый файл отдаётся", bool(S.geo_path("geosite.dat")))
    check("которого нет — не отдаётся", not S.geo_path("geoip.dat"),
          "приложение попробует снова, лишнего чужому знать незачем")

    for bad in ("../../etc/passwd", "wg0.conf", "", "geosite.dat/../x"):
        if S.geo_path(bad):
            check("чужое имя не отдаётся: %r" % bad, False, "отдали")
            break
    else:
        check("чужие имена не отдаются", True,
              "имя сверяется со списком, а не берётся из запроса")

    # Отдаём поток кусками, а не FileResponse. Тот зовёт `loop.sendfile`, а
    # поверх TLS его нет: asyncio уходит в запасной путь и падает там с
    # AttributeError, обрывая передачу на середине. Человек видит «не удалось
    # скачать файл», а без гео-файлов приложение считает профиль испорченным
    # целиком — не работает ничего. Проверяем текстом, потому что проверить
    # поведением можно только с настоящим сокетом и настоящим TLS.
    src = open("/app/subscription.py", encoding="utf-8").read()
    part = src[src.index("async def handle_geo"):][:2200]
    # Считаем только код: пояснение, ПОЧЕМУ мы ушли от FileResponse, обязано
    # его называть, и запрещать это было бы глупо.
    code = chr(10).join(l for l in part.splitlines()
                        if not l.lstrip().startswith("#"))
    check("через FileResponse не отдаём", "FileResponse" not in code,
          "он падает на TLS и рвёт закачку")
    check("отдаём потоком", "StreamResponse" in part)
    check("и кусками, а не целиком в память", "f.read(" in part,
          "двадцать семь мегабайт на двоих, а памяти на узле два гигабайта")

    print()
    print("=== обрубок не кладётся на место целого ===")
    with open(os.path.join(S.GEO_DIR, "geoip.dat"), "wb") as f:
        f.write(b"error page")
    r = await S.handle_geo(Req("geoip.dat"))
    check("огрызок не отдаётся", r.status == 404,
          "иначе приложение снова скажет «повреждены»")
    check("порог скачивания заметно больше огрызка",
          monitor.GEO_MIN_BYTES >= 100 * 1024,
          "сейчас %d б" % monitor.GEO_MIN_BYTES)

    print()
    print("=== качается не чаще, чем надо ===")
    check("раз в сутки", monitor.GEO_REFRESH_HOURS >= 24,
          "списки обновляются ежедневно, а весят мегабайты")
    check("берём из известного места",
          "v2ray-rules-dat" in monitor.GEO_SOURCE)

    for f in os.listdir(S.GEO_DIR):
        os.remove(os.path.join(S.GEO_DIR, f))
    await db.set_setting("xray_sub_base", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
