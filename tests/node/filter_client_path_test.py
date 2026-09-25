# -*- coding: utf-8 -*-
"""Фильтр глазами пира, на узле без своего домена.

Клиент сидит в отдельной сети за интерфейсом `wg0` — как настоящий пир — и
спрашивает DNS у 1.1.1.1, как записано в его файле конфига. Узел обязан
забрать запрос себе (заворот DNS), ответить на закрытый сайт адресом страницы
отказа и показать её по HTTP и HTTPS.

Раскладку ставят те же функции узла, что и в бою (`save_dns_state`,
`apply_dns_filters`, `apply_dns_names`). Зона — «vpn», сертификата нет: так
живёт узел, где владелец ничего не настраивал.
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

CONF = "/etc/amnezia/amneziawg"
NODE, PERSON, OTHER = "10.13.13.1", "10.13.13.50", "10.13.13.60"
PY = "/opt/venv/bin/python3" if os.path.exists("/opt/venv/bin/python3") else "python3"
ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-56s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


# --- сеть: узел за wg0, два пира в своих сетях -----------------------------
sh("ip link add wg0 type bridge && ip addr add %s/24 dev wg0 && ip link set wg0 up" % NODE)
for n, ip in (("p1", PERSON), ("p2", OTHER)):
    sh("ip netns add %s" % n)
    sh("ip link add v%s type veth peer name eth0 netns %s" % (n, n))
    sh("ip link set v%s master wg0 && ip link set v%s up" % (n, n))
    sh("ip -n %s addr add %s/24 dev eth0 && ip -n %s link set eth0 up "
       "&& ip -n %s link set lo up" % (n, ip, n, n))
    # Всё — через узел, как у пира с AllowedIPs = 0.0.0.0/0.
    sh("ip -n %s route add default via %s" % (n, NODE))
sh("sysctl -qw net.ipv4.ip_forward=1")
sh("sysctl -qw net.bridge.bridge-nf-call-iptables=0 2>/dev/null")

# --- раскладка, как её ставит бот ------------------------------------------
os.makedirs(CONF + "/cache/dns", exist_ok=True)
open(CONF + "/cache/dns/social.txt", "w").write("0.0.0.0 facebook.com\n")
ns["save_dns_state"]({PERSON: ["social"]}, "https://t.me/example_bot", [], [])
ns["apply_dns_filters"]({PERSON: ["social"]}, everyone=False)
ns["apply_dns_names"]({"xn--80aicmhbn.vpn": NODE}, {}, "vpn")
redir = sh("iptables -t nat -S DNS_REDIR").stdout
print(redir)
check("DNS человека заворачивается на узел", "-s %s/32" % PERSON in redir)
check("имена: заворот всей сети туннеля", "-s 10.13.13.0/24" in redir)

if os.path.exists(CONF + "/block_page.pem"):
    os.remove(CONF + "/block_page.pem")
env = dict(os.environ, DNS_UPSTREAM="127.0.0.1:5399", BLOCK_CERT_DIR="/tmp/no-certs")
p = subprocess.Popen([PY, "-u", "/app/dnsfilter.py"], env=env,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
end = time.time() + 20
while time.time() < end:
    line = p.stdout.readline()
    if "DNS-фильтр слушает" in line:
        break
time.sleep(6)       # фильтр перечитывает состояние раз в пять секунд


def dig(nsname, name):
    r = sh("ip netns exec %s python3 -c \"\n"
           "import socket,struct\n"
           "q=struct.pack('!HHHHHH',1,0x100,1,0,0,0)+b''.join(bytes([len(x)])+x.encode() "
           "for x in '%s'.split('.'))+b'\\x00\\x00\\x01\\x00\\x01'\n"
           "s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(3)\n"
           "s.sendto(q,('1.1.1.1',53))\n"
           "try:\n d=s.recv(512)\n"
           " print(socket.inet_ntoa(d[-4:]) if d[3]&15==0 and d[7] else 'rcode=%%d'%%(d[3]&15))\n"
           "except Exception as e: print('нет ответа')\n\"" % (nsname, name))
    return (r.stdout or r.stderr).strip()


print("=== DNS пира к 1.1.1.1 ===")
a = dig("p1", "www.facebook.com")
check("закрытый сайт человеку → адрес страницы", a == NODE, a)
a = dig("p2", "www.facebook.com")
check("тот же сайт другому → не подменён", a != NODE, a)
a = dig("p2", "xn--80aicmhbn.vpn")
check("служебное имя «закрыто.vpn» → адрес узла", a == NODE, a)

print("\n=== страница отказа у пира ===")
r = sh("ip netns exec p1 curl -s --max-time 8 --resolve www.facebook.com:80:%s "
       "http://www.facebook.com/" % NODE)
check("http → «закрыт фильтром»", "Этот сайт закрыт фильтром" in r.stdout)
r = sh("ip netns exec p1 curl -sk --max-time 8 --resolve www.facebook.com:443:%s "
       "https://www.facebook.com/" % NODE)
check("https → «закрыт фильтром» (443 уведён на 8443)",
      "Этот сайт закрыт фильтром" in r.stdout, "rc=%d" % r.returncode)
r = sh("ip netns exec p2 curl -sk --max-time 8 --resolve xn--80aicmhbn.vpn:443:%s "
       "https://xn--80aicmhbn.vpn/" % NODE)
check("закрыто.vpn по https → страница", "Доступ к этому сервису закрыт" in r.stdout,
      "rc=%d" % r.returncode)

print("\n=== «Соцсети» закрывают и российские ===")
# Внешний список на стенде — только facebook; ВК и ОК приходят встроенным
# довеском категории.
for site in ("vk.com", "m.vk.com", "ok.ru", "m.ok.ru", "x.com"):
    a = dig("p1", site)
    check("%s → страница" % site, a == NODE, a)

print("\n=== «закрыть для всех»: общая категория и свой список ===")
ns["save_dns_state"]({}, "https://t.me/example_bot", ["social"], ["yandex.ru"])
ns["apply_dns_filters"]({}, everyone=True)
time.sleep(6)
for who in ("p1", "p2"):
    a = dig(who, "vk.com")
    check("%s: vk.com (общая категория) → страница" % who, a == NODE, a)
    a = dig(who, "www.yandex.ru")
    check("%s: www.yandex.ru (свой список) → страница" % who, a == NODE, a)
r = sh("ip netns exec p2 curl -s --max-time 8 --resolve www.yandex.ru:80:%s "
       "http://www.yandex.ru/" % NODE)
check("http → страница «закрыт фильтром»", "Этот сайт закрыт фильтром" in r.stdout)

p.terminate()
print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
