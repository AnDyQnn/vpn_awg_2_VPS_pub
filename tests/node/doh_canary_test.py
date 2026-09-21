# -*- coding: utf-8 -*-
"""Браузер сам отключает свой DNS, если ответить ему «такого имени нет».

Firefox включает DNS поверх HTTPS по умолчанию и тем самым обходит фильтр. Но
сначала он спрашивает особое имя: если сеть отвечает на него отказом, он решает,
что у сети свои правила, и свой DNS не включает.

Это вежливый путь — браузер отказывается от обхода сам. Резать ему соединения мы
тоже умеем, но это грубее и заметнее.

Проверяется на настоящем резолвере из образа: важен именно КОД ответа. На «сервер
не смог» браузер попробует ещё раз другим путём, и только «такого нет» он
принимает и успокаивается.
"""
import io
import json
import os
import socket
import subprocess
import time

OWN_NAME = "homelab.vpn"
CANARY = "use-application-dns.net"
NORMAL = "example.com"

os.makedirs("/etc/amnezia/amneziawg/cache/dns", exist_ok=True)
io.open("/etc/amnezia/amneziawg/dns_names.json", "w", encoding="utf-8").write(
    json.dumps({"names": {OWN_NAME: "10.13.13.5"}, "upstreams": {}}))

PY = "/opt/venv/bin/python3" if os.path.exists("/opt/venv/bin/python3") else "python3"
res = subprocess.Popen([PY, "-u", "/app/dnsfilter.py"])


def ask(name, timeout=4):
    """Возвращает (код ответа, число записей)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    pkt = b"\xab\xcd\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
    for part in name.encode().split(b"."):
        pkt += bytes([len(part)]) + part
    pkt += b"\x00\x00\x01\x00\x01"
    try:
        s.sendto(pkt, ("127.0.0.1", 53))
        data, _ = s.recvfrom(512)
    except Exception as e:
        return ("нет ответа: %s" % type(e).__name__, -1)
    finally:
        s.close()
    rcode = data[3] & 0x0F
    answers = (data[6] << 8) | data[7]
    return (rcode, answers)


ready = False
for _ in range(40):
    if ask(OWN_NAME, timeout=1)[1] >= 0:
        ready = True
        break
    time.sleep(0.5)
assert ready, "резолвер не поднялся — проверять нечем"
print("резолвер поднялся")

print("\n=== своё имя отвечает как раньше ===")
rcode, answers = ask(OWN_NAME)
print("  код:", rcode, "записей:", answers)
assert rcode == 0 and answers >= 1, "своё имя перестало разрешаться"
print("  ок")

print("\n=== служебное имя браузера: «такого нет» ===")
rcode, answers = ask(CANARY)
print("  код:", rcode, "записей:", answers)
assert rcode == 3, (
    f"код ответа {rcode}, а нужен 3 — «такого имени нет». На любой другой "
    f"браузер попробует ещё раз и включит свой DNS в обход фильтра")
assert answers == 0, "в отказе не должно быть записей"
print("  браузер отключит свой DNS сам: ок")

print("\n=== это не попало в журнал попыток ===")
# Нарушения тут нет: спрашивает сам браузер, а не человек лезет на запрещённое.
# Попади это в журнал — владелец увидел бы десятки «нарушений» на ровном месте.
hits = "/etc/amnezia/amneziawg/dns_hits.jsonl"
body = io.open(hits, encoding="utf-8").read() if os.path.exists(hits) else ""
assert CANARY not in body, "служебное имя записалось как нарушение"
print("  журнал чист: ок")

print("\n=== обычное имя не задето ===")
rcode, answers = ask(NORMAL, timeout=6)
print("  код:", rcode, "записей:", answers)
assert rcode != 3, "обычное имя стало отвечать «такого нет»"
print("  ок")

res.terminate()
try:
    res.wait(timeout=5)
except Exception:
    res.kill()
print("\nВСЁ ПРОШЛО")
