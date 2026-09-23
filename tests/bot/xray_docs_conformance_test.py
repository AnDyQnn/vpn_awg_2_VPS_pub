# -*- coding: utf-8 -*-
"""Xray проекта — буква в букву с документацией.

Три первоисточника, и по каждому своя часть:

  • ссылка vless:// — стандарт авторов Xray (XTLS/Xray-core, обсуждение 716) и
    пример из документации Happ (happ.su/main/dev-docs/routing);
  • вход сервера — эталонный пример авторов Xray (Xray-examples,
    VLESS-TCP-XTLS-Vision-REALITY/config_server.jsonc);
  • профиль маршрутизации и заголовки подписки — документация Happ
    (routing.md, app-management.md).

Зачем тестом. Отступление от документации ничего не роняет на глазах — Xray
принимает конфиг, приложение принимает ссылку, — а работает потом не так. Такое
находится только сверкой, и сверка должна повторяться сама.
"""
import asyncio
import base64
import json
import re
import sys
from urllib.parse import parse_qsl, quote, unquote, urlsplit

sys.path.insert(0, "/app")

from database import db                            # noqa: E402
import happ_routing as H                           # noqa: E402
import xray                                        # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-56s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


# Параметры ссылки из стандарта (обсуждение 716).
LINK_PARAMS = {"type", "encryption", "security", "fp", "sni", "alpn", "pbk", "sid",
               "pqv", "spx", "flow", "headerType", "host", "path", "mode", "extra",
               "serviceName", "authority", "mtu", "tti"}
# Ключи профиля из документации Happ (routing.md).
PROFILE_KEYS = {"Name", "GlobalProxy", "RemoteDNSType", "RemoteDNSDomain", "RemoteDNSIP",
                "DomesticDNSType", "DomesticDNSDomain", "DomesticDNSIP", "Geoipurl",
                "Geositeurl", "LastUpdated", "DnsHosts", "DirectSites", "DirectIp",
                "ProxySites", "ProxyIp", "BlockSites", "BlockIp", "DomainStrategy",
                "FakeDNS"}
PROFILE_LISTS = ("DirectSites", "DirectIp", "ProxySites", "ProxyIp", "BlockSites", "BlockIp")


async def main():
    await db.connect()
    await db.execute("DELETE FROM xray_users WHERE user_uuid='dc-1'")
    await db.execute("DELETE FROM users WHERE uuid='dc-1'")
    # Имя с кириллицей и пробелом — ровно то, на чём ломалась некодированная ссылка.
    await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ('Тест Имя','dc-1',TRUE)")
    await db.execute("INSERT INTO xray_users (user_uuid, xray_uuid, sub_token) "
                     "VALUES ('dc-1','11111111-2222-3333-4444-555555555555','tok-dc-0123456789')")
    for key, val in (("xray_public_key", "PUBKEY_abc-_"), ("xray_short_id", "ab12"),
                     ("xray_private_key", "PRIV"), ("server_host", "203.0.113.10"),
                     ("xray_dest", ""), ("xray_port", "")):
        await db.set_setting(key, val)

    print("=== ссылка vless:// по стандарту ===")
    link = await xray.profile_link("dc-1")
    parts = urlsplit(link)
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    print("   ", link[:110], "…")
    check("схема vless", parts.scheme == "vless")
    check("uuid на месте", parts.username == "11111111-2222-3333-4444-555555555555")
    check("адрес и порт", parts.hostname == "203.0.113.10" and parts.port == 443,
          "%s:%s" % (parts.hostname, parts.port))
    unknown = set(params) - LINK_PARAMS
    check("только параметры из стандарта", not unknown, str(unknown))
    check("encryption=none сказано явно", params.get("encryption") == "none",
          "как в примере из документации Happ")
    check("type=tcp", params.get("type") == "tcp")
    check("security=reality", params.get("security") == "reality")
    check("для REALITY есть pbk", bool(params.get("pbk")))
    check("для REALITY есть fp", bool(params.get("fp")))
    check("sni не пустой", bool(params.get("sni")))
    check("flow — Vision", params.get("flow") == "xtls-rprx-vision")
    check("имя после # закодировано", parts.fragment == quote("Тест Имя", safe=""),
          parts.fragment)
    check("и раскодируется обратно", unquote(parts.fragment) == "Тест Имя")

    print()
    print("=== вход сервера по эталону авторов Xray ===")

    async def fake_ips():
        return {"dc-1": "10.13.13.9"}

    xray.peer_ip_map = fake_ips
    config, _addrs, _note = await xray.build_config()
    ib = [i for i in config["inbounds"] if i.get("protocol") == "vless"][0]
    st = ib["streamSettings"]
    rs = st.get("realitySettings") or {}
    check("decryption none", ib["settings"].get("decryption") == "none")
    check("у людей flow Vision",
          all(c.get("flow") == "xtls-rprx-vision" for c in ib["settings"]["clients"]))
    check("network tcp", st.get("network") == "tcp")
    check("security reality", st.get("security") == "reality")
    check("REALITY: dest, serverNames, privateKey, shortIds",
          all(k in rs for k in ("dest", "serverNames", "privateKey", "shortIds")),
          str(sorted(rs)))
    sn = ib.get("sniffing") or {}
    check("sniffing включён", sn.get("enabled") is True, str(sn))
    check("sniffing распознаёт http, tls, quic",
          set(sn.get("destOverride") or []) == {"http", "tls", "quic"})
    check("sniffing только для маршрутизации", sn.get("routeOnly") is True)

    print()
    print("=== профиль маршрутизации по документации Happ ===")
    prof = await H.profile("dc-1")
    check("только ключи из документации", set(prof) <= PROFILE_KEYS,
          str(set(prof) - PROFILE_KEYS))
    check("GlobalProxy строкой", prof.get("GlobalProxy") == "true")
    check("FakeDNS строкой", prof.get("FakeDNS") in ("true", "false"))
    check("тип DNS из документированных",
          prof.get("RemoteDNSType") in ("DoH", "DoU") and
          prof.get("DomesticDNSType") in ("DoH", "DoU"))
    check("DomainStrategy из документированных",
          prof.get("DomainStrategy") in ("AsIs", "IPIfNonMatch", "IPOnDemand"))
    check("все шесть списков на месте",
          all(isinstance(prof.get(k), list) for k in PROFILE_LISTS),
          str([k for k in PROFILE_LISTS if not isinstance(prof.get(k), list)]))
    check("LastUpdated — время в unix", str(prof.get("LastUpdated", "")).isdigit())
    rlink = await H.link(uuid_val="dc-1")
    check("ссылка профиля happ://routing/onadd/{base64}",
          rlink.startswith("happ://routing/onadd/"))
    back = json.loads(base64.b64decode(rlink.rsplit("/", 1)[1]).decode())
    check("base64 раскрывается в тот же профиль", back == prof)

    print()
    print("=== заголовки подписки по документации Happ ===")
    import subscription as S
    resp = await S.handle_sub(type("R", (), {"match_info": {"token": "tok-dc-0123456789"},
                                              "headers": {"Accept": "*/*"},
                                              "remote": "203.0.113.5"})())
    hdr = {k.lower(): v for k, v in resp.headers.items()}
    check("profile-update-interval — целое", str(hdr.get("profile-update-interval", "")).isdigit(),
          str(hdr.get("profile-update-interval")))
    check("subscription-userinfo в формате документации",
          bool(re.fullmatch(r"upload=\d+; download=\d+; total=\d+; expire=\d+",
                            hdr.get("subscription-userinfo", ""))),
          hdr.get("subscription-userinfo", "-"))
    check("routing — ссылка профиля", hdr.get("routing", "").startswith("happ://routing/onadd/"))
    body = base64.b64decode(resp.body).decode()
    check("тело — base64 со ссылками", body.startswith("vless://"))

    await db.execute("DELETE FROM xray_users WHERE user_uuid='dc-1'")
    await db.execute("DELETE FROM users WHERE uuid='dc-1'")
    await db.set_setting("server_host", "")


asyncio.get_event_loop().run_until_complete(main())
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
