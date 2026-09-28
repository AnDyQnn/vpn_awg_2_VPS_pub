# -*- coding: utf-8 -*-
"""Заход на адрес самого узла — не инцидент «доступы».

Человеку с ролью веб-запрос к закрытому адресу туннеля уводится на страницу
отказа, и страница пишет инцидент. Сам узел (10.13.13.1) в это правило тоже
попадал: браузер или проверка связи в приложении заходили на адрес узла — и
владельцу приходила тревога «доступы» про место, где закрывать нечего.

Проверяется:
  • в цепочке заворота адрес узла пропускается раньше любого заворота;
  • страница на запрос к адресу узла инцидент не пишет;
  • запрос к закрытому сервису по-прежнему пишет.
"""
import ast
import asyncio
import io
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "/app")

SRC = "/app/api.py"
NEED_FUNCS = {"_acl_web_ensure_chain", "apply_acl_web", "_acl_rule_spec"}
NEED_CONSTS = {"ACL_WEB_CHAIN", "ACL_WEB_PORTS", "BLOCK_PAGE_IP", "TUNNEL_NET",
               "VPN_SUBNET", "NODE_IP", "DE_AGENT_IP"}
tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = [n for n in tree.body
          if (isinstance(n, ast.FunctionDef) and n.name in NEED_FUNCS)
          or (isinstance(n, ast.Assign)
              and {t.id for t in n.targets if isinstance(t, ast.Name)} & NEED_CONSTS)]
ns = {"subprocess": subprocess, "os": os, "json": json, "time": time}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)

import dnsfilter                                   # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


print("=== заворот на страницу пропускает сам узел ===")
ns["apply_acl_web"]([{"ip": "10.13.13.2", "allow": []}])
rules = subprocess.run("iptables -t nat -S %s" % ns["ACL_WEB_CHAIN"], shell=True,
                       capture_output=True, text=True).stdout.splitlines()
node_ret = [i for i, l in enumerate(rules) if "-d 10.13.13.1/32" in l and "RETURN" in l]
first_dnat = [i for i, l in enumerate(rules) if "DNAT" in l]
check("исключение для узла есть", node_ret)
check("и стоит раньше заворота", node_ret and first_dnat and node_ret[0] < first_dnat[0])


class Writer:
    def __init__(self):
        self.data = b""

    def write(self, b):
        self.data += b

    async def drain(self):
        pass

    def close(self):
        pass

    def get_extra_info(self, name):
        return ("10.13.13.2", 50000) if name == "peername" else None


async def ask(host):
    r = asyncio.StreamReader()
    r.feed_data(("GET / HTTP/1.1\r\nHost: %s\r\n\r\n" % host).encode())
    r.feed_eof()
    w = Writer()
    await dnsfilter.handle_http(r, w)
    return w.data


def hits():
    if not os.path.exists(dnsfilter.HITS_FILE):
        return []
    return [json.loads(l) for l in io.open(dnsfilter.HITS_FILE, encoding="utf-8") if l.strip()]


dnsfilter.HITS_FILE = "/tmp/node_self_hits.jsonl"
if os.path.exists(dnsfilter.HITS_FILE):
    os.unlink(dnsfilter.HITS_FILE)
dnsfilter._hit_seen.clear()
dnsfilter._hit_refs.clear()

print("\n=== страница: адрес узла — без инцидента ===")
page = asyncio.run(ask("10.13.13.1"))
check("страница отдана", b"200 OK" in page)
check("инцидента нет", not [h for h in hits() if h.get("domain") == "10.13.13.1"], hits())

print("\n=== закрытый сервис — инцидент по-прежнему пишется ===")
asyncio.run(ask("10.13.13.5"))
got = [h for h in hits() if h.get("domain") == "10.13.13.5"]
check("инцидент записан", got, got)

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
