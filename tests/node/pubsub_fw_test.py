# -*- coding: utf-8 -*-
"""Охрана порта подписки: правила файрвола.

Главное, что здесь проверяется, — что правила вообще стоят в том месте, где
они работают. Ufw на опубликованные порты контейнеров не действует: Docker
пишет свои правила в PREROUTING и FORWARD раньше и ufw не спрашивает. Человек,
который напишет "ufw deny 2096", будет уверен, что порт закрыт, а он открыт.
Единственная цепочка, которую Docker зовёт сам и своими правилами не
перекрывает, — DOCKER-USER.

Вторая половина проверки — что ядро вообще умеет то, о чём мы просим. Правило
с недоступным модулем не ставится, iptables говорит об этом одной строкой в
stderr, и порт остаётся без охраны, хотя скрипт отработал "успешно".
"""
import os
import subprocess
import sys

ok = True
SCRIPT = "/scripts/public_sub.sh"


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-54s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# Скрипт написан на bash и пользуется BASH_SOURCE — под busybox-овым sh он не
# заработает. В образе узла bash не обязателен, поэтому ставим его сами.
if subprocess.run("command -v bash", shell=True, capture_output=True).returncode:
    sh("apk add --no-cache -q bash >/dev/null 2>&1")


# --------------------------------------------------------------- что написано

print("=== куда ставятся правила ===")
try:
    text = open(SCRIPT, encoding="utf-8").read()
except OSError as e:
    print("  ПРОВАЛ: скрипт не читается: %s" % e)
    sys.exit(1)

check("цепочка своя, а не общая", "-N VPN_SUB" in text or 'iptables -N "$CHAIN"' in text)
check("зацеплена в DOCKER-USER", "-I DOCKER-USER 1" in text,
      "ufw на порты контейнеров не действует")
check("ufw не считается защитой",
      "ufw здесь ничего не решает" in text,
      "иначе следующий человек будет искать причину не там")

print()
print("=== чем именно режем ===")
check("предел одновременных соединений", "--connlimit-above" in text)
check("предел частоты с одного адреса",
      "--hashlimit-mode srcip" in text)
check("потолок на весь порт",
      "--hashlimit-mode dstip" in text,
      "по адресу считать мало: поток может идти с тысячи")
check("отказ молчанием", text.count("-j DROP") >= 3 and "-j REJECT" not in text,
      "по молчанию сканер не отличит закрытый порт от занятого")
check("правила сужены до контейнера",
      "-d $CONT_IP --dport $CONT_PORT" in text,
      "иначе однажды заденут Xray или туннель")

print()
print("=== снятие возвращает всё как было ===")
check("цепочка отцепляется", "-D DOCKER-USER -j" in text)
check("и удаляется", '-X "$CHAIN"' in text)
check("таймер тоже снимается", "systemctl disable --now vpn-subcert.timer" in text)

print()
print("=== сертификат ===")
check("профиль shortlived", "--preferred-profile shortlived" in text,
      "остальные профили IP не принимают вовсе")
check("адрес отдельным флагом", "--ip-address" in text,
      "-d принимает только имя")
check("версия certbot проверяется", "NEED_MAJOR=5" in text,
      "--ip-address появился в 5.3, в apt версия старше на годы")
check("продление стоит таймером", "OnCalendar" in text)

# ------------------------------------------------------- умеет ли это ядро

print()
print("=== ядро умеет то, о чём мы просим ===")
sh("iptables -N TSTSUB 2>/dev/null")
sh("iptables -F TSTSUB")

rc1, out1 = sh("iptables -A TSTSUB -p tcp --dport 8080 -m conntrack --ctstate NEW "
               "-m connlimit --connlimit-above 8 --connlimit-mask 32 -j DROP")
check("connlimit доступен", rc1 == 0, out1.strip()[:70])

rc2, out2 = sh("iptables -A TSTSUB -p tcp --dport 8080 -m conntrack --ctstate NEW "
               "-m hashlimit --hashlimit-above 30/min --hashlimit-burst 10 "
               "--hashlimit-mode srcip --hashlimit-name tst_src -j DROP")
check("hashlimit по адресу доступен", rc2 == 0, out2.strip()[:70])

rc3, out3 = sh("iptables -A TSTSUB -p tcp --dport 8080 -m conntrack --ctstate NEW "
               "-m hashlimit --hashlimit-above 50/sec --hashlimit-burst 100 "
               "--hashlimit-mode dstip --hashlimit-name tst_all -j DROP")
check("hashlimit на весь порт доступен", rc3 == 0, out3.strip()[:70])

_, listed = sh("iptables -L TSTSUB -n")
check("все три правила встали", listed.count("DROP") == 3,
      "правило с недоступным модулем не ставится молча")

sh("iptables -F TSTSUB; iptables -X TSTSUB")

# ------------------------------------------------------- скрипт целиком

print()
print("=== скрипт отрабатывает целиком ===")
sh("iptables -N DOCKER-USER 2>/dev/null")
os.makedirs("/tmp/node/volumes/flags", exist_ok=True)
rc, out = sh("bash %s firewall /tmp/node 2>&1" % SCRIPT)
_, chain = sh("iptables -L VPN_SUB -n 2>&1")
check("цепочка создана", "VPN_SUB" in chain, chain.strip()[:70])
check("в ней три правила", chain.count("DROP") == 3,
      "поставлено: %d" % chain.count("DROP"))
_, hook = sh("iptables -L DOCKER-USER -n")
check("зацеплена в DOCKER-USER", "VPN_SUB" in hook, hook.strip()[:70])

rc, out = sh("bash %s firewall /tmp/node 2>&1" % SCRIPT)
_, hook2 = sh("iptables -L DOCKER-USER -n")
check("повторный запуск не плодит зацепок",
      hook2.count("VPN_SUB") == 1, "зацепок: %d" % hook2.count("VPN_SUB"))
_, chain2 = sh("iptables -L VPN_SUB -n")
check("и не плодит правил", chain2.count("DROP") == 3,
      "правил: %d" % chain2.count("DROP"))

print()
print("=== решение владельца переживает выкладку ===")
# Выкладка зовёт этот скрипт каждый раз. Без отметки первое же обновление молча
# отменяло бы решение закрыть подписку и снова открывало порт.
check("у выкладки свой режим", "  ensure)" in text,
      "он отличается от on ровно тем, что уважает отметку")
# Файл лежит в общей папке, а бит запуска обновление раздаёт только внутри
# папки ноды. Запуск "напрямую" молча упирался в «Permission denied», и шаг
# настройки подписки отрабатывал за секунду, ничего не сделав.
check("режим ensure не требует бита запуска",
      'exec bash "$0" on' in text,
      "иначе шаг молча ничего не делает")
check("и таймер продления тоже",
      "ExecStart=/bin/bash" in text)
check("отметка ставится при закрытии", ': > "$OFF_MARK"' in text)
check("и снимается при открытии вручную", 'rm -f "$OFF_MARK"' in text)
dep = "/nodescripts/deploy.sh"
check("выкладка зовёт именно ensure",
      os.path.exists(dep) and 'public_sub.sh" ensure' in
      open(dep, encoding="utf-8").read(),
      "иначе отметка ничего не значит")

sh('mkdir -p /tmp/node2/volumes/flags && : > /tmp/node2/volumes/flags/public_sub.off')
rc, out = sh("bash %s ensure /tmp/node2 2>&1" % SCRIPT)
check("закрытую подписку выкладка не открывает", "не трогаю" in out, out.strip()[:70])

print()
print("=== охрану возвращает сторож ===")
# Третья ступень лечения в стороже — перезапуск докера, а он стирает
# DOCKER-USER. Без возврата порт остался бы без охраны до следующего тика
# таймера, то есть до полусуток.
wd = "/scripts/vpn_watchdog.sh"
if os.path.exists(wd):
    wtext = open(wd, encoding="utf-8").read()
    check("сторож проверяет зацепку", "iptables -C DOCKER-USER -j VPN_SUB" in wtext)
    check("и возвращает её сам", "public_sub.sh\" firewall" in wtext)
    check("проверка в основном цикле", "    ensure_subguard" in wtext)
    check("без сертификата не трогает",
          'volumes/certs/fullchain.pem" ] || return 0' in wtext,
          "подписка не открыта — охранять нечего")
else:
    check("сторож доступен для проверки", False, "нет /scripts/vpn_watchdog.sh")

print()
print("=== сверка смотрит на порт, когда охрана уже вернулась ===")
# Перезапуск докера стирает DOCKER-USER, а возвращает правила шаг подписки.
# Сверка стояла ПЕРЕД ним и каждый раз видела молчащий вход: в отчёте после
# каждой выкладки лежало расхождение «сертификат есть, а порт молчит»,
# которого через минуту уже не было.
dep = "/nodescripts/deploy.sh"
if os.path.exists(dep):
    dtext = open(dep, encoding="utf-8").read()
    i_sub = dtext.find("public_sub.sh\" ensure")
    i_chk = dtext.find("contract_check.sh\" \"$NODE_DIR\"")
    check("оба шага на месте", i_sub > 0 and i_chk > 0,
          "подписка %d, сверка %d" % (i_sub, i_chk))
    check("сверка идёт после подписки", 0 < i_sub < i_chk,
          "иначе она врёт после каждой выкладки")
else:
    check("выкладка доступна для проверки", False, "нет /nodescripts/deploy.sh")

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
