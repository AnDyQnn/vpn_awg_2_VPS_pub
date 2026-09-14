# -*- coding: utf-8 -*-
"""Вход Xray должен быть открыт снаружи — иначе протокол бессмыслен.

Найдено на бою. Узел рубил входящий 443 правилом, которое ставилось, когда на
этом порту стояла страница отказа: её закрывали от интернета, и это было верно.
Потом страница переехала на 8443, а на 443 встал Xray. Правило осталось.

Со стороны это выглядело как «конфиг не тот»: изнутри контейнера Reality
работал и отдавал настоящий сертификат маскировочного домена, а снаружи не
отвечало ничего. На узле к моменту находки накопилось 3333 отброшенных пакета —
это люди, которые подключались и молча ничего не получали.

Проверяется:
  • Xray включён — двери нет;
  • Xray выключен — дверь закрыта, за открытым портом никого оставлять нельзя;
  • переключение туда-обратно не плодит одинаковых правил.
"""
import subprocess
import sys

sys.path.insert(0, "/app")

import api                                         # noqa: E402

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-46s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def drop_rules():
    """Сколько правил «рубить входящий 443» стоит прямо сейчас."""
    out = subprocess.run("iptables -S INPUT", shell=True,
                         capture_output=True, text=True).stdout
    return [l for l in out.split("\n")
            if "--dport 443" in l and "-j DROP" in l and "eth0" in l]


subprocess.run("iptables -F INPUT", shell=True)

print("=== Xray выключен: дверь закрыта ===")
api.xray_port_gate(False)
check("правило стоит", len(drop_rules()) == 1, "правил: %d" % len(drop_rules()))

print()
print("=== Xray включён: дверь открыта ===")
api.xray_port_gate(True)
check("правила нет", len(drop_rules()) == 0, "правил: %d" % len(drop_rules()))

print()
print("=== переключение туда-обратно не плодит правил ===")
for _ in range(4):
    api.xray_port_gate(False)
check("после четырёх закрытий правило одно", len(drop_rules()) == 1,
      "правил: %d" % len(drop_rules()))
for _ in range(3):
    api.xray_port_gate(True)
check("после открытий правил нет", len(drop_rules()) == 0,
      "правил: %d" % len(drop_rules()))

print()
print("=== открытие при закрытой двери и наоборот ===")
api.xray_port_gate(False)
api.xray_port_gate(True)
api.xray_port_gate(True)
check("двойное открытие безопасно", len(drop_rules()) == 0)
api.xray_port_gate(False)
check("и закрытие после него срабатывает", len(drop_rules()) == 1)

subprocess.run("iptables -F INPUT", shell=True)

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
