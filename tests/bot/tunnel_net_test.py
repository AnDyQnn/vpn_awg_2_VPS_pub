# -*- coding: utf-8 -*-
"""Адреса узла не уходят мимо туннеля вместе с домашней сетью.

Владелец прислал конфиг, который приложение собрало из нашего профиля. В нём
правило: `10.0.0.0/8 → direct`. Домашняя сеть, роутер, принтер — всё верно.
Только внутри этой восьмёрки лежит и наш собственный `10.13.13.0/24`: узел, его
резолвер и страница отказа.

Отсюда и жалоба «меня не редиректнуло на блок страничку». Фильтр честно
отвечает на закрытый домен адресом `10.13.13.1`, браузер идёт по нему — и
правило отправляет его МИМО туннеля, в физическую сеть, где такого адреса нет.
Вместо объяснения, почему сайт закрыт, человек видит ошибку соединения и решает,
что сломан VPN.

Проверяем арифметику подсетей, а не текст: домашнее осталось домашним, наше
перестало быть домашним, и ни один кусок не потерялся.
"""
import asyncio
import ipaddress
import sys

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import happ_routing as H                           # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def covered(nets, addr):
    """Попадает ли адрес хоть под одну из сетей списка."""
    a = ipaddress.ip_address(addr)
    for n in nets:
        try:
            if a in ipaddress.ip_network(n):
                return True
        except ValueError:
            pass
    return False


async def main():
    await db.connect()
    prof = await H.profile()
    direct = prof["DirectIp"]

    print("=== что идёт мимо туннеля ===")
    check("домашняя сеть — мимо", covered(direct, "192.168.1.1"))
    check("десятка дома — мимо", covered(direct, "10.0.0.1"),
          "роутер и принтер должны остаться у человека")
    check("соседний адрес десятки — мимо", covered(direct, "10.200.0.5"))
    check("link-local — мимо", covered(direct, "169.254.1.1"))

    print()
    print("=== а что остаётся за туннелем ===")
    check("узел не уходит мимо", not covered(direct, "10.13.13.1"),
          "иначе страница отказа недостижима")
    check("и другие адреса туннеля тоже",
          not covered(direct, "10.13.13.77"),
          "там же живут имена вроде дом.vpn")
    # Приложение раскладывает правила как «block, direct, proxy» — прямое
    # считается РАНЬШЕ туннельного (`routingOrder` в его отчёте). Поэтому одной
    # записью в ProxyIp делу не помочь: спасает проверка выше, что перекрытия
    # больше нет. Эта запись — объявление замысла, а не защита.
    check("замысел объявлен", H.TUNNEL_NET in (prof.get("ProxyIp") or []),
          "видно глазами в конфиге, который присылает человек")

    print()
    print("=== соседи по восьмёрке не пострадали ===")
    # Вырезаем ровно /24 и ничего больше: 10.13.12.x и 10.13.14.x — чужие.
    check("адрес до нашей сети — мимо", covered(direct, "10.13.12.9"))
    check("адрес после нашей сети — мимо", covered(direct, "10.13.14.9"))

    print()
    print("=== арифметика сошлась ===")
    tun = ipaddress.ip_network(H.TUNNEL_NET)
    tens = [ipaddress.ip_network(n) for n in direct
            if ipaddress.ip_network(n).subnet_of(ipaddress.ip_network("10.0.0.0/8"))]
    total = sum(n.num_addresses for n in tens)
    check("из десятки вычли ровно нашу сеть",
          total == ipaddress.ip_network("10.0.0.0/8").num_addresses - tun.num_addresses,
          "осталось %d адресов" % total)
    check("куски не перекрываются",
          len(set(str(n) for n in tens)) == len(tens))


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
