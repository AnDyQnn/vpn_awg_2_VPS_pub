# -*- coding: utf-8 -*-
"""Человек на Xray считается активным.

Отметка «последняя активность» ставилась только по рукопожатию WireGuard. У
Xray рукопожатия нет вовсе — значит человек, сидящий только на нём, вечно
выглядел неактивным.

Ломается от этого не отображение, а автоматика: «не подключался N дней»,
вопросы владельцу и снятие заброшенных ключей. Человек пользуется VPN каждый
день, а система считает его брошенным и однажды отключает.

Признак у него один: живой трафик по адресу-двойнику. Узел его видит, оставалось
перевести адрес в человека.
"""
import asyncio
import time

from database import db


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'ax-%'")
    for uid, name in (("ax-1", "Активный"), ("ax-2", "Молчит")):
        await db.execute(
            "INSERT INTO users (name, uuid, is_active, last_active_at) "
            "VALUES ($1,$2,TRUE, NOW() - INTERVAL '40 days')", name, uid)

    import monitor
    import acl

    async def ips():
        return {"ax-1": "10.13.13.41", "ax-2": "10.13.13.42"}
    acl.peer_ip_map = ips

    async def days(uid):
        row = await db.fetch_val(
            "SELECT EXTRACT(EPOCH FROM (NOW() - last_active_at)) / 86400 "
            "FROM users WHERE uuid=$1", uid)
        return float(row or 0)

    print("=== до отметки оба выглядят брошенными ===")
    for uid in ("ax-1", "ax-2"):
        d = await days(uid)
        print(f"  {uid}: не активен {d:.0f} дней")
        assert d > 30

    print("\n=== узел увидел трафик у одного из них ===")
    # 10.13.13.41 + 128 = 10.13.13.169 — адрес-двойник первого.
    monitor.state_data["addr_seen"] = {"10.13.13.169": time.time()}
    marked = await monitor.mark_xray_active()
    print("  отмечено:", marked)
    assert marked == 1, f"отметили {marked}, а трафик был у одного"

    d1, d2 = await days("ax-1"), await days("ax-2")
    print(f"  ax-1: {d1:.2f} дней · ax-2: {d2:.0f} дней")
    assert d1 < 0.01, "активному не поставили отметку — он так и числится брошенным"
    assert d2 > 30, "молчащему поставили отметку — тогда брошенных не найти вовсе"
    print("  отмечен только тот, у кого был трафик: ок")

    print("\n=== старый трафик активностью не считается ===")
    # Иначе человек, отключившийся неделю назад, числился бы активным вечно:
    # отметки по адресам живут в памяти и сами не пропадают.
    await db.execute(
        "UPDATE users SET last_active_at = NOW() - INTERVAL '40 days' "
        "WHERE uuid='ax-1'")
    monitor.state_data["addr_seen"] = {
        "10.13.13.169": time.time() - monitor.XRAY_SEEN_WINDOW - 60}
    marked = await monitor.mark_xray_active()
    print("  отмечено:", marked)
    assert marked == 0, "просроченный трафик засчитан как активность"
    assert await days("ax-1") > 30
    print("  ок")

    print("\n=== пусто — не ошибка ===")
    monitor.state_data["addr_seen"] = {}
    assert await monitor.mark_xray_active() == 0
    print("  ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'ax-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
