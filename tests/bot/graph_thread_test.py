# -*- coding: utf-8 -*-
"""Графики рисуются, не останавливая бота.

Картинка в matplotlib — секунда-две чистого процессора на одноядерном узле.
Пока она рисовалась в общем цикле, все нажатия у всех стояли; «трафик в
реальном времени» перерисовывается каждые 10 секунд — и кнопки замирали по
кругу. Проверяем: пока рисуется картинка, цикл продолжает жить.
"""
import asyncio
import os
import time

from database import db
import graphs


async def main():
    await db.connect()
    os.makedirs("/volumes/backups", exist_ok=True)

    ticks = []

    async def ticker():
        while True:
            ticks.append(time.monotonic())
            await asyncio.sleep(0.02)

    t = asyncio.ensure_future(ticker())
    await asyncio.sleep(0.05)
    for name, coro in (("трафик", graphs.generate_vpn_graph()),
                       ("нагрузка", graphs.generate_load_graph(hours=24))):
        before = len(ticks)
        start = time.monotonic()
        path = await coro
        took = time.monotonic() - start
        assert os.path.exists(path), path
        # Самый длинный промежуток между тиками — столько цикл простоял.
        gaps = [b - a for a, b in zip(ticks[before:], ticks[before + 1:])]
        worst = max(gaps) if gaps else took
        print("  %-9s рисовалось %.2f с, цикл стоял не дольше %.2f с"
              % (name, took, worst))
        # Весь рисунок в общем цикле дал бы простой, равный времени рисования.
        # В отдельном потоке цикл получает слово каждые несколько миллисекунд.
        assert worst < max(0.1, took / 3), \
            "цикл бота стоял, пока рисовался график (%.2f из %.2f с)" % (worst, took)
    t.cancel()
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
