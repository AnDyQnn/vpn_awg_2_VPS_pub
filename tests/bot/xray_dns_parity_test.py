# -*- coding: utf-8 -*-
"""Выбор DNS у Xray такой же, как у амнезии.

При выдаче ключа AmneziaWG человек выбирает резолвер: обычный или с резкой
рекламы. На Xray этого выбора не было — в профиль жёстко шёл один адрес, и
человек, перейдя на второй протокол, молча терял резку рекламы. Понять, почему
она вернулась, он не мог ничем: у него всё «включено».

Проверяется именно перенос выбора, а не сам факт наличия поля.
"""
import asyncio

from database import db
import happ_routing as hr


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'dp-%'")
    for uid, name in (("dp-1", "СРезкой"), ("dp-2", "Обычный")):
        await db.execute(
            "INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
            name, uid)

    import acl
    import dnsnames

    async def ips():
        return {"dp-1": "10.13.13.41", "dp-2": "10.13.13.42"}
    acl.peer_ip_map = ips

    async def upstreams():
        # Ровно то, что лежит в конфигах: у первого AdGuard, у второго обычный.
        return {"10.13.13.41": "94.140.14.14", "10.13.13.42": "1.1.1.1"}
    dnsnames.client_upstreams = upstreams

    print("=== выбор человека переносится в профиль ===")
    p1 = await hr.profile("dp-1")
    p2 = await hr.profile("dp-2")
    print("  с резкой рекламы:", p1["DomesticDNSIP"])
    print("  обычный:         ", p2["DomesticDNSIP"])
    assert p1["DomesticDNSIP"] == "94.140.14.14", p1["DomesticDNSIP"]
    assert p2["DomesticDNSIP"] == "1.1.1.1", p2["DomesticDNSIP"]
    print("каждому свой резолвер: ок")

    print("\n=== туннельный DNS при этом всегда наш ===")
    # Иначе узел не видит запросов, и человек на Xray остаётся без фильтров и
    # без внутренних имён — хотя у него всё «включено».
    for p in (p1, p2):
        assert p["RemoteDNSIP"] == hr.TUNNEL_DNS, p["RemoteDNSIP"]
    print("  ", p1["RemoteDNSIP"])
    print("фильтры и внутренние имена продолжают работать: ок")

    print("\n=== нет конфига — берём обычный, а не падаем ===")
    async def nothing():
        return {}
    dnsnames.client_upstreams = nothing
    p3 = await hr.profile("dp-1")
    assert p3["DomesticDNSIP"] == hr.DIRECT_DNS_DEFAULT, p3["DomesticDNSIP"]

    async def boom():
        raise RuntimeError("узел молчит")
    dnsnames.client_upstreams = boom
    p4 = await hr.profile("dp-1")
    assert p4["DomesticDNSIP"] == hr.DIRECT_DNS_DEFAULT
    print("  ", p4["DomesticDNSIP"])
    print("удобство не роняет профиль целиком: ок")

    print("\n=== без ключа (общий профиль) тоже собирается ===")
    p5 = await hr.profile(None)
    assert p5["DomesticDNSIP"] == hr.DIRECT_DNS_DEFAULT
    assert p5["DirectIp"], "общие исключения обязаны быть на месте"
    print("ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'dp-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
