# -*- coding: utf-8 -*-
"""Свой канал Xray до Германии: сборка конфига.

Германия подключена пиром на тот же интерфейс, где живут клиенты AmneziaWG, —
значит два канала на деле один. Здесь собирается второй: Германия подключается
к нам сама (как и по амнезии), а Россия проталкивает трафик людей в её
соединение.

Проверяется не «появился канал», а то, что ломается молча и дорого:

  1. Обращения ВНУТРЬ туннеля остаются на прежнем пути и правило для них стоит
     выше — иначе запрос к домашнему сервису уедет в Германию.
  2. Личный адрес человека остаётся на этом внутреннем канале — на нём держатся
     роли, фильтры и страница отказа.
  3. Мост приходит на тот же вход, что и люди, и не путается с ними.
  4. Откат: моста нет — собираем как раньше, люди идут прежним путём.

Готовый конфиг кладётся в /out — его проверит настоящим Xray отдельный тест
узла. Сборка, которую не принимает сам Xray, бесполезна, как бы стройно она ни
выглядела в проверках.
"""
import asyncio
import json
import os

from database import db


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'cs-%'")
    for uid, name in (("cs-1", "Первый"), ("cs-2", "Второй")):
        await db.execute(
            "INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
            name, uid)

    import xray
    import cascade

    async def people():
        return [{"user_uuid": "cs-1",
                 "xray_uuid": "11111111-1111-1111-1111-111111111111",
                 "name": "Первый", "is_active": True},
                {"user_uuid": "cs-2",
                 "xray_uuid": "22222222-2222-2222-2222-222222222222",
                 "name": "Второй", "is_active": True}]
    db.list_xray_users = people

    async def ips():
        return {"cs-1": "10.13.13.41", "cs-2": "10.13.13.42"}
    xray.peer_ip_map = ips

    # Ключи настоящего вида, выданные самим Xray. Выдуманные строки он не
    # принимает: формат проверяется при разборе конфига, и тест ловил бы
    # «ошибку» там, где её нет, а настоящую пропускал.
    PRIV = "CDFyF-laN14-y0T3kyLqHjNGmVLltonxM0zbGaTHonM"
    PUB = "zAEiqMQQwi7Cy79g7Atu0fVkxDZAcDzyY9P8-4KyPRk"

    async def keys():
        return {"private_key": PRIV, "public_key": PUB, "short_id": "aabbccdd"}
    xray.ensure_keys = keys

    async def ways():
        return [(443, "avito.ru")]
    xray.entries = ways

    def save(cfg, name):
        try:
            os.makedirs("/out", exist_ok=True)
            with open(f"/out/{name}", "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("  (конфиг не сохранён для проверки Xray:", e, ")")

    # --- 1. Канала нет: прежнее поведение ------------------------------
    print("=== канал не настроен ===")
    for k in (cascade.KEY_ON, cascade.KEY_UUID, cascade.KEY_FALLBACK,
              cascade.KEY_HOST, cascade.KEY_MASK):
        await db.set_setting(k, "")
    cfg, addrs, note = await xray.build_config()
    assert cfg, note
    save(cfg, "xray_plain.json")
    tags = [o.get("tag") for o in cfg["outbounds"]]
    print("  каналы:", tags)
    assert tags[0] == "direct", (
        "запасной канал обязан быть первым: в Xray первый исходящий — канал по "
        "умолчанию, и несовпавший трафик записывался бы на случайного человека")
    assert not [c for c in cfg["inbounds"][0]["settings"]["clients"]
                if c.get("reverse")], "мост появился там, где канала нет"
    for uid in ("cs-1", "cs-2"):
        mine = [r for r in cfg["routing"]["rules"] if r.get("user") == [uid]]
        assert len(mine) == 1, f"{uid}: правил должно быть одно"
        assert mine[0]["outboundTag"].startswith("out-")
    print("  прежнее поведение сохранено: ок")

    # --- 2. Канал настроен ----------------------------------------------
    print("\n=== канал настроен, мост подключён ===")
    await db.set_setting(cascade.KEY_ON, "1")
    await db.set_setting(cascade.KEY_FALLBACK, "0")
    await db.set_setting(cascade.KEY_UUID,
                         "33333333-3333-3333-3333-333333333333")
    await db.set_setting(cascade.KEY_MASK, "avito.ru")
    await db.set_setting(cascade.KEY_HOST, "203.0.113.10")
    await db.set_setting(cascade.KEY_PORT, "443")

    cfg, addrs, note = await xray.build_config()
    assert cfg, note
    save(cfg, "xray_cascade.json")

    print("\n=== мост среди людей, но отличим от них ===")
    clients = cfg["inbounds"][0]["settings"]["clients"]
    bridges = [c for c in clients if c.get("reverse")]
    print("  всего учётных записей:", len(clients), "из них мост:", len(bridges))
    assert len(bridges) == 1, "мост должен быть ровно один"
    assert bridges[0]["email"] == cascade.BRIDGE_USER
    assert bridges[0]["reverse"]["tag"] == cascade.PORTAL_TAG
    assert "flow" not in bridges[0], (
        "у моста не должно быть ускорения для трафика человека — "
        "через него идёт служебный поток")
    print("  мост на общем входе, отдельной двери не завели: ок")

    print("\n=== внутрь туннеля — прежним путём и ВЫШЕ остального ===")
    rules = cfg["routing"]["rules"]
    for r in rules:
        print("   ", r.get("inboundTag") or r.get("user"), "->",
              r.get("outboundTag"), "по", "адресу" if r.get("ip") else "всему")
    for uid in ("cs-1", "cs-2"):
        mine = [i for i, r in enumerate(rules) if r.get("user") == [uid]]
        assert len(mine) == 2, f"{uid}: нужно два правила — внутрь и наружу"
        inner = [i for i in mine if rules[i].get("ip")]
        outer = [i for i in mine if not rules[i].get("ip")]
        assert inner and outer
        assert min(inner) < min(outer), (
            f"{uid}: правило наружу встало выше — обращение к домашнему "
            f"сервису уехало бы в Германию")
        assert rules[inner[0]]["outboundTag"].startswith("out-"), (
            f"{uid}: внутрь туннеля идём не своим каналом — "
            f"потеряются роли и фильтры")
        assert rules[outer[0]]["outboundTag"] == cascade.PORTAL_TAG
    print("  порядок и направления верны: ок")

    print("\n=== личный адрес человека на месте ===")
    sends = sorted(o["sendThrough"] for o in cfg["outbounds"]
                   if o.get("sendThrough"))
    print("  адреса:", sends)
    assert sends == ["10.13.13.169", "10.13.13.170"], (
        "личный адрес потерялся — роли и фильтры перестанут узнавать человека")

    print("\n=== счётчики включены ===")
    assert cfg.get("stats") == {}, "счётчики не включены"
    assert cfg["policy"]["levels"]["0"]["statsUserUplink"] is True
    api_in = [i for i in cfg["inbounds"] if i.get("tag") == "api"]
    assert api_in, "служебный вход счётчиков не заведён"
    assert api_in[0]["listen"] == "127.0.0.1", (
        "служебный вход слушает не только петлю — до него добрались бы снаружи")
    assert rules[0].get("inboundTag") == ["api"], (
        "правило служебного входа должно стоять первым")
    print("  счётчики есть, служебный вход только на петле: ок")

    print("\n=== конфиг моста: приватного ключа чужой стороны в нём нет ===")
    ch = await cascade.settings()
    bridge = cascade.bridge_config(ch, PUB, "aabbccdd")
    body = json.dumps(bridge, ensure_ascii=False)
    save(bridge, "xray_bridge.json")
    assert "privateKey" not in body, "в конфиг моста попал приватный ключ"
    assert PRIV not in body, "приватный ключ узла утёк в конфиг моста"
    assert bridge["outbounds"][0]["tag"] == "out", (
        "у моста первым должен стоять обычный выход — иначе несовпавшее "
        "уедет обратно в туннель")
    out = [o for o in bridge["outbounds"] if o.get("protocol") == "vless"][0]
    assert out["settings"]["reverse"]["tag"] == cascade.BRIDGE_TAG
    assert out["settings"]["address"] == "203.0.113.10"
    print("  мост звонит в Россию сам, ключ только публичный: ок")

    # --- 3. Откат --------------------------------------------------------
    print("\n=== мост пропал: люди идут прежним путём ===")
    await db.set_setting(cascade.KEY_FALLBACK, "1")
    ok, why = await cascade.ready()
    print("  готовность:", ok, "—", why)
    assert ok is False, "откат не сработал — люди остались бы в тишине"
    cfg, _a, _n = await xray.build_config()
    assert not [c for c in cfg["inbounds"][0]["settings"]["clients"]
                if c.get("reverse")], "при откате мост остался на входе"
    for uid in ("cs-1", "cs-2"):
        mine = [r for r in cfg["routing"]["rules"] if r.get("user") == [uid]]
        assert len(mine) == 1 and mine[0]["outboundTag"].startswith("out-")
    print("  вернулись на прежний путь целиком: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'cs-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
