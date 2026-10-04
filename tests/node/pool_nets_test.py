# -*- coding: utf-8 -*-
"""Подсети своих групп закрываются по IP, а не только по DNS.

Likee при закрытых доменах подключается к сети Bigo по зашитым адресам —
фильтр по DNS этого не видит. Группа теперь принимает подсети, и узел режет их
файрволом тем же людям, у кого группа включена.

Проверяется на живом iptables и ipset:
  • подсети уходят в отдельный файл, домены — в обычный список;
  • правило стоит выше общего ACCEPT — иначе оно не срабатывает никогда;
  • запрет только тем, у кого группа; исключение из общей категории действует;
  • клиент-сервер не трогается никогда;
  • после перезапуска (цепочка пустая) всё встаёт из файлов;
  • группа исчезла — её набор убирается.
"""
import ast
import io
import ipaddress
import json
import os
import subprocess
import time

SRC = "/app/api.py"
FUNCS = {"_pool_net", "save_pool_list", "_pool_set_name", "read_pool_nets",
         "_pool_mask", "_read_pool_files", "read_pool_masks", "_mask_spec",
         "apply_pool_nets", "_insert_before_accept"}
CONSTS = {"CONF_DIR", "POOL_NET_CHAIN", "MASK_PREFIXES", "DE_AGENT_IP", "TUNNEL_NET", "VPN_SUBNET"}
tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = [n for n in tree.body
          if (isinstance(n, ast.FunctionDef) and n.name in FUNCS)
          or (isinstance(n, ast.Assign)
              and {t.id for t in n.targets if isinstance(t, ast.Name)} & CONSTS)]
ns = {"os": os, "subprocess": subprocess, "ipaddress": ipaddress, "json": json, "re": __import__("re"),
      "time": time}
exec(compile(ast.Module(body=picked, type_ignores=[]), SRC, "exec"), ns)

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print("  %s %-56s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout


# Обстановка узла: общий ACCEPT в FORWARD, как после setup_network.
subprocess.run("iptables -A FORWARD -i wg0 -j ACCEPT", shell=True)
cache = ns["CONF_DIR"] + "/cache/dns"
os.makedirs(cache, exist_ok=True)

print("=== группа делится на домены и подсети ===")
ns["save_pool_list"]("pool_likee_78c9", ["likee.video", "like.video",
                                         "169.136.158.0/24", "164.90.66.0/24"])
txt = io.open(cache + "/pool_likee_78c9.txt", encoding="utf-8").read().split()
nets = io.open(cache + "/pool_likee_78c9.nets", encoding="utf-8").read().split()
check("в списке DNS только домены", sorted(txt) == ["like.video", "likee.video"], txt)
check("подсети отдельно", sorted(nets) == ["164.90.66.0/24", "169.136.158.0/24"], nets)

print("\n=== правила ===")
clients = {"10.13.13.8": ["adult", "pool_likee_78c9"], "10.13.13.9": ["adult"]}
ns["apply_pool_nets"](clients, [], {})
setname = ns["_pool_set_name"]("pool_likee_78c9")
members = sh("ipset list %s" % setname)
check("набор заполнен", "169.136.158.0/24" in members and "164.90.66.0/24" in members)
chain = sh("iptables -S FLT_NETS")
check("запрет тому, у кого группа",
      "-s 10.13.13.8/32 -m set --match-set %s dst -j REJECT" % setname in chain)
check("у кого группы нет — запрета нет", "10.13.13.9" not in chain)
check("клиент-сервер не трогаем", "-s 10.13.13.254/32 -j RETURN" in chain)
fwd = [l for l in sh("iptables -S FORWARD").splitlines() if l.startswith("-A")]
hook = next((i for i, l in enumerate(fwd) if "-j FLT_NETS" in l), None)
acc = next((i for i, l in enumerate(fwd) if l.endswith("-j ACCEPT")), None)
check("цепочка выше общего ACCEPT", hook is not None and acc is not None and hook < acc,
      "%s < %s" % (hook, acc))

print("\n=== группа на всех, с исключением ===")
ns["apply_pool_nets"]({}, ["pool_likee_78c9"], {"10.13.13.5": ["pool_likee_78c9"]})
chain = sh("iptables -S FLT_NETS").splitlines()
ret = next((i for i, l in enumerate(chain) if "-s 10.13.13.5/32" in l and "RETURN" in l), None)
rej = next((i for i, l in enumerate(chain) if "-s 10.13.13.0/24" in l and "REJECT" in l), None)
check("исключённый пропущен раньше общего запрета",
      ret is not None and rej is not None and ret < rej)

print("\n=== повторное применение не плодит крючков ===")
ns["apply_pool_nets"](clients, [], {})
fwd = sh("iptables -S FORWARD")
check("крючок один", fwd.count("-j FLT_NETS") == 1, fwd.count("-j FLT_NETS"))

print("\n=== после перезапуска всё встаёт из файлов ===")
subprocess.run("iptables -F FLT_NETS", shell=True)
ns["apply_pool_nets"](clients, [], {})
check("запрет снова на месте", "-s 10.13.13.8/32" in sh("iptables -S FLT_NETS"))

print("\n=== группа без подсетей и пропавшая группа ===")
ns["save_pool_list"]("pool_likee_78c9", ["likee.video"])
check("файл подсетей убран", not os.path.exists(cache + "/pool_likee_78c9.nets"))
ns["apply_pool_nets"](clients, [], {})
check("набор группы удалён", setname not in sh("ipset list -n").split())
check("запретов не осталось", "REJECT" not in sh("iptables -S FLT_NETS"))

print("\n=== маски: файл и правила ===")
ns["save_pool_list"]("pool_likee_78c9", ["likee.video", "маска:nalog.ru",
                                         "mask:ya.ru", "маска:кривая"])
txt = io.open(cache + "/pool_likee_78c9.txt", encoding="utf-8").read().split()
masks = io.open(cache + "/pool_likee_78c9.masks", encoding="utf-8").read().split()
check("маски не попали в список DNS", txt == ["likee.video"], txt)
check("маски отдельно, кривая отброшена", masks == ["nalog.ru", "ya.ru"], masks)
ns["apply_pool_nets"](clients, [], {})
chain = sh("iptables -S FLT_NETS")
check("правило маски встало (модуль string есть)",
      # iptables показывает имя в шестнадцатеричном виде
      "-s 10.13.13.8/32" in chain and "nalog.ru".encode().hex() in chain
      and "! --dport 443" in chain,
      chain[-300:])
check("сброс, а не тишина", "tcp-reset" in chain)

print("\n=== маска на деле: тот же разбор, на петле ===")
# Правило узла стоит в FORWARD, а здесь проверяем само совпадение: ловит ли
# оно имя в начале TLS не на 443 и пропускает ли на 443.
import socket
import ssl
import threading

spec = ns["_mask_spec"]("nalog.ru")
subprocess.run("iptables -I OUTPUT -o lo %s -j REJECT --reject-with tcp-reset" % spec,
               shell=True)
got = {}


def serve(port):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)
    srv.settimeout(5)
    try:
        conn, _ = srv.accept()
        conn.settimeout(3)
        got[port] = conn.recv(2048)
    except Exception:
        got[port] = b""
    srv.close()


def hello(port, name):
    t = threading.Thread(target=serve, args=(port,))
    t.start()
    time.sleep(0.2)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    s = socket.create_connection(("127.0.0.1", port), timeout=3)
    result = "прошло"
    try:
        ctx.wrap_socket(s, server_hostname=name, do_handshake_on_connect=False).do_handshake()
    except ConnectionResetError:
        result = "сброшено"
    except Exception:
        pass
    t.join()
    return result, got.get(port, b"")


r1, data1 = hello(21278, "nalog.ru")
check("nalog.ru на 21278 — сброшено", r1 == "сброшено" and b"nalog.ru" not in data1, r1)
r2, data2 = hello(443, "nalog.ru")
check("nalog.ru на 443 — проходит", b"nalog.ru" in data2, r2)
r3, data3 = hello(21279, "maya.ru")
check("чужое имя на высоком порту — проходит", b"maya.ru" in data3, r3)
subprocess.run("iptables -D OUTPUT -o lo %s -j REJECT --reject-with tcp-reset" % spec,
               shell=True)

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
raise SystemExit(0 if ok else 1)
