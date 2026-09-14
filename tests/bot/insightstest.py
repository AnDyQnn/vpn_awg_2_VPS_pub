# -*- coding: utf-8 -*-
"""Проверка подбора, кому смотреть персональный график. В прод не уезжает."""
import asyncio
from datetime import datetime, timedelta

from database import db
import insights


# Напоминание, на котором этот тест однажды уже сломался: bytes_in — это то,
# что сервер ПРИНЯЛ от человека, то есть его отдача. Скачивание — bytes_out.
async def add_hour(uuid, hours_ago, mb_up, mb_down, packets, peak=0):
    await db.execute(
        "INSERT INTO traffic_hourly (user_uuid, hour, bytes_in, bytes_out, "
        "packets_in, packets_out, peak_pps, samples) "
        "VALUES ($1, date_trunc('hour', NOW() - ($2 || ' hours')::INTERVAL), "
        "$3,$4,$5,$6,$7,240) ON CONFLICT (user_uuid, hour) DO UPDATE SET "
        "bytes_in=$3, bytes_out=$4, packets_in=$5, packets_out=$6, peak_pps=$7",
        uuid, str(hours_ago), int(mb_up * 1024 * 1024), int(mb_down * 1024 * 1024),
        packets // 2, packets // 2, peak)


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'in-%'")
    names = {"in-1": "Торрентщик", "in-2": "Ютубер", "in-3": "Тихий",
             "in-4": "Всплеск", "in-5": "Раздача"}
    for uid, name in names.items():
        await db.execute("INSERT INTO users (name, uuid) VALUES ($1,$2)", name, uid)

    # Торрент: много мелких пакетов. 2 ГБ и 8 млн пакетов ≈ 268 Б на пакет
    await add_hour("in-1", 1, 1000, 1000, 8_000_000, peak=7000)
    # Ютуб: столько же трафика, но пакеты крупные ≈ 1.4 КБ, и это СКАЧИВАНИЕ
    await add_hour("in-2", 1, 100, 1900, 1_500_000, peak=1800)
    # Тихий: мало трафика
    await add_hour("in-3", 1, 1, 5, 6000, peak=40)
    # Всплеск: неделю по чуть-чуть, сейчас резко больше
    # Норма должна быть осмысленной: ниже 50 МБ в час сравнивать не с чем,
    # иначе в подбор попадает любой, кто всю неделю молчал.
    for h in range(30, 160, 6):
        await add_hour("in-4", h, 20, 60, 40_000, peak=300)
    await add_hour("in-4", 2, 100, 500, 700_000, peak=2500)
    # Раздача: отдаёт столько же, сколько принимает, но пакеты крупные
    await add_hour("in-5", 1, 400, 380, 600_000, peak=1200)

    picks = {p["uuid"]: p for p in await insights.chart_candidates()}
    print("подобраны:", {names[u]: p["reasons"] for u, p in picks.items()})

    assert "in-1" in picks, "торрент обязан попасть в подбор"
    assert any("мелкие пакеты" in r for r in picks["in-1"]["reasons"])
    assert any("раздаёт почти столько" in r for r in picks["in-1"]["reasons"])
    print("торрент: пойман по размеру пакета и по отдаче: ок")

    assert "in-2" not in picks, "обычное видео не должно попадать в подбор"
    assert "in-3" not in picks, "тихий пир не должен попадать в подбор"
    print("ютуб и тихий пир не в подборе: ок")

    assert "in-4" in picks and any("всплеск" in r for r in picks["in-4"]["reasons"]), \
        picks.get("in-4")
    print("всплеск против своей нормы: ок")

    assert "in-5" in picks and any("раздаёт почти столько" in r for r in picks["in-5"]["reasons"])
    assert not any("мелкие пакеты" in r for r in picks["in-5"]["reasons"]), \
        "крупные пакеты не должны считаться торрентом"
    print("раздача поймана, но не названа торрентом: ок")

    # «Сейчас на связи» — пометка, а не повод. Иначе в подбор попадает
    # половина семьи, и смотреть становится нечего.
    picks2 = {p["uuid"]: p for p in await insights.chart_candidates(["in-3"])}
    assert "in-3" not in picks2, "тихий пир не должен попадать в подбор из-за онлайна"
    assert any("и сейчас на связи" in r for r in picks2["in-1"]["reasons"]) is False
    picks2b = {p["uuid"]: p for p in await insights.chart_candidates(["in-1"])}
    assert any("и сейчас на связи" in r for r in picks2b["in-1"]["reasons"]),         picks2b["in-1"]["reasons"]
    print("онлайн — пометка к поводу, а не повод: ок")

    # превышение лимита
    await db.execute(
        "INSERT INTO pps_events (user_uuid, started_at, peak_pps, avg_packet_size) "
        "VALUES ('in-2', NOW() - INTERVAL '2 hours', 6000, 900)")
    picks3 = {p["uuid"]: p for p in await insights.chart_candidates()}
    assert "in-2" in picks3 and any("за лимит" in r for r in picks3["in-2"]["reasons"])
    print("превышение лимита добавляет человека: ок")

    # порядок: у кого причин больше — тот выше
    ordered = await insights.chart_candidates(["in-1"])
    assert ordered[0]["uuid"] == "in-1", [o["name"] for o in ordered]
    print("сортировка по числу причин: ок")

    # мелкая выборка не должна давать вердикт
    await db.execute("DELETE FROM traffic_hourly WHERE user_uuid='in-3'")
    await add_hour("in-3", 1, 0.5, 0.5, 3000)
    picks4 = {p["uuid"]: p for p in await insights.chart_candidates()}
    assert "in-3" not in picks4, "на трёх тысячах пакетов судить нельзя"
    print("мелкая выборка не даёт вердикта: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'in-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
