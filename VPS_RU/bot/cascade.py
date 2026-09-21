# -*- coding: utf-8 -*-
"""Свой канал Xray до Германии, независимый от амнезии.

Зачем
-----
Германия подключена пиром на тот же интерфейс, где живут клиенты AmneziaWG.
Значит два канала — на деле один:

    было:   AWG_RU_in  ──┐
                          ├── амнезия ──→ Германия
            Xray_RU_in ──┘

    стало:  AWG_RU_in  ──── амнезия ────→ AWG_DE_out
            Xray_RU_in ──── VLESS ──────→ Xray_DE_out

Главное, что это даёт: если амнезию заблокируют по признаку протокола, под нож
попадут ОБА нынешних пути — и клиентский, и наш до Германии, потому что оба
амнезия и оба пересекают границу. Канал на другом протоколе это переживёт.

Направление: Германия подключается к России
-------------------------------------------
Так же, как по амнезии, и это не формальность.

Когда Россия звонит наружу, получается редкая картина: сервер в РФ держит одно
толстое постоянное соединение к одному зарубежному адресу. Обычные серверы так
себя не ведут — они делают много коротких соединений к разным местам. Такой
поток виден, и прятать его нечем.

Когда звонит Германия, она приходит на тот же 443, куда и так подключаются
люди, — для наблюдателя это ещё один клиент среди тридцати. Нынешняя схема так
и стоит год на двух разных узлах.

Как трафик течёт к тому, кто позвонил
-------------------------------------
У амнезии направление дозвона неважно: после рукопожатия пакеты идут в обе
стороны. У VLESS иначе — там клиент спрашивает, сервер отвечает. Поэтому
берётся штатный обратный канал Xray: у учётной записи моста на нашем входе
стоит пометка `reverse`, и она превращается в исходящий канал, через который
Россия проталкивает трафик людей в уже открытое соединение Германии.

Проверено не по документации, а на живом стенде из трёх контейнеров и на той же
версии Xray, что стоит у нас: запрос вошёл в Россию и вышел с адреса Германии.

Что это стоит
-------------
Трафик людей больше не уходит из России пакетами с личного адреса — он уезжает
внутрь соединения моста. Отсюда два следствия:

  * учёт байтов берётся из собственной статистики Xray (см. xray_stats.py),
    а не из счётчиков iptables. Объём, лимиты по нему, графики — на месте;
  * лимит в ПАКЕТАХ в секунду у людей на Xray не работает: статистика Xray
    пакетов не считает. Это единственная настоящая потеря, и она записана в
    документации честно.

Обращения ВНУТРЬ туннеля остаются на прежнем пути — они уходят локально с
адреса-двойника. Поэтому роли, фильтры и страница отказа работают как раньше.
"""
import json
import uuid as uuid_lib

import aiohttp

from database import db
from utils import DE_AGENT_URL, WG_API_URL, api_session

KEY_ON = "cascade_on"
KEY_UUID = "cascade_uuid"          # чем мост представляется России
KEY_MASK = "cascade_mask"          # маска, под которой он приходит
KEY_HOST = "cascade_ru_host"       # куда мосту звонить
KEY_PORT = "cascade_ru_port"
# Внешний адрес Германии. Спрашиваем у неё ОДИН РАЗ, при настройке, и кладём
# сюда. Дальше проверка «жив ли мост» смотрит на живое соединение с этого
# адреса и агента Германии не трогает вовсе: агент живёт за туннелем амнезии, и
# ходить через него значило бы снова связать каналы — только уже в проверке.
KEY_DE_IP = "cascade_de_ip"
# Канал настроен, но моста сейчас нет. Отдельно от «выключено вручную»:
# возвращаться надо само, без участия владельца.
KEY_FALLBACK = "cascade_fallback"

# Пометки обратного канала. Совпадать на двух сторонах они не обязаны —
# стороны узнают друг друга по учётной записи, а не по имени пометки.
PORTAL_TAG = "reverse-out"         # у нас: исходящий канал в сторону моста
BRIDGE_TAG = "reverse-in"          # у Германии: входящий из России
# Учётное имя моста. Нарочно не похоже на uuid человека, чтобы его нельзя было
# спутать с посетителем ни в правилах, ни в статистике.
BRIDGE_USER = "de-bridge"


async def settings():
    return {
        "on": (await db.get_setting(KEY_ON)) == "1",
        "fallback": (await db.get_setting(KEY_FALLBACK)) == "1",
        "uuid": await db.get_setting(KEY_UUID),
        "mask": await db.get_setting(KEY_MASK),
        "host": await db.get_setting(KEY_HOST),
        "port": int(await db.get_setting(KEY_PORT) or 443),
        "de_ip": await db.get_setting(KEY_DE_IP),
    }


async def ready():
    """Пускать ли людей через свой канал прямо сейчас.

    Откат учитывается здесь же: пока моста нет, конфиг собирается без обратного
    канала, и люди выходят прежним путём — через туннель амнезии. Это важнее
    удобства: канал без моста означает не «медленнее», а тишину у всех сразу."""
    cfg = await settings()
    if not cfg["uuid"]:
        return False, "не настроен"
    if not cfg["on"]:
        return False, "выключен"
    if cfg["fallback"]:
        return False, "мост не подключён — идём прежним путём"
    return True, ""


def portal_client(cfg):
    """Учётная запись моста на нашем входе.

    Без `flow`: ускорение vision рассчитано на трафик человека, а здесь через
    соединение идёт служебный поток обратного канала."""
    return {
        "id": cfg["uuid"],
        "email": BRIDGE_USER,
        "reverse": {"tag": PORTAL_TAG},
    }


def bridge_config(cfg, public_key, short_id):
    """Конфиг моста — то, что работает на Германии.

    Мост подключается к России сам и ждёт, когда в это соединение пойдёт
    трафик. Выпускает его прямым каналом: Германия и есть конец пути.

    Никаких правил разделения здесь нет намеренно — что посылать, решает
    Россия, а Германия только выпускает."""
    return {
        "log": {"loglevel": "warning"},
        "outbounds": [
            # Первым — обычный выход: он же запасной для всего, что не совпало
            # с правилами. Документация предупреждает прямо: без явного
            # запасного канала несовпавшее может уехать обратно в туннель.
            {"protocol": "freedom", "tag": "out"},
            {
                "protocol": "vless",
                "tag": "to-ru",
                "settings": {
                    "address": cfg["host"],
                    "port": int(cfg["port"]),
                    "id": cfg["uuid"],
                    "encryption": "none",
                    "reverse": {"tag": BRIDGE_TAG},
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "serverName": cfg["mask"],
                        "publicKey": public_key,
                        "shortId": short_id,
                        "fingerprint": "chrome",
                    },
                },
            },
        ],
        "routing": {"rules": [
            # Всё, что приехало из России, выпускаем наружу.
            {"type": "field", "inboundTag": [BRIDGE_TAG], "outboundTag": "out"},
        ]},
    }


async def _agent(method, path, payload=None, timeout=20):
    async with api_session() as session:
        fn = session.post if method == "POST" else session.get
        kw = {"timeout": aiohttp.ClientTimeout(total=timeout)}
        if payload is not None:
            kw["json"] = payload
        async with fn(f"{DE_AGENT_URL}{path}", **kw) as r:
            body = await r.text()
            if r.status != 200:
                raise RuntimeError(f"агент ответил {r.status}: {body[:200]}")
            return json.loads(body) if body else {}


async def setup(ru_host, ru_port, mask, public_key, short_id):
    """Заводит мост: придумывает ему учётную запись и отдаёт конфиг Германии.

    Ключи маскировки не заводятся отдельные — мост приходит на тот же вход, что
    и люди, и пользуется той же маскировкой. Меньше сущностей, меньше мест,
    где они разойдутся."""
    # Спрашиваем адрес Германии до того, как что-то менять: если она недоступна,
    # лучше не начинать вовсе, чем оставить настройку на полпути.
    de_ip = ""
    try:
        de_ip = (await _agent("GET", "/xray/whoami", timeout=25)).get("ip", "")
    except Exception as e:
        raise RuntimeError(f"Германия не назвала свой адрес: {e}")

    cfg = {
        "uuid": str(uuid_lib.uuid4()),
        "mask": mask,
        "host": str(ru_host).strip(),
        "port": int(ru_port or 443),
        "de_ip": de_ip,
    }
    # Порт 0: у моста нет своего входа, дверь открывать нечего.
    await _agent("POST", "/xray/apply",
                 {"config": bridge_config(cfg, public_key, short_id),
                  "port": 0},
                 timeout=40)
    await db.set_setting(KEY_UUID, cfg["uuid"])
    await db.set_setting(KEY_MASK, cfg["mask"])
    await db.set_setting(KEY_HOST, cfg["host"])
    await db.set_setting(KEY_PORT, str(cfg["port"]))
    await db.set_setting(KEY_DE_IP, cfg["de_ip"])
    # Первая сверка — не сразу: мосту нужно время дозвониться. Пока считаем,
    # что его нет, и люди идут прежним путём. Сторож переключит, когда увидит.
    await db.set_setting(KEY_FALLBACK, "1")
    await db.set_setting(KEY_ON, "1")
    return cfg


async def turn_off():
    """Выключает свой канал. Люди возвращаются на прежний путь — через туннель
    амнезии, то есть туда, где работали до его появления."""
    await db.set_setting(KEY_ON, "0")
    try:
        await _agent("POST", "/xray/off")
    except Exception:
        # Германия могла быть недоступна. У нас уже выключено, люди не
        # пострадают, а её процесс останется без дела.
        pass


async def bridge_present():
    """Подключён ли мост.

    Спрашиваем СВОЙ узел, а не агента Германии: агент живёт за туннелем
    амнезии, и если ходить через него, отказ амнезии выглядел бы как отказ
    нашего канала. Каналы снова оказались бы связаны — только уже в проверке,
    а вся затея ровно в том, чтобы они не зависели друг от друга."""
    cfg = await settings()
    peer = cfg.get("de_ip")
    if not peer:
        return False
    try:
        async with api_session() as session:
            async with session.get(f"{WG_API_URL}/xray/bridge?peer={peer}",
                                   timeout=10) as r:
                if r.status != 200:
                    return False
                return bool((await r.json()).get("present"))
    except Exception:
        return False


async def status():
    cfg = await settings()
    out = dict(cfg)
    out.pop("uuid", None)          # наружу показывать незачем
    out["bridge"] = await bridge_present()
    try:
        out["de"] = await _agent("GET", "/xray/status", timeout=10)
    except Exception as e:
        out["de"] = {"error": str(e)}
    return out
