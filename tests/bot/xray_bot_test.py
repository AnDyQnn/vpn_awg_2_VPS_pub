# -*- coding: utf-8 -*-
"""Сборка конфига Xray в боте: адреса, пропуски, приостановленные, подписка."""
import asyncio
import base64
import json

from database import db
import xray


class FakeResp:
    def __init__(self, payload, status=200):
        self._p, self.status = payload, status

    async def json(self):
        return self._p

    async def text(self):
        return json.dumps(self._p)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class FakeSession:
    """Подменяет узел: ключи отдаёт, конфиг запоминает."""
    last = {}
    addrs = None

    def post(self, url, json=None, timeout=None):
        if url.endswith("/xray/keys"):
            return FakeResp({"privatekey": "PRIV-TEST", "password": "PUB-TEST"})
        if url.endswith("/xray/config"):
            FakeSession.last = json["config"]
            FakeSession.addrs = json.get("addresses")
            return FakeResp({"status": "ok", "note": "запущен"})
        return FakeResp({}, 404)

    def get(self, url, timeout=None):
        return FakeResp({}, 404)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'xr-%'")
    # Ключи Reality живут в настройках и переживают прогон: если их оставил
    # соседний тест, этот возьмёт чужие и упадёт на сравнении.
    await db.execute("DELETE FROM settings WHERE key LIKE 'xray_%'")
    for uid, name, active in (("xr-1", "Ника", True), ("xr-2", "Папа", True),
                              ("xr-3", "Пауза", False), ("xr-4", "БезАдреса", True)):
        await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,$3)",
                         name, uid, active)

    xray.api_session = lambda: FakeSession()
    # адреса как у пиров: у четвёртого адреса нет
    async def ips():
        return {"xr-1": "10.13.13.6", "xr-2": "10.13.13.7", "xr-3": "10.13.13.8"}
    xray.peer_ip_map = ips
    await db.set_setting("server_host", "203.0.113.9")

    print("=== выдача подключений ===")
    for uid in ("xr-1", "xr-2", "xr-3", "xr-4"):
        ok, res = await xray.issue(uid)
        assert ok, res
    print("выдано четверым, токены получены")

    cfg = FakeSession.last
    clients = cfg["inbounds"][0]["settings"]["clients"]
    emails = {c["email"] for c in clients}
    print("в конфиге:", emails)

    assert "xr-3" not in emails, "приостановленный не должен попадать в конфиг"
    assert "xr-4" not in emails, "человек без адреса не должен попадать в конфиг"
    assert emails == {"xr-1", "xr-2"}, emails
    print("пауза и отсутствие адреса отсекаются: ок")

    print("\n=== sendThrough: у каждого свой адрес ===")
    sent = {o["tag"]: o.get("sendThrough") for o in cfg["outbounds"] if "sendThrough" in o}
    print(sent)
    # Адрес-двойник: тот же номер во второй половине сети. Со своего адреса пира
    # отправлять нельзя — он лежит за туннелем и узлу не принадлежит.
    assert set(sent.values()) == {"10.13.13.134", "10.13.13.135"}, sent
    assert len(sent) == 2
    print("каждому свой адрес-двойник: ок")

    print("\n=== узлу переданы адреса, которые он должен поднять ===")
    print(FakeSession.addrs)
    assert sorted(FakeSession.addrs) == ["10.13.13.134", "10.13.13.135"], FakeSession.addrs
    print("список совпадает с конфигом: ок")

    print("\n=== правила ведут человека в его канал ===")
    for rule in cfg["routing"]["rules"]:
        user = rule["user"][0]
        tag = rule["outboundTag"]
        expect = "10.13.13.134" if user == "xr-1" else "10.13.13.135"
        assert sent[tag] == expect, (user, tag, sent[tag])
    print("совпадают: ок")

    assert any(o.get("tag") == "direct" for o in cfg["outbounds"]), "нет запасного канала"
    print("запасной канал на месте: ок")

    print("\n=== маскировка ===")
    rs = cfg["inbounds"][0]["streamSettings"]["realitySettings"]
    # Не вписанная строка, а то, что реально настроено: маску меняют, и тест
    # не должен падать из-за этого, иначе его однажды просто выключат.
    dest = (await xray.settings())["dest"]
    assert rs["privateKey"] == "PRIV-TEST", rs
    assert dest, "маска не задана вовсе"
    # Имён может быть несколько: вход обязан принять любое из пула, потому что
    # у разных людей в ссылке зашиты разные.
    assert rs["serverNames"] == xray.mask_names(dest), rs["serverNames"]
    assert dest in rs["serverNames"], "сам домен обязан быть в пуле"
    assert cfg["inbounds"][0]["port"] == 443
    print("Reality настроен, порт 443, ключ от узла: ок")

    print("\n=== ссылка и подписка ===")
    link = await xray.profile_link("xr-1")
    print(link[:110] + "…")
    assert link.startswith("vless://") and "203.0.113.9:443" in link
    assert "pbk=PUB-TEST" in link and "security=reality" in link

    rec = await db.get_xray_user("xr-1")
    body = await xray.subscription_body(rec["sub_token"])
    decoded = base64.b64decode(body).decode()
    # Подписка отдаёт ВСЕ входы, а не один: приложение перебирает их и
    # переходит на живой, когда маска отваливается. Основной идёт первым.
    profiles = decoded.split(chr(10))
    assert profiles[0] == link, (profiles[0], link)
    assert len(profiles) == len(await xray.entries()), profiles
    print("подписка отдаёт профиль в base64: ок")

    # Скачать подписку — это ещё НЕ подключиться. Отметку «переехал на Xray»
    # ставит только живой трафик: по ней владельцу открывается снятие
    # AmneziaWG, и поставленная за скачивание она предлагала бы снять рабочий
    # доступ человеку, который по Xray не передал ни байта.
    seen = await db.get_xray_user("xr-1")
    assert not seen["first_seen_at"], "скачивание подписки — не подключение"
    print("скачивание подписки отметкой о переезде не считается: ок")

    print("\n=== приостановленному подписка не отдаётся ===")
    rec3 = await db.get_xray_user("xr-3")
    assert await xray.subscription_body(rec3["sub_token"]) == "", "пауза должна гасить подписку"
    print("пусто: ок")

    print("\n=== перевыпуск: ключ новый, адрес прежний ===")
    # Раньше здесь ожидалось обратное — что перевыпуск меняет и адрес. Это и
    # оказалось бедой: адрес, уже вставленный в приложение, умирал, приложение
    # молча оставалось с отозванным ключом, и человек сидел без связи.
    old_token = rec["sub_token"]
    old_uuid = rec["xray_uuid"]
    ok, new_token = await xray.issue("xr-1")
    assert ok and new_token == old_token, "адрес подписки обязан пережить перевыпуск"
    after = await db.get_xray_user("xr-1")
    assert after["xray_uuid"] != old_uuid, "ключ доступа обязан смениться"
    # Подписка отдаётся в base64 — раскодируем, иначе сравнивать не с чем.
    import base64 as _b64
    body = _b64.b64decode(await xray.subscription_body(old_token)).decode("utf-8", "replace")
    assert after["xray_uuid"] in body, "по прежнему адресу должен приезжать новый ключ"
    assert old_uuid not in body, "отозванный ключ не должен доезжать до человека"
    print("адрес прежний, ключ новый: ок")

    print("\n=== отзыв самого адреса — отдельно и осознанно ===")
    ok, changed = await xray.issue("xr-1", new_address=True)
    assert ok and changed != old_token, "по просьбе адрес обязан смениться"
    assert await xray.subscription_body(old_token) == "", "прежний адрес должен умереть"
    assert await xray.subscription_body(changed) != "", "новый должен работать"
    print("адрес сменён по просьбе: ок")

    await db.execute("DELETE FROM users WHERE uuid LIKE 'xr-%'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
