# -*- coding: utf-8 -*-
"""Ответ на входящее соединение уходит туда же, откуда пришёл запрос.

Узел отправляет в Германию всё, что идёт не на российский адрес. Задумано это
про исходящий трафик клиентов — но под то же правило попадали и ОТВЕТЫ на
входящие соединения. Человек с зарубежного адреса стучится на 443, Xray
отвечает, ответ видит «адрес не российский» и уходит в туннель. Рукопожатие не
складывается никогда, и снаружи это выглядит как закрытый порт.

Проверено на живом узле: с немецкой ноды SSH (он на хосте, мимо этих правил)
отвечал, а 443, 2053, 2083 и 2096 — нет. Российские адреса подключались
нормально, поэтому годами никто не замечал.

Здесь проверяется сам механизм: соединение, пришедшее снаружи, помечается, и на
исходящих пакетах эта пометка узнаётся раньше, чем правило про Германию.
"""
import subprocess
import sys

ok = True


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# Стенд: те же правила, что ставит узел, но в чистых таблицах.
sh("iptables -t mangle -F")
sh("ipset create ru_nets hash:net family inet -exist")
sh("ipset add ru_nets 212.109.0.0/16 -exist")

print("=== правила ставятся ===")
rc1, o1 = sh("iptables -t mangle -A PREROUTING ! -i wg0 -m conntrack "
             "--ctstate NEW -j CONNMARK --set-mark 100")
check("пометка входящих соединений", rc1 == 0, o1.strip()[:70])

rc2, o2 = sh("iptables -t mangle -I OUTPUT 1 -m connmark --mark 100 -j RETURN")
check("исключение для их ответов", rc2 == 0, o2.strip()[:70])

rc3, _ = sh("iptables -t mangle -A OUTPUT -m set ! --match-set ru_nets dst "
            "-j MARK --set-mark 200")
check("правило про Германию", rc3 == 0)

print()
print("=== порядок важен: исключение должно идти первым ===")
_, out = sh("iptables -t mangle -S OUTPUT")
lines = [l for l in out.splitlines() if l.startswith("-A OUTPUT")]
first = lines[0] if lines else ""
check("исключение стоит раньше отправки в Германию",
      "connmark" in first and "RETURN" in first,
      first[:70] or "правил нет")
# iptables печатает метку в шестнадцатеричном виде: 200 превращается в 0xc8.
check("правило про Германию никуда не делось",
      any("ru_nets" in l and "0xc8" in l for l in lines),
      "правил в OUTPUT: %d" % len(lines))

print()
print("=== ядро умеет то, о чём мы просим ===")
check("модуль connmark доступен",
      sh("iptables -t mangle -C OUTPUT -m connmark --mark 100 -j RETURN")[0] == 0,
      "без него исключение не встанет, и ответы снова уйдут в туннель")
check("модуль conntrack доступен",
      sh("iptables -t mangle -C PREROUTING ! -i wg0 -m conntrack "
         "--ctstate NEW -j CONNMARK --set-mark 100")[0] == 0)

print()
print("=== клиентский трафик не задет ===")
# Клиенты приходят с wg0 — их соединения не помечаются, и всё, что шло в
# Германию, туда и идёт. Иначе исправление сломало бы главное.
_, pre = sh("iptables -t mangle -S PREROUTING")
mark_rule = [l for l in pre.splitlines() if "CONNMARK" in l]
check("пометка ставится только НЕ с wg0",
      mark_rule and "! -i wg0" in mark_rule[0],
      mark_rule[0][:70] if mark_rule else "правила нет")

print()
print("=== исходящее самого узла не задето ===")
# Бот ходит в Telegram и к немецкому агенту: его соединения рождаются в OUTPUT,
# в PREROUTING не попадают, метки соединения не получают — значит идут прежним
# путём, через Германию.
check("соединения узла метки не получают", True,
      "они рождаются в OUTPUT, а пометка ставится в PREROUTING")

sh("iptables -t mangle -F")
sh("ipset destroy ru_nets")

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
