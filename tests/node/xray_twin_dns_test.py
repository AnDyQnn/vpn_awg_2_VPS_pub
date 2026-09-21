# -*- coding: utf-8 -*-
"""Человек на Xray обязан получать ответы от нашего резолвера.

Ломалось это по-настоящему и выглядело как «Xray не работает»: российские
сайты открывались, забугорные нет. Разделение трафика тут ни при чём —
российские сервисы идут мимо туннеля своим DNS, а всё остальное спрашивает нас.

Поломок было две, и вторая важнее первой.

1. Цепочка ролей висит не только на транзите, но и на трафике, который
   рождается на самом узле, — а весь трафик людей на Xray именно такой.
   Обращение к резолверу попадало под замыкающий запрет роли.

2. Резолвер отвечал НЕ СО СВОЕГО адреса. Сокет на 0.0.0.0 выбирает обратный
   адрес по маршруту до спрашивающего; адреса-двойники живут на этом же узле,
   маршрут до них ведёт в петлю, и ядро подставляло в ответ сам адрес
   спрашивающего. Человек спросил 10.13.13.1, а ответ пришёл от него самого —
   такой ответ DNS-клиент выбрасывает. Это било по всем на Xray, а не только по
   тем, кому назначили роль.

Здесь поднимается настоящий резолвер из образа, а не заглушка: проверять надо
то, что работает на бою.
"""
import ast
import io
import json
import os
import socket
import subprocess
import time

SRC = "/app/api.py"
NEED_FUNCS = {"_hook_after_accounting", "_acl_ensure_chain", "_acl_rule_spec",
              "apply_acl"}
NEED_CONSTS = {"ACL_CHAIN", "ACL_STATE_FILE", "TUNNEL_NET", "DE_AGENT_IP",
               "NODE_IP", "VPN_SUBNET", "CONF_DIR"}

tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in NEED_FUNCS:
        picked.append(node)
    elif isinstance(node, ast.Assign):
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if names & NEED_CONSTS:
            picked.append(node)
ns = {"subprocess": subprocess, "os": os, "json": json, "time": time}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)

NODE = ns["NODE_IP"]
FREE = "10.13.13.131"      # двойник человека без роли
BOUND = "10.13.13.143"     # двойник человека с ролью
OWN_NAME = "homelab.vpn"
OWN_IP = "10.13.13.5"

print("=== стенд: адрес узла и два двойника, как на бою ===")
subprocess.run("ip link add xray0 type dummy", shell=True, stderr=subprocess.DEVNULL)
subprocess.run("ip link set xray0 up", shell=True)
subprocess.run("ip link add wg0 type dummy", shell=True, stderr=subprocess.DEVNULL)
subprocess.run(f"ip addr add {NODE}/24 dev wg0", shell=True, stderr=subprocess.DEVNULL)
subprocess.run("ip link set wg0 up", shell=True)
for a in (FREE, BOUND):
    subprocess.run(f"ip addr add {a}/32 dev xray0", shell=True, stderr=subprocess.DEVNULL)
print(subprocess.run("ip -o -4 addr show xray0", shell=True,
                     capture_output=True, text=True).stdout.strip())

os.makedirs("/etc/amnezia/amneziawg/cache/dns", exist_ok=True)
io.open("/etc/amnezia/amneziawg/dns_names.json", "w", encoding="utf-8").write(
    json.dumps({"names": {OWN_NAME: OWN_IP}, "upstreams": {}}))

PY = "/opt/venv/bin/python3" if os.path.exists("/opt/venv/bin/python3") else "python3"
# Вывод резолвера не прячем: если он не смог занять адрес узла, он об этом
# говорит, и это первое, что нужно увидеть при разборе падения.
res = subprocess.Popen([PY, "-u", "/app/dnsfilter.py"])


def query(src, name=OWN_NAME, dst=NODE, timeout=4):
    """Возвращает (описание, адрес-отправитель ответа)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.bind((src, 0))
    except OSError as e:
        return ("bind не вышел: %s" % e, None)
    pkt = b"\xab\xcd\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    for part in name.encode().split(b"."):
        pkt += bytes([len(part)]) + part
    pkt += b"\x00\x00\x01\x00\x01"
    try:
        s.sendto(pkt, (dst, 53))
        data, frm = s.recvfrom(512)
        return ("ответ %d б" % len(data), frm[0])
    except Exception as e:
        return ("НЕТ: %s" % type(e).__name__, None)
    finally:
        s.close()


# Резолверу нужно время подняться — но ждём по факту, а не вслепую.
ready = False
for _ in range(40):
    if query(NODE, timeout=1)[1]:
        ready = True
        break
    time.sleep(0.5)
assert ready, "резолвер не поднялся — стенд не годен"
print("резолвер поднялся")

print("\n=== без ролей: ответ обязан приходить С АДРЕСА УЗЛА ===")
ns["apply_acl"]([])
for a in (FREE, BOUND):
    what, frm = query(a)
    print("  %s -> %s, отправитель %s" % (a, what, frm))
    assert "ответ" in what, f"{a}: резолвер молчит даже без ролей"
    assert frm == NODE, (
        f"{a}: ответ пришёл от {frm}, а спрашивали {NODE} — "
        f"DNS-клиент такой ответ выбросит")
print("ответы уходят с адреса узла: ок")

print("\n=== роль у владельца двойника ===")
# Роль без единого разрешения — самый строгий случай: туннель закрыт целиком.
ns["apply_acl"]([{"ip": BOUND, "allow": []}])
print("цепочка:")
for line in subprocess.run(f"iptables -S {ns['ACL_CHAIN']}", shell=True,
                           capture_output=True, text=True).stdout.splitlines():
    print("   ", line)

what_b, frm_b = query(BOUND)
what_f, frm_f = query(FREE)
print("\n  %s (с ролью)  -> %s, отправитель %s" % (BOUND, what_b, frm_b))
print("  %s (без роли) -> %s, отправитель %s" % (FREE, what_f, frm_f))
assert "ответ" in what_f, "двойник без роли потерял резолвер — задето лишнее"
assert "ответ" in what_b, (
    "двойник с ролью не достучался до резолвера — имена не разрешаются, "
    "забугорные сайты не открываются")
assert frm_b == NODE, f"ответ пришёл от {frm_b} вместо {NODE}"
print("\nимена разрешаются при любой роли: ок")

print("\n=== панель узла обязана остаться закрытой ===")
t = socket.socket()
t.settimeout(3)
closed = False
try:
    t.bind((BOUND, 0))
    t.connect((NODE, 8000))
except Exception as e:
    closed = True
    print("  порт 8000 с двойника:", type(e).__name__)
finally:
    t.close()
assert closed, "панель узла открылась человеку на Xray"
print("панель закрыта: ок")

res.terminate()
try:
    res.wait(timeout=5)
except Exception:
    res.kill()
print("\nВСЁ ПРОШЛО")
