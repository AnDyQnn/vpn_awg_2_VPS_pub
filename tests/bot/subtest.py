# -*- coding: utf-8 -*-
"""Сервер подписок: что отдаётся, кому отказывают и что видит клиент."""
import asyncio
import base64
import json
import os
import uuid as uuid_lib

import aiohttp

os.environ.setdefault("SUB_PORT", "18080")

from database import db
import subscription
import xray

PORT = int(os.environ["SUB_PORT"])
BASE = f"http://127.0.0.1:{PORT}"


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
    def post(self, url, json=None, timeout=None):
        if url.endswith("/xray/keys"):
            return FakeResp({"privatekey": "PRIV-TEST", "password": "PUB-TEST"})
        if url.endswith("/xray/config"):
            return FakeResp({"status": "ok", "note": "запущен"})
        return FakeResp({}, 404)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


async def main():
    await db.connect()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sb-%'")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active, expires_at) "
        "VALUES ($1,$2,TRUE,NOW() + INTERVAL '30 days')", "Ника", "sb-1")
    await db.execute(
        "INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,FALSE)", "Пауза", "sb-2")
    # немного трафика — клиент должен увидеть цифры на карточке профиля
    await db.execute(
        "INSERT INTO traffic_hourly (user_uuid, hour, bytes_in, bytes_out) "
        "VALUES ($1, date_trunc('hour', NOW()), 1000, 2000)", "sb-1")

    xray.api_session = lambda: FakeSession()

    async def ips():
        return {"sb-1": "10.13.13.6", "sb-2": "10.13.13.7"}
    xray.peer_ip_map = ips
    await db.set_setting("server_host", "203.0.113.9")

    ok, token = await xray.issue("sb-1")
    assert ok, token
    ok, token2 = await xray.issue("sb-2")
    assert ok, token2

    runner = await subscription.start_server()

    async with aiohttp.ClientSession() as s:
        print("=== живая подписка ===")
        async with s.get(f"{BASE}/sub/{token}") as r:
            assert r.status == 200, r.status
            body = await r.text()
            head = dict(r.headers)
        link = base64.b64decode(body).decode()
        print(link[:90] + "…")
        # Подписка отдаёт список входов; основной — первый.
        assert link.split(chr(10))[0] == await xray.profile_link("sb-1")
        assert len(link.split(chr(10))) == len(await xray.entries())
        print("отдан профиль этого человека: ок")

        print("\n=== что видит клиент ===")
        print({k: v for k, v in head.items()
               if k.lower().startswith(("profile", "subscription", "cache"))})
        assert head["profile-update-interval"] == "12"
        assert base64.b64decode(head["profile-title"].split(":", 1)[1]).decode() == "Ника"
        info = dict(p.strip().split("=") for p in head["subscription-userinfo"].split(";"))
        assert info["upload"] == "1000" and info["download"] == "2000", info
        assert int(info["expire"]) > 0, info
        assert head["Cache-Control"] == "no-store"
        print("имя, объём и срок доехали: ок")

        print("\n=== приостановленному отказ ===")
        async with s.get(f"{BASE}/sub/{token2}") as r:
            assert r.status == 404, r.status
        print("404: ок")

        print("\n=== чужой и выдуманный токен ===")
        for bad in ("нет-такого", "a" * 40, ""):
            async with s.get(f"{BASE}/sub/{bad}") as r:
                assert r.status == 404, (bad, r.status)
        async with s.get(f"{BASE}/") as r:
            assert r.status == 404, r.status
            assert "vpn" not in (await r.text()).lower()
        print("везде 404, корень молчит: ок")

        print("\n=== отзыв ссылки действует сразу ===")
        ok, new_token = await xray.issue("sb-1")
        assert ok and new_token != token
        async with s.get(f"{BASE}/sub/{token}") as r:
            assert r.status == 404, "старая ссылка обязана умереть немедленно"
        async with s.get(f"{BASE}/sub/{new_token}") as r:
            assert r.status == 200
        print("старая мертва, новая жива: ок")

        print("\n=== адрес подписки ===")
        # Раньше без настройки адреса ссылку не показывали вовсе — подписка
        # раздавалась наружу, и без сертификата это было нельзя. Теперь она
        # раздаётся внутри туннеля: адрес есть всегда, наружу ничего не торчит.
        inside = await xray.subscription_url(new_token)
        assert inside.startswith("http://10.13.13."), \
            f"по умолчанию подписка обязана быть внутри туннеля, а не {inside}"
        assert new_token in inside, "личный токен обязан быть в ссылке"
        await db.set_setting("xray_sub_base", "https://vpn.example.com/")
        url = await xray.subscription_url(new_token)
        print(url)
        assert url == f"https://vpn.example.com/sub/{new_token}"
        print("собирается из настройки, лишний слеш убран: ок")

    await runner.cleanup()
    await db.execute("DELETE FROM users WHERE uuid LIKE 'sb-%'")
    await db.execute("DELETE FROM settings WHERE key='xray_sub_base'")
    print("\nВСЁ ПРОШЛО")


asyncio.run(main())
