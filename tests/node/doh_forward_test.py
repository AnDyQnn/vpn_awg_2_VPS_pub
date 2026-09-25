# -*- coding: utf-8 -*-
"""Запрет обходного DNS работает на транзите пиров, а не только на бумаге.

Что было: цепочка запрета стояла в FORWARD ниже общего «-i wg0 -j ACCEPT» и
не срабатывала ни разу — на боевом узле счётчик ноль. Телефон по умолчанию
спрашивает DNS поверх TLS (1.1.1.1:853), Chrome — поверх HTTPS; оба пути шли
мимо узла, и фильтр не видел ни одного запроса. Снаружи: «фильтры не
работают», хотя сам фильтр исправен. Тем же был мёртв замок панели агента.

Стенд повторяет боевой FORWARD: сначала общие ACCEPT, потом всё остальное
тем же порядком, что при старте узла. Пиры — в своих сетях за мостом wg0,
в интернет — через eth0 контейнера.

Проверяется:
  • тому, чей DNS узел забирает, закрыты 853 и DoH к известным резолверам;
  • тому, чей DNS не забирается, всё открыто, и обычный DNS к 1.1.1.1 жив —
    закрыть его значило бы выключить человеку интернет;
  • когда заворот на всех (есть имена), закрыто всем, кроме агента;
  • панель агента (:8000) пирам закрыта.
"""
import ast
import io
import json
import os
import re
import subprocess
import time
import typing

SRC = "/app/api.py"
tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = []
for node in tree.body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        continue
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        continue
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        node.decorator_list = []
    picked.append(node)
ns = {"subprocess": subprocess, "os": os, "json": json, "time": time, "re": re,
      "ipaddress": __import__("ipaddress"), "uuid": __import__("uuid"),
      "urllib": __import__("urllib.request"),
      "HTTPException": lambda status_code=500, detail="": Exception(detail),
      "BaseModel": type("BaseModel", (), {}),
      "List": typing.List, "Optional": typing.Optional,
      "Depends": lambda *a, **k: None, "Request": object,
      "FastAPI": lambda *a, **k: type("App", (), {
          "post": lambda self, *a, **k: (lambda f: f),
          "get": lambda self, *a, **k: (lambda f: f),
          "delete": lambda self, *a, **k: (lambda f: f)})()}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)
os.makedirs(ns["CONF_DIR"], exist_ok=True)

NODE, FILTERED, FREE, AGENT = "10.13.13.1", "10.13.13.50", "10.13.13.60", "10.13.13.254"
ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-60s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


# --- сеть: мост wg0, пиры и «агент» в своих сетях, интернет через eth0 ------
sh("ip link add wg0 type bridge && ip addr add %s/24 dev wg0 && ip link set wg0 up" % NODE)
for n, ip in (("p1", FILTERED), ("p2", FREE), ("de", AGENT)):
    sh("ip netns add %s" % n)
    sh("ip link add v%s type veth peer name eth0 netns %s" % (n, n))
    sh("ip link set v%s master wg0 && ip link set v%s up" % (n, n))
    # Адрес /32 и маршрут только через узел — как у пира в туннеле: друг до
    # друга пиры ходят через узел, а не напрямую по мосту.
    sh("ip -n %s addr add %s/32 dev eth0 && ip -n %s link set eth0 up "
       "&& ip -n %s link set lo up && ip -n %s route add %s dev eth0 "
       "&& ip -n %s route add default via %s dev eth0"
       % (n, ip, n, n, n, NODE, n, NODE))
    sh("ip route add %s/32 dev wg0" % ip)
sh("sysctl -qw net.ipv4.conf.all.send_redirects=0")
sh("sysctl -qw net.ipv4.conf.wg0.send_redirects=0")
sh("sysctl -qw net.ipv4.conf.wg0.proxy_arp=1")
sh("sysctl -qw net.ipv4.ip_forward=1")
sh("sysctl -qw net.bridge.bridge-nf-call-iptables=0")
sh("iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE")
# Боевой порядок FORWARD: общие ACCEPT ставит setup_network первыми.
sh("iptables -A FORWARD -i wg0 -j ACCEPT")
sh("iptables -A FORWARD -o wg0 -j ACCEPT")
ns["_insert_before_accept"](
    "FORWARD", "-i wg0 -o wg0 -p tcp --dport 8000 ! -s 10.13.13.1 -j DROP")
# Панель «агента» в его сети.
subprocess.Popen("ip netns exec de python3 -m http.server 8000 --bind %s" % AGENT,
                 shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)


def tcp(nsname, host, port):
    """ok — соединилось; refused — отказ (запрет узла); timeout — тишина."""
    r = sh("ip netns exec %s python3 -c \"\n"
           "import socket\n"
           "s=socket.socket();s.settimeout(4)\n"
           "try:\n s.connect(('%s',%d));print('ok')\n"
           "except ConnectionRefusedError: print('refused')\n"
           "except socket.timeout: print('timeout')\n"
           "except Exception as e: print('err',e)\n\"" % (nsname, host, port))
    return r.stdout.strip()


def udp_dns(nsname):
    """Обычный DNS к 1.1.1.1 напрямую: жив ли он у человека."""
    r = sh("ip netns exec %s python3 -c \"\n"
           "import socket,struct\n"
           "q=struct.pack('!HHHHHH',1,0x100,1,0,0,0)+b'\\x07example\\x03com\\x00\\x00\\x01\\x00\\x01'\n"
           "s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(4)\n"
           "s.sendto(q,('1.1.1.1',53))\n"
           "try: s.recv(512);print('ok')\n"
           "except Exception as e: print('нет',e)\n\"" % nsname)
    return r.stdout.strip()


print("=== вариант 1: фильтр лично одному, имён нет ===")
ns["save_dns_state"]({FILTERED: ["social"]}, "", [], [])
ns["rebuild_dns_chain"](clients={FILTERED: ["social"]}, names={}, everyone=False)
ns["doh_block_apply"](True)
fw = sh("iptables -S FORWARD").stdout.splitlines()
print("\n".join("    " + l for l in fw))
pos = {k: next((i for i, l in enumerate(fw) if k in l), 99)
       for k in ("DNS_BYPASS_SEL", "-i wg0 -j ACCEPT", "dport 8000")}
check("запрет обхода стоит выше общего ACCEPT",
      pos["DNS_BYPASS_SEL"] < pos["-i wg0 -j ACCEPT"], pos)
check("замок панели агента выше общего ACCEPT",
      pos["dport 8000"] < pos["-i wg0 -j ACCEPT"])

r = tcp("p1", "1.1.1.1", 853)
check("под фильтром: DNS поверх TLS (1.1.1.1:853) — отказ", r == "refused", r)
r = tcp("p1", "1.1.1.1", 443)
check("под фильтром: DNS поверх HTTPS (1.1.1.1:443) — отказ", r == "refused", r)
import socket  # noqa: E402
site = socket.gethostbyname("example.com")
r = tcp("p1", site, 443)
check("под фильтром: обычный сайт на 443 открыт", r == "ok", "%s → %s" % (site, r))
r = tcp("p2", "1.1.1.1", 853)
check("без фильтра: 853 не трогаем", r == "ok", r)
r = udp_dns("p2")
check("без фильтра: обычный DNS к 1.1.1.1 жив", r == "ok", r)

print("\n=== вариант 2: есть имена — DNS всей сети идёт через узел ===")
ns["rebuild_dns_chain"](clients={}, names={"дом.vpn": "10.13.13.5"}, everyone=False)
r = tcp("p2", "1.1.1.1", 853)
check("всем: 853 — отказ", r == "refused", r)
r = tcp("de", "1.1.1.1", 853)
check("агент в Германии не задет", r == "ok", r)

print("\n=== вариант 3: ни имён, ни фильтров ===")
ns["save_dns_state"]({}, "", [], [])
ns["rebuild_dns_chain"](clients={}, names={}, everyone=False)
r = tcp("p1", "1.1.1.1", 853)
check("никого не заворачиваем — никому не закрываем", r == "ok", r)
r = udp_dns("p1")
check("обычный DNS к 1.1.1.1 жив", r == "ok", r)

print("\n=== панель агента ===")
r = tcp("p1", AGENT, 8000)
check("пиру панель агента закрыта", r == "timeout", r)
r = sh("curl -s -o /dev/null -w '%%{http_code}' --max-time 4 http://%s:8000/" % AGENT).stdout
check("самому узлу — открыта", r == "200", r)

print("\n=== повторный запуск не плодит правил и не опускает их ===")
ns["doh_block_apply"](True)
ns["_insert_before_accept"](
    "FORWARD", "-i wg0 -o wg0 -p tcp --dport 8000 ! -s 10.13.13.1 -j DROP")
fw = sh("iptables -S FORWARD").stdout
check("выбор запрета один", fw.count("DNS_BYPASS_SEL") == 1, fw.count("DNS_BYPASS_SEL"))
check("замок панели один", fw.count("dport 8000") == 1, fw.count("dport 8000"))

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
