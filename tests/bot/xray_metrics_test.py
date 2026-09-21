# -*- coding: utf-8 -*-
"""Метрики Xray копятся и складываются в сводку.

Трафик по людям и так копится в часовых срезах. А число соединений, живость
процесса и состояние моста видны только «прямо сейчас»: посмотрел — увидел, не
посмотрел — не увидел. Разбирать по ним приходится задним числом: «вчера
вечером всё тормозило» без цифр не разобрать никак.

Проверяется то, ради чего снимки и делаются:

  1. доля времени, а не «да/нет» — мост отваливается на минуты, и по одному
     снимку этого не видно вовсе;
  2. «моста не было ни разу» и «мост не настроен» — разные вещи, и путать их
     нельзя: во втором случае ругаться не на что;
  3. старое подчищается, иначе снимок раз в пять минут копит девять тысяч
     строк в месяц.
"""
import asyncio

from database import db


async def main():
    await db.connect()
    await db.init_tables()
    await db.execute("DELETE FROM xray_metrics")

    print("=== пусто — это пусто, а не ошибка ===")
    s = await db.xray_metrics_summary(24)
    print(" ", s)
    assert not s.get("n"), "на пустой таблице появились числа"
    print("  ок")

    print("\n=== снимки складываются в сводку ===")
    # Процесс живой не всегда, мост тоже: так и бывает на самом деле.
    for conn, proc, bridge in ((10, True, True), (50, True, True),
                               (30, True, False), (0, False, False)):
        await db.add_xray_metric(users=7, connections=conn,
                                 process_up=proc, bridge_up=bridge)

    s = await db.xray_metrics_summary(24)
    print(" ", {k: s[k] for k in sorted(s)})
    assert s["n"] == 4
    assert s["peak"] == 50, "пик соединений посчитан неверно"
    # 90/4 = 22,5, и база округляет вверх. Проверяем именно то, что она
    # возвращает, а не то, что кажется «правильным» на глаз.
    assert s["avg_conn"] == 23, f"среднее посчитано неверно: {s['avg_conn']}"
    assert s["proc_ok"] == 3, "живость процесса посчитана неверно"
    assert s["bridge_ok"] == 2, "живость моста посчитана неверно"
    assert s["bridge_seen"] == 4
    print("  пик, среднее и доли времени: ок")

    print("\n=== «мост не настроен» и «моста не было» — разное ===")
    # Когда канал не настроен, писать про мост нечего. Если не различать, экран
    # ругался бы «мост 0%» там, где ругаться не на что.
    await db.execute("DELETE FROM xray_metrics")
    for _ in range(3):
        await db.add_xray_metric(users=7, connections=5,
                                 process_up=True, bridge_up=None)
    s = await db.xray_metrics_summary(24)
    print("  снимков:", s["n"], "мост виден в:", s["bridge_seen"])
    assert s["n"] == 3
    assert s["bridge_seen"] == 0, (
        "ненастроенный мост посчитан как наблюдавшийся — экран сказал бы "
        "«мост 0%» там, где канала просто нет")
    print("  различаются: ок")

    print("\n=== старое подчищается ===")
    await db.execute(
        "UPDATE xray_metrics SET taken_at = NOW() - INTERVAL '40 days'")
    await db.add_xray_metric(users=7, connections=1, process_up=True,
                             bridge_up=None)
    before = await db.fetch_val("SELECT COUNT(*) FROM xray_metrics")
    await db.trim_xray_metrics(30)
    after = await db.fetch_val("SELECT COUNT(*) FROM xray_metrics")
    print(f"  было {before}, стало {after}")
    assert before == 4 and after == 1, "подчистка убрала не то"
    print("  ок")

    print("\n=== сводка смотрит только в своё окно ===")
    s = await db.xray_metrics_summary(1)
    assert s["n"] == 1, "в часовое окно попали старые снимки"
    print("  ок")

    await db.execute("DELETE FROM xray_metrics")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
