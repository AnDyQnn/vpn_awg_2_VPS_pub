# -*- coding: utf-8 -*-
"""Кому есть смысл смотреть персональный график.

Графиков столько же, сколько людей, и листать их все бессмысленно: интересны
двое-трое. Здесь собраны признаки, по которым человек попадает в этот короткий
список, и к каждому идёт причина словами — чтобы администратор понимал, почему
ему предлагают именно этого.

Про размер пакета, потому что это главный признак и его легко перепутать со
скоростью: обычный трафик даёт около килобайта на пакет, то есть примерно
120 пакетов в секунду на мегабит. Торрент с его мелкими пакетами и DHT выбирает
втрое-вчетверо больше пакетов на ту же полосу — и упирается в процессор узла
при скромных мегабитах. Поэтому средний размер пакета ниже полукилобайта
говорит о характере потока больше, чем любая цифра скорости.

Пакеты по каждому человеку берутся из счётчиков файрвола: WireGuard отдаёт по
пирам только байты, пакетов у него нет вовсе.
"""
from database import db

SMALL_PACKET = 500          # байт: ниже этого поток «неестественный»
MIN_PACKETS = 20000         # меньше — выборка слишком мелкая, чтобы судить
MIN_BYTES = 50 * 1024 * 1024
UPLOAD_RATIO = 0.7          # отдача от приёма, при которой это уже раздача
SPIKE_TIMES = 3             # во сколько раз час выбился из собственной нормы


async def _last24():
    rows = await db.fetch_all("""
        SELECT t.user_uuid, u.name,
               COALESCE(SUM(t.bytes_in), 0)   AS bytes_in,
               COALESCE(SUM(t.bytes_out), 0)  AS bytes_out,
               COALESCE(SUM(t.packets_in), 0) AS packets_in,
               COALESCE(SUM(t.packets_out), 0) AS packets_out,
               COALESCE(MAX(t.peak_pps), 0)   AS peak_pps,
               COALESCE(MAX(t.bytes_in + t.bytes_out), 0) AS busiest_hour
        FROM traffic_hourly t JOIN users u ON u.uuid = t.user_uuid
        WHERE t.hour > NOW() - INTERVAL '24 HOURS'
        GROUP BY t.user_uuid, u.name
    """)
    return {r["user_uuid"]: dict(r) for r in rows}


async def _week_norm():
    """Своя норма за неделю, БЕЗ последних суток: иначе всплеск сам поднимет
    планку, относительно которой мы его ищем."""
    rows = await db.fetch_all("""
        SELECT user_uuid, AVG(bytes_in + bytes_out) AS avg_hour
        FROM traffic_hourly
        WHERE hour > NOW() - INTERVAL '7 DAYS'
          AND hour <= NOW() - INTERVAL '24 HOURS'
        GROUP BY user_uuid
    """)
    return {r["user_uuid"]: float(r["avg_hour"] or 0) for r in rows}


def _reasons(rec, norm, online, exceeded):
    """Причины попадания в список — словами, а не кодами."""
    out = []
    if online:
        out.append("сейчас на связи")
    if exceeded:
        out.append(f"выходил за лимит ({exceeded})")

    packets = (rec["packets_in"] or 0) + (rec["packets_out"] or 0)
    total = (rec["bytes_in"] or 0) + (rec["bytes_out"] or 0)
    if packets >= MIN_PACKETS:
        avg = total / packets
        if avg < SMALL_PACKET:
            out.append(f"мелкие пакеты (~{int(avg)} Б) — похоже на торрент")
    if total >= MIN_BYTES and rec["bytes_in"]:
        ratio = (rec["bytes_out"] or 0) / rec["bytes_in"]
        if ratio >= UPLOAD_RATIO:
            out.append("отдаёт почти столько же, сколько получает")
    if norm and rec["busiest_hour"] > norm * SPIKE_TIMES and rec["busiest_hour"] >= MIN_BYTES:
        out.append("резкий всплеск против своей нормы за неделю")
    return out


async def chart_candidates(online_uuids=None):
    """Кого стоит посмотреть. Возвращает список словарей с причинами,
    самые «шумные» сверху — у кого причин больше."""
    online_uuids = set(online_uuids or [])
    last24 = await _last24()
    norm = await _week_norm()

    try:
        events = await db.get_pps_events(24)
    except Exception:
        events = []
    exceeded = {}
    for e in events:
        exceeded[e["user_uuid"]] = exceeded.get(e["user_uuid"], 0) + 1

    # Человек на связи, но без трафика за сутки, — тоже кандидат: график покажет,
    # что он подключён и молчит, а это тоже ответ.
    uuids = set(last24) | online_uuids | set(exceeded)
    result = []
    for uid in uuids:
        rec = last24.get(uid) or {"name": None, "bytes_in": 0, "bytes_out": 0,
                                  "packets_in": 0, "packets_out": 0,
                                  "peak_pps": 0, "busiest_hour": 0}
        why = _reasons(rec, norm.get(uid, 0), uid in online_uuids, exceeded.get(uid, 0))
        if not why:
            continue
        name = rec.get("name")
        if not name:
            user = await db.get_user_by_uuid(uid)
            name = (user or {}).get("name") or uid[:8]
        result.append({"uuid": uid, "name": name, "reasons": why,
                       "peak_pps": rec["peak_pps"],
                       "bytes": (rec["bytes_in"] or 0) + (rec["bytes_out"] or 0)})

    # Сортируем по числу причин, потом по пику: сначала те, у кого совпало больше.
    result.sort(key=lambda r: (len(r["reasons"]), r["peak_pps"]), reverse=True)
    return result
