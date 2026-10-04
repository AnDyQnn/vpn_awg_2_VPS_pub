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
         "apply_pool_nets", "_insert_before_accept"}
CONSTS = {"CONF_DIR", "POOL_NET_CHAIN", "DE_AGENT_IP", "TUNNEL_NET", "VPN_SUBNET"}
tree = ast.parse(io.open(SRC, encoding="utf-8").read())
picked = [n for n in tree.body
          if (isinstance(n, ast.FunctionDef) and n.name in FUNCS)
          or (isinstance(n, ast.Assign)
              and {t.id for t in n.targets if isinstance(t, ast.Name)} & CONSTS)]
ns = {"os": os, "subprocess": subprocess, "ipaddress": ipaddress, "json": json,
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

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
raise SystemExit(0 if ok else 1)
