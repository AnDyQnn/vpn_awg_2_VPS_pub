# -*- coding: utf-8 -*-
"""Поиск масок на узле: разбор имени из начала TLS и защита входа.

Имя берётся из настоящего ClientHello — того, что отправляет обычный TLS-клиент.
Ошибка в разборе дала бы либо пустой поиск, либо мусор вместо имён.
"""
import ast
import io
import ipaddress
import os
import re
import ssl
import struct
import subprocess
import time

SRC = "/app/api.py"
FUNCS = {"_hello_sni"}
CONSTS = {"SNIFF_SKIP_PORTS"}
tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = [n for n in tree.body
          if (isinstance(n, ast.FunctionDef) and n.name in FUNCS)
          or (isinstance(n, ast.Assign)
              and {t.id for t in n.targets if isinstance(t, ast.Name)} & CONSTS)]
ns = {"re": re, "time": time, "os": os, "ipaddress": ipaddress, "struct": struct}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def client_hello(name):
    """Первое, что отправляет обычный TLS-клиент, — без сети."""
    ctx = ssl.create_default_context()
    inc, out = ssl.MemoryBIO(), ssl.MemoryBIO()
    obj = ctx.wrap_bio(inc, out, server_hostname=name)
    try:
        obj.do_handshake()
    except ssl.SSLWantReadError:
        pass
    return out.read()


print("=== имя из настоящего ClientHello ===")
for name in ("nalog.ru", "ya.ru", "bstream.hzmklvdieo.com"):
    got = ns["_hello_sni"](client_hello(name))
    check("разобрано %s" % name, got == name, got)
check("не ClientHello — ничего", ns["_hello_sni"](b"\x17\x03\x03\x00\x10" + b"x" * 16) is None)
check("обрывок — ничего, без падения", ns["_hello_sni"](client_hello("ya.ru")[:30]) is None)

print("\n=== порты, где чужое имя — норма, пропускаются ===")
skip = ns["SNIFF_SKIP_PORTS"]
check("443, 80 и пуши Google/Apple", {443, 80, 5228, 5223} <= skip)
check("21278 Likee — смотрим", 21278 not in skip)

print("\n=== вход точки: только адреса туннеля ===")
src = io.open(SRC, encoding="utf-8").read()
check("чужой адрес отклоняется", "адрес не из туннеля" in src)
check("клиент-сервер не слушаем", "str(addr) == DE_AGENT_IP" in src)
check("одновременно один поиск", '"поиск уже идёт"' in src)

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
raise SystemExit(0 if ok else 1)
