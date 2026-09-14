# -*- coding: utf-8 -*-
"""Вердикт по всплеску — на настоящем случае с боевого узла.

Человек качнул что-то с телефона: один замер, пик 5710 пакетов в секунду,
средний пакет 1159 байт, отдал за неделю вшестеро меньше, чем принял. Система
записала «превышение», и по экрану это было неотличимо от торрента. Проверяем,
что теперь различимо.
"""
import asyncio
from datetime import datetime, timedelta

from database import db
from insights import event_verdict, packet_size_note


def case(name, **kw):
    verdict, worrying = event_verdict(kw)
    mark = "⚠️" if worrying else "•"
    print(f"  {mark} {name}: {verdict}")
    return verdict, worrying


async def main():
    now = datetime.utcnow()

    print("=== настоящий случай: телефон качает из магазина ===")
    verdict, worrying = case(
        "Shlusik", peak_pps=5710, avg_packet_size=1159, upload_share=0.15,
        started_at=now, ended_at=now)
    assert not worrying, "обычную загрузку нельзя подавать как проблему"
    assert "разовая" in verdict, verdict

    print("\n=== торрент: мелкие пакеты ===")
    verdict, worrying = case(
        "торрент", peak_pps=6000, avg_packet_size=260, upload_share=0.4,
        started_at=now - timedelta(minutes=40), ended_at=now)
    assert worrying and "торрент" in verdict, verdict

    print("\n=== раздача: отдаёт больше, чем берёт ===")
    verdict, worrying = case(
        "раздача", peak_pps=3000, avg_packet_size=1200, upload_share=0.8,
        started_at=now - timedelta(minutes=10), ended_at=now)
    assert worrying and "раздач" in verdict, verdict

    print("\n=== долгая загрузка: не торрент, но заметно ===")
    verdict, worrying = case(
        "долгая", peak_pps=7000, avg_packet_size=1300, upload_share=0.1,
        started_at=now - timedelta(minutes=25), ended_at=now)
    assert worrying and "25 мин" in verdict, verdict

    print("\n=== размер пакета объясняется, а не пугает ===")
    for size, must in ((29751, "склеивает"), (1159, "1159"), (260, "мелкие")):
        note = packet_size_note(size)
        print(f"  {size} → {note}")
        assert must in note, (size, note)

    print("\n=== длительность реально сохраняется ===")
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid='vt-1'")
    await db.execute("INSERT INTO users (name, uuid) VALUES ('Тест','vt-1')")
    began = datetime.utcnow() - timedelta(minutes=12)
    await db.record_pps_event("vt-1", 6000, 300, started_at=began, upload_share=0.7)
    rows = await db.get_pps_events(24)
    row = next(r for r in rows if r["user_uuid"] == "vt-1")
    length = (row["ended_at"] - row["started_at"]).total_seconds()
    print(f"  записано {int(length)} секунд, доля отдачи {row['upload_share']}")
    assert length > 600, "начало всплеска снова потерялось"
    assert abs(row["upload_share"] - 0.7) < 0.01
    verdict, worrying = event_verdict(dict(row))
    print("  вердикт:", verdict)
    assert worrying

    await db.execute("DELETE FROM users WHERE uuid='vt-1'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
