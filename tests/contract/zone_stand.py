# -*- coding: utf-8 -*-
"""Стенд: настоящий бот против настоящего узла — зона имён и фильтры.

Запускается в контейнере бота, в сети контейнера узла (как в бою). Путь
установки, где владелец ничего не настраивал, и дальше:

  1. свежий узел без домена: зона «vpn», служебное имя «закрыто.vpn»,
     своё имя человеку, фильтр — всё доезжает до узла и отвечает в DNS;
  2. владелец задал домен: имена переезжают в «example.ru»;
  3. владелец убрал домен: имена возвращаются в «vpn».

Адреса пиров 10.13.13.2–5 заранее висят на узле как свои (так делает
запускающий скрипт) — иначе спросить DNS «от имени пира» изнутри нельзя.
"""
import asyncio
import json
import os
import socket
import ssl
import struct
import uuid

import aiohttp

from database import db
import dnsnames as dn
from restrictions import reapply
from utils import WG_API_URL, api_session
from wireguard_manager import create_peer

NODE = "10.13.13.1"
ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-58s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def dns_a(name, src):
    q = struct.pack("!HHHHHH", 7, 0x0100, 1, 0, 0, 0)
    for part in dn.to_punycode(name).split("."):
        q += bytes([len(part)]) + part.encode()
    q += b"\x00" + struct.pack("!HH", 1, 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((src, 0))
    s.settimeout(3)
    try:
        s.sendto(q, (NODE, 53))
        d = s.recv(512)
    except OSError:
        return "нет ответа"
    finally:
        s.close()
    if d[3] & 15:
        return "rcode=%d" % (d[3] & 15)
    return socket.inet_ntoa(d[-4:]) if d[7] else "пусто"


def https_page(host, src):
    """Запрос по https на адрес страницы с адреса пира: текст и сертификат."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    raw = socket.create_connection((NODE, 443), timeout=5, source_address=(src, 0))
    with ctx.wrap_socket(raw, server_hostname=dn.to_punycode(host)) as s:
        cert = s.getpeercert(binary_form=True) or b""
        s.sendall(("GET / HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n"
                   % dn.to_punycode(host)).encode())
        body = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            body += chunk
    return body.decode("utf-8", "ignore"), cert


async def node_get(path):
    async with api_session() as s:
        async with s.get(f"{WG_API_URL}{path}", timeout=aiohttp.ClientTimeout(total=10)) as r:
            return await r.json()


async def phase(title, zone_name, person_ip, other_ip):
    print("\n=== %s ===" % title)
    moved, clashed = await dn.migrate_zone()
    await dn.ensure_node_name()
    good, msg = await dn.apply_names(title)
    check("зона бота «%s»" % zone_name, dn.zone() == zone_name)
    check("имена разложены на узел", good, msg)
    names = (await node_get("/dns/names")).get("names", {})
    svc = "%s.%s" % (dn.NODE_HEAD, zone_name)
    check("служебное имя «%s» на узле" % svc,
          names.get(dn.to_punycode(svc)) == NODE, "имён: %d" % len(names))
    check("своё имя «дом.%s» → адрес человека" % zone_name,
          names.get(dn.to_punycode("дом." + zone_name)) == person_ip)
    stale = [n for n in names if "." in n and not n.endswith(dn.to_punycode(zone_name))]
    check("в старой зоне ничего не осталось", not stale, stale[:3])
    check("служебное имя одно, без двойника",
          sum(1 for n in names if n.startswith(dn.to_punycode(dn.NODE_HEAD) + ".")) == 1)

    print("  -- DNS глазами пира --")
    check("«%s» → узел" % svc, dns_a(svc, other_ip) == NODE, dns_a(svc, other_ip))
    check("«дом.%s» → человек" % zone_name,
          dns_a("дом." + zone_name, other_ip) == person_ip)
    check("короткое «дом» → человек", dns_a("дом", other_ip) == person_ip)
    got = dns_a("www.facebook.com", person_ip)
    check("под фильтром: facebook → страница", got == NODE, got)
    got = dns_a("www.facebook.com", other_ip)
    check("без фильтра: facebook не подменён", got != NODE, got)

    print("  -- страница отказа по https --")
    body, cert = https_page("www.facebook.com", person_ip)
    check("закрытый сайт → «закрыт фильтром»", "Этот сайт закрыт фильтром" in body)
    body, cert = https_page(svc, other_ip)
    check("«%s» → страница узла" % svc, "Доступ к этому сервису закрыт" in body)
    return moved, clashed


async def main():
    await db.connect()
    os.environ["PUBLIC_DOMAIN"] = ""
    for key in (dn.ZONE_KEY, dn.NODE_NAME_KEY, dn.NODE_NAME_DONE):
        await db.execute("DELETE FROM settings WHERE key=$1", key)
    await db.execute("DELETE FROM dns_names")
    await db.execute("DELETE FROM users WHERE name LIKE 'zs-%'")

    print("=== свежая установка: два человека ===")
    ids = {}
    for name in ("zs-anna", "zs-boris"):
        uid = str(uuid.uuid4())
        await db.execute("INSERT INTO users (name, uuid, is_active) VALUES ($1,$2,TRUE)",
                         name, uid)
        _, conf_path, _ = await create_peer(name, uid=uid)
        conf = open(conf_path, encoding="utf-8").read()
        ip = next(l.split("=", 1)[1].strip().split("/")[0]
                  for l in conf.splitlines() if l.startswith("Address"))
        ids[name] = (uid, ip)
        print("  %s → %s" % (name, ip))
    (anna, anna_ip), (boris, boris_ip) = ids["zs-anna"], ids["zs-boris"]
    dns_line = next(l for l in conf.splitlines() if l.startswith("DNS"))
    print("  строка DNS в конфиге:", dns_line)

    name, err = dn.normalize("дом")
    check("«дом» дополняется локальной зоной", name == "дом.vpn", name or err)
    await db.set_dns_name(name, target_uuid=anna)
    await db.set_user_filter(anna, "social", True)
    good, msg = await reapply("стенд")
    check("фильтр разложен на узел", good, msg)
    flt = await node_get("/dns/filters")
    check("узел: фильтр на адресе Анны", flt.get("clients", {}).get(anna_ip) == ["social"],
          flt.get("clients"))

    # Список категории на стенде подкладывает запускающий скрипт: качать с
    # GitHub здесь незачем, проверяется не загрузка, а цепочка.
    await asyncio.sleep(6)

    await phase("1. без домена", "vpn", anna_ip, boris_ip)

    os.environ["PUBLIC_DOMAIN"] = "example.ru"
    moved, _ = await phase("2. владелец задал домен", "example.ru", anna_ip, boris_ip)
    check("переехали имена", moved >= 2, "переехало: %d" % moved)

    os.environ["PUBLIC_DOMAIN"] = ""
    moved, _ = await phase("3. владелец убрал домен", "vpn", anna_ip, boris_ip)
    check("вернулись имена", moved >= 2, "переехало: %d" % moved)

    print("\nВСЁ ПРОШЛО" if ok else "\nЕСТЬ ПРОВАЛЫ")


asyncio.run(main())
