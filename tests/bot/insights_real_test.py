# -*- coding: utf-8 -*-
"""Подбор на данных, снятых с боевого сервера: обычные люди не должны попадать."""
import asyncio
from database import db
import insights


async def add(uuid, hours_ago, mb_in, mb_out, packets=0, peak=0):
    await db.execute(
        "INSERT INTO traffic_hourly (user_uuid, hour, bytes_in, bytes_out, "
        "packets_in, packets_out, peak_pps, samples) VALUES ($1, "
        "date_trunc('hour', NOW() - ($2 || ' hours')::INTERVAL),$3,$4,$5,$6,$7,240) "
        "ON CONFLICT (user_uuid, hour) DO UPDATE SET bytes_in=$3, bytes_out=$4, "
        "packets_in=$5, packets_out=$6, peak_pps=$7",
        uuid, str(hours_ago), int(mb_in*1048576), int(mb_out*1048576),
        packets//2, packets//2, peak)


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'rl-%'")
    names = {"rl-1": "work2", "rl-2": "Алексей", "rl-3": "теща", "rl-4": "торрент"}
    for u, n in names.items():
        await db.execute("INSERT INTO users (name, uuid) VALUES ($1,$2)", n, u)

    # Реальные пропорции с сервера: отдано сервером (= скачано человеком)
    # в разы больше принятого. Это ОБЫЧНЫЕ люди.
    for h in range(1, 24):
        await add("rl-1", h, 81, 392)      # work2: 1.9 ГБ принято / 9.4 ГБ отдано
        await add("rl-2", h, 55, 1096)     # Алексей: 1.3 / 26.3 ГБ
        await add("rl-3", h, 55, 190)      # тёща
    for h in range(25, 168, 3):            # неделя такой же нормы
        await add("rl-1", h, 81, 392)
        await add("rl-2", h, 55, 1096)
        await add("rl-3", h, 55, 190)

    # А это настоящий торрент: раздаёт почти столько же, пакеты мелкие
    for h in range(1, 24):
        await add("rl-4", h, 700, 800, 5_000_000, peak=6800)
    for h in range(25, 168, 3):
        await add("rl-4", h, 5, 20, 20000, peak=200)

    picks = {p["uuid"]: p for p in await insights.chart_candidates()}
    print("подобраны:", {names[u]: p["reasons"] for u, p in picks.items()})

    for quiet in ("rl-1", "rl-2", "rl-3"):
        assert quiet not in picks, f"{names[quiet]} не должен попадать — он просто качает"
    print("обычные люди в подбор не попали: ок")

    assert "rl-4" in picks, "торрент обязан попасть"
    r = picks["rl-4"]["reasons"]
    assert any("мелкие пакеты" in x for x in r) and any("раздаёт" in x for x in r), r
    print("торрент пойман по пакетам и по раздаче: ок")

    # «на связи» само по себе в подбор не тащит
    only_online = {p["uuid"] for p in await insights.chart_candidates(["rl-1", "rl-3"])}
    assert "rl-1" not in only_online and "rl-3" not in only_online, \
        "быть на связи — не повод попадать в подбор"
    print("онлайн сам по себе поводом не является: ок")

    with_note = {p["uuid"]: p for p in await insights.chart_candidates(["rl-4"])}
    assert "и сейчас на связи" in with_note["rl-4"]["reasons"][-1]
    print("но к настоящему поводу добавляется пометкой: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'rl-%'")
    print("\nВСЁ ПРОШЛО")

asyncio.run(main())
