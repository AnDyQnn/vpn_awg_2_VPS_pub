# -*- coding: utf-8 -*-
"""Своя заглушка как маска входа.

Главное, что здесь проверяется, — что её нельзя выбрать вслепую. Reality ходит
к маске в КАЖДОМ рукопожатии, поэтому маска, которой нет, — это вход, который не
работает ни у кого, и заметить это можно только по жалобам.
"""
import asyncio
import os

from database import db
import xray


def set_domain(value):
    if value:
        os.environ["PUBLIC_DOMAIN"] = value
    else:
        os.environ.pop("PUBLIC_DOMAIN", None)


async def main():
    await db.connect()
    import decoy
    import handlers_pubsub
    import subscription

    # Заглушку держит сервер подписок — у него же и спрашиваем. Поднимать
    # настоящий TLS ради этого незачем: проверяем связку решений, а не сокет.
    def decoy_state(up):
        subscription.decoy_up = lambda: up

    print("=== адрес, куда уводится рукопожатие ===")
    assert xray.dest_addr("avito.ru") == "avito.ru:443"
    assert xray.dest_addr(xray.SELF_DEST) == "127.0.0.1:8444", \
        xray.dest_addr(xray.SELF_DEST)
    print("  чужой сайт →", xray.dest_addr("avito.ru"))
    print("  свой сайт  →", xray.dest_addr(xray.SELF_DEST))
    print("чужой на 443, свой на петлю: ок")

    print("\n=== имя маски берётся из имени узла ===")
    set_domain("")
    assert xray.mask_names(xray.SELF_DEST) == [], \
        "без имени узла у своей маски нет имени вовсе"
    set_domain("example.ru")
    assert xray.mask_names(xray.SELF_DEST) == ["example.ru"], \
        xray.mask_names(xray.SELF_DEST)
    print("  ", xray.mask_names(xray.SELF_DEST))
    print("ровно одно имя — то, на которое выписан сертификат: ок")

    print("\n=== выбрать вслепую нельзя ===")
    set_domain("")
    ok, why = xray.self_mask_ready()
    print("  без имени:", ok, why)
    assert not ok and "имени" in why

    set_domain("example.ru")
    decoy_state(False)
    ok, why = xray.self_mask_ready()
    print("  заглушка лежит:", ok, why)
    assert not ok and "заглушка" in why

    decoy_state(True)
    ok, why = xray.self_mask_ready()
    print("  всё на месте:", ok, why or "—")
    assert ok, why
    print("оба условия проверяются порознь: ок")

    print("\n=== выбранная маска, ставшая непригодной, не роняет вход ===")
    await db.set_setting("xray_dest", xray.SELF_DEST)
    set_domain("")
    ways = await xray.entries()
    print("  входы:", ways)
    assert ways[0][1] == xray.DEFAULT_DEST, ways
    assert all(mask for _p, mask in ways), "вход без маски собирать нельзя"
    set_domain("example.ru")
    ways = await xray.entries()
    assert ways[0][1] == xray.SELF_DEST, ways
    print("  с именем:", ways)
    print("без имени узла подставляется обычная маска: ок")

    print("\n=== запасные входы маску с основным не делят ===")
    masks = [m for _p, m in ways]
    assert len(set(masks)) == len(masks), masks
    print("  ", masks)
    print("упадёт одна — остальные живы: ок")

    print("\n=== готовность: чего не хватает, сказано заранее ===")
    await db.set_setting("xray_dest", "avito.ru")
    rows = await xray.readiness()
    for ok, must, name, why, cb in rows:
        print(f"  {'✅' if ok else ('❌' if must else '⚠️')} {name} → {cb}")
    names = [r[2] for r in rows]
    assert "Ключи Reality" in names and "Своё имя узла" in names, names
    must_bad = [r for r in rows if not r[0] and r[1]]
    assert all(r[4] for r in rows), "у каждой строки должно быть куда идти чинить"
    # Имя узла и подписка — желательное, а не обязательное: без них Xray
    # работает, просто хуже. Путать это нельзя, иначе владелец решит, что
    # протокол вообще не заведётся.
    by_name = {r[2]: r[1] for r in rows}
    assert by_name["Своё имя узла"] is False
    assert by_name["Доступ к подписке снаружи"] is False
    assert by_name["Ключи Reality"] is True
    print("  обязательного не хватает:", len(must_bad))
    print("обязательное отделено от желательного: ок")

    print("\n=== ссылка на подписку не ведёт в закрытый порт ===")
    set_domain("example.ru")
    handlers_pubsub.is_on = lambda: False
    base = await xray.subscription_base()
    print("  подписка закрыта:", base)
    assert "example.ru" not in base, \
        "имя без открытого наружу порта — ссылка в никуда"
    handlers_pubsub.is_on = lambda: True
    base = await xray.subscription_base()
    print("  подписка открыта:", base)
    assert base.startswith("https://example.ru"), base
    print("имя годится только вместе с открытой подпиской: ок")

    print("\n=== со своей маской подписка едет по 443 ===")
    # Ради этого всё и затевалось: нестандартные порты режут мобильные
    # операторы, и человек за таким оператором профиль не получал вовсе.
    await db.set_setting("xray_dest", xray.SELF_DEST)
    decoy_state(True)
    base = await xray.subscription_base()
    print("  своя маска:", base)
    assert base == "https://example.ru", base
    assert ":2096" not in base, "порт, который режут, в ссылке остался"

    # А если заглушка не поднята, 443 обещать нельзя: там некому ответить.
    decoy_state(False)
    base = await xray.subscription_base()
    print("  заглушка лежит:", base)
    assert base.endswith(":2096"), base
    print("443 обещаем только когда есть кому отвечать: ок")
    decoy_state(True)

    set_domain("")
    await db.set_setting("xray_dest", xray.DEFAULT_DEST)
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
