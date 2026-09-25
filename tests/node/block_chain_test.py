# -*- coding: utf-8 -*-
"""Страница отказа целиком: DNS-ответ → заворот 443 → страница с сертификатом.

Остальные тесты смотрят на куски по отдельности. Здесь — вся цепочка на
настоящем DNS-фильтре и настоящем iptables, в обоих режимах узла:

  • без своего домена — зона «.vpn», страница на самоподписанном сертификате;
  • со своим доменом — зона «example.ru», страница на сертификате домена, и
    на своё имя («закрыто.example.ru») открывается без предупреждения.

И то, ради чего тест появился: на 443 узла теперь слушает подписка Clash Mi.
Запрос человека к странице отказа идёт на 10.13.13.1:443 и обязан попасть на
страницу (8443), а не на сервер подписки. А снаружи 443 — это подписка, и
заворот её трогать не должен.
"""
import ast
import io
import json
import os
import re
import socket
import struct
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
SITE = "www.facebook.com"            # в категории «соцсети»
CLOSED = "закрыто"                   # служебное имя узла
PY = "/opt/venv/bin/python3" if os.path.exists("/opt/venv/bin/python3") else "python3"

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-58s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def puny(name):
    return ".".join(p if p.isascii() else p.encode("idna").decode() for p in name.split("."))


def dns_a(name, src):
    """A-запрос к узлу с адреса человека. Адрес ответа или код ошибки."""
    q = struct.pack("!HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)
    for part in puny(name).split("."):
        q += bytes([len(part)]) + part.encode()
    q += b"\x00" + struct.pack("!HH", 1, 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((src, 0))
    s.settimeout(3)
    try:
        s.sendto(q, (NODE, 53))
        data = s.recv(512)
    except OSError as e:
        return "нет ответа (%s)" % e
    finally:
        s.close()
    rcode = data[3] & 0x0F
    if rcode:
        return "rcode=%d" % rcode
    if struct.unpack("!H", data[6:8])[0] == 0:
        return "пусто"
    return socket.inet_ntoa(data[-4:])


def curl(url, src, host_ip=None, extra=""):
    """Запрос с адреса человека. Возвращает (код curl, тело, строка subject)."""
    host = re.sub(r"^https?://([^/:]+).*$", r"\1", url)
    port = 443 if url.startswith("https") else 80
    res = "--resolve %s:%d:%s" % (host, port, host_ip) if host_ip else ""
    r = sh("curl -sv --max-time 8 --interface %s %s %s '%s' 2>/tmp/curl.err"
           % (src, res, extra, url))
    err = open("/tmp/curl.err", encoding="utf-8", errors="ignore").read()
    subj = next((l.strip() for l in err.splitlines() if "subject:" in l), "")
    return r.returncode, r.stdout, subj


# --- сеть узла --------------------------------------------------------------
sh("ip link add tun0 type dummy")
for a in ("%s/24" % NODE, "%s/32" % PERSON, "%s/32" % OTHER):
    sh("ip addr add %s dev tun0" % a)
sh("ip link set up dev tun0")
ns["ensure_block_page_reachable"]()
nat = sh("iptables -t nat -S OUTPUT").stdout
check("заворот 10.13.13.1:443 → 8443 стоит", "--to-ports 8443" in nat)

# Подставная подписка на 443 — как бот на боевом узле: 0.0.0.0, свой TLS.
sh("openssl req -x509 -newkey rsa:2048 -nodes -days 1 -keyout /tmp/sub.pem "
   "-out /tmp/sub.pem -subj '/CN=subscription' 2>/dev/null")
open("/tmp/sub.py", "w").write('''
import http.server, ssl
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b = b"SUBSCRIPTION-SERVER"
        self.send_response(200); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
s = http.server.HTTPServer(("0.0.0.0", 443), H)
c = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); c.load_cert_chain("/tmp/sub.pem")
s.socket = c.wrap_socket(s.socket, server_side=True)
s.serve_forever()
''')
sub = subprocess.Popen([PY, "/tmp/sub.py"])

# Фильтр «соцсети» — только человеку PERSON. Список категории — из кэша.
os.makedirs(CONF + "/cache/dns", exist_ok=True)
open(CONF + "/cache/dns/social.txt", "w").write("0.0.0.0 facebook.com\n")
json.dump({"clients": {PERSON: ["social"]}, "common": [], "custom": [],
           "bot_link": "https://t.me/example_bot"}, open(CONF + "/dns_filter.json", "w"))


def start_filter(zone, cert_dir):
    json.dump({"names": {puny("%s.%s" % (CLOSED, zone)): NODE}, "zone": zone},
              open(CONF + "/dns_names.json", "w"))
    env = dict(os.environ, DNS_UPSTREAM="127.0.0.1:5399", BLOCK_CERT_DIR=cert_dir)
    p = subprocess.Popen([PY, "-u", "/app/dnsfilter.py"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log = []
    end = time.time() + 20
    while time.time() < end:
        line = p.stdout.readline()
        log.append(line.strip())
        if "DNS-фильтр слушает" in line:
            break
    time.sleep(1)
    return p, log


def common_checks(zone, closed_url, redirect=False):
    print("\n  -- DNS --")
    check("закрытый сайт человеку → адрес страницы", dns_a(SITE, PERSON) == NODE,
          dns_a(SITE, PERSON))
    other = dns_a(SITE, OTHER)
    check("тот же сайт другому → не подменён", other != NODE, other)
    check("служебное имя «%s.%s» → адрес узла" % (CLOSED, zone),
          dns_a("%s.%s" % (CLOSED, zone), OTHER) == NODE)

    print("\n  -- страница по HTTP --")
    if not redirect:
        rc, body, _ = curl("http://%s/" % SITE, PERSON, NODE)
        check("закрытый сайт по http → страница «закрыт фильтром»",
              "Этот сайт закрыт фильтром" in body and "соцсети" in body, "curl=%d" % rc)
    else:
        svc = puny("%s.%s" % (CLOSED, zone))
        r = sh("curl -s -o /dev/null --max-time 8 --interface %s --resolve %s:80:%s "
               "-w '%%{http_code} %%{redirect_url}' http://%s/" % (PERSON, SITE, NODE, SITE))
        code, _, url = r.stdout.partition(" ")
        check("закрытый сайт по http → перенаправление на своё имя",
              code == "302" and url.startswith("https://%s/?site=%s&c=social&ref=" % (svc, SITE)),
              r.stdout[:90])
        # Переход по нему — страница на своём имени, сертификат проходит проверку.
        rc, body, _ = curl(url, PERSON, NODE, "--cacert /tmp/certs/fullchain.pem")
        check("по перенаправлению — страница без предупреждения, с тем сайтом",
              rc == 0 and "Этот сайт закрыт фильтром" in body and SITE in body
              and "соцсети" in body, "curl=%d" % rc)
        hits = open(CONF + "/dns_hits.jsonl").read() \
            if os.path.exists(CONF + "/dns_hits.jsonl") else ""
        check("переход не записан вторым инцидентом", svc not in hits)

    print("\n  -- страница по HTTPS: 443 уводится на неё, а не на подписку --")
    rc, body, subj = curl("https://%s/" % SITE, PERSON, NODE, "-k")
    check("закрытый сайт по https → страница, не подписка",
          "Этот сайт закрыт фильтром" in body and "SUBSCRIPTION" not in body,
          "curl=%d" % rc)
    check("сертификат — страницы отказа, а не подписки", subj and "subscription" not in subj,
          subj)
    rc, body, subj = curl(closed_url, OTHER, NODE, "-k")
    check("служебное имя по https → страница «доступ закрыт»",
          "Доступ к этому сервису закрыт" in body and "SUBSCRIPTION" not in body,
          "curl=%d" % rc)

    print("\n  -- подписка снаружи не задета --")
    eth = sh("ip -4 -o addr show eth0 | awk '{print $4}' | cut -d/ -f1").stdout.strip()
    r = sh("curl -sk --max-time 5 https://%s/" % eth)
    check("адрес узла снаружи :443 → подписка", r.stdout == "SUBSCRIPTION-SERVER",
          r.stdout[:40] or "rc=%d" % r.returncode)
    return subj


# --- РЕЖИМ 1: своего домена нет ----------------------------------------------
print("=== режим «без домена»: зона .vpn, самоподписанный ===")
if os.path.exists(CONF + "/block_page.pem"):
    os.remove(CONF + "/block_page.pem")
p, log = start_filter("vpn", "/tmp/no-certs")
check("страница поднялась на самоподписанном",
      any("8443 (самоподписанный)" in l for l in log), [l for l in log if "8443" in l])
closed = "https://%s.vpn/" % puny(CLOSED)
subj = common_checks("vpn", closed)
check("сертификат самоподписанный (CN=blocked)", "CN=blocked" in subj, subj)
rc, _, _ = curl(closed, OTHER, NODE)
check("без -k браузер ругается — это ожидаемо без домена", rc == 60, "curl=%d" % rc)
p.terminate()
p.wait()

# --- РЕЖИМ 2: свой домен и сертификат на него --------------------------------
print("\n=== режим «свой домен»: зона example.ru, сертификат домена ===")
os.makedirs("/tmp/certs", exist_ok=True)
sh("openssl req -x509 -newkey rsa:2048 -nodes -days 1 "
   "-keyout /tmp/certs/privkey.pem -out /tmp/certs/fullchain.pem -subj '/CN=example.ru' "
   "-addext 'subjectAltName=DNS:example.ru,DNS:*.example.ru' 2>/dev/null")
p, log = start_filter("example.ru", "/tmp/certs")
check("страница поднялась на сертификате домена",
      any("8443 (настоящий)" in l for l in log), [l for l in log if "8443" in l])
closed = "https://%s.example.ru/" % puny(CLOSED)
subj = common_checks("example.ru", closed, redirect=True)
check("сертификат домена", "example.ru" in subj, subj)
# Сертификат учебный, поэтому доверие ему задаём явно — как браузер доверяет
# Let's Encrypt. Главное: имя совпадает, и предупреждения нет.
rc, body, _ = curl(closed, OTHER, NODE, "--cacert /tmp/certs/fullchain.pem")
check("своё имя открывается без предупреждения", rc == 0 and "Доступ" in body,
      "curl=%d" % rc)
rc, _, _ = curl("https://%s/" % SITE, PERSON, NODE, "--cacert /tmp/certs/fullchain.pem")
check("чужой сайт — предупреждение, подменять чужой сертификат нельзя", rc != 0,
      "curl=%d" % rc)
p.terminate()
sub.terminate()

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
