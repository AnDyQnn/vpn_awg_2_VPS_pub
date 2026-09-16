# -*- coding: utf-8 -*-
"""Недельная проверка хоста доходит до того, кто её читает.

Проверка писала отчёт и завершалась с кодом ноль, но бот его не видел никогда:
скрипт лежит в общей папке `scripts/`, а `volumes` у каждой ноды свои — VPS_RU
или VPS_DE. Без аргумента путь брался от корня проекта, и отчёт ложился рядом с
ним, в папку, куда никто не смотрит.

Аудит при этом честно писал «ещё не отрабатывала» и был прав: за всё время
отчёт не доехал ни разу.

Второй скрытый дефект — счётчики. `grep -c` печатает 0 и возвращает единицу,
когда совпадений нет, а страховка `|| echo 0` дописывала ВТОРОЙ ноль. Значение
становилось «0\\n0», и сравнение с числом падало с «integer expression
expected» — посреди скрипта, тихо, с общим кодом выхода ноль.
"""
import json
import os
import subprocess
import sys

ok = True
SCRIPT = "/scripts/host_health.sh"


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-54s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


if subprocess.run("command -v bash", shell=True, capture_output=True).returncode:
    sh("apk add --no-cache -q bash >/dev/null 2>&1")

print("=== отчёт ложится в папку ноды, а не рядом с проектом ===")
# Стенд повторяет расположение на узле: общая scripts/ и папка ноды рядом.
root = "/tmp/hh_root"
sh("rm -rf %s" % root)
os.makedirs(root + "/VPS_RU/volumes/flags", exist_ok=True)
# Папку ноды узнают по compose-файлу — воспроизводим прод, а не упрощение.
open(root + "/VPS_RU/docker-compose.yml", "w").write("services: {}\n")
os.makedirs(root + "/scripts", exist_ok=True)
sh("cp %s %s/scripts/host_health.sh" % (SCRIPT, root))

rc, out = sh("bash %s/scripts/host_health.sh 2>&1" % root)
check("отработала без ошибок", rc == 0, out.strip()[:70])
check("на числах не спотыкается",
      "integer expression expected" not in out,
      "иначе проверка молча обрывается посередине")
check("ничего лишнего не выполняется",
      "command not found" not in out,
      "разорванный комментарий однажды стал командой")

want = root + "/VPS_RU/volumes/flags/host_health.json"
check("отчёт там, где его ищет бот", os.path.exists(want),
      want if os.path.exists(want) else "файла нет")

stray = root + "/volumes/flags/host_health.json"
check("рядом с проектом ничего не появилось", not os.path.exists(stray),
      "там его никто не читает")

print()
print("=== содержимое годится для чтения ===")
if os.path.exists(want):
    d = json.load(open(want, encoding="utf-8"))
    for key in ("disk_used_pct", "inode_used_pct", "var_log_mb", "zombies"):
        v = d.get(key)
        check("поле %s — число" % key, isinstance(v, (int, float)),
              "получили %r" % (v,))
    check("сказано, для какой ноды", bool(d.get("node")), str(d.get("node")))
else:
    check("отчёт читается", False, "файла нет")

print()
print("=== аргумент по-прежнему уважается ===")
os.makedirs("/tmp/hh_named/volumes/flags", exist_ok=True)
sh("bash %s/scripts/host_health.sh /tmp/hh_named" % root)
check("отчёт лёг в указанную папку",
      os.path.exists("/tmp/hh_named/volumes/flags/host_health.json"),
      "вызовы с явным путём не должны сломаться")

print()
print("=== счётчик зависших процессов ===")
# Их почти всегда ноль, и именно на нуле ломалась старая подстраховка.
rc2, out2 = sh("ps -eo stat= 2>/dev/null | grep -c '^Z'")
check("счёт даёт одно число", out2.strip().count("\n") == 0,
      "получили %r" % out2.strip())

sh("rm -rf %s /tmp/hh_named" % root)

print()
print("=== аудит не судит узел в момент перезапуска ===")
# Проверка через полминуты после пересоздания контейнера рисовала катастрофу на
# ровном месте: «ядро зависло», «wg0 не найден», «NAT отсутствует». Всё неправда
# — узел просто поднимался. Такой отчёт хуже, чем никакого.
for name, path in (("мастера", "/nodescripts/host_audit.sh"),
                   ("Германии", "/descripts/host_audit.sh")):
    if not os.path.exists(path):
        continue
    at = open(path, encoding="utf-8").read()
    check("аудит %s ждёт готовности узла" % name, "SETTLE_LEFT=90" in at,
          "иначе десять ложных ошибок при целом туннеле")
    check("ждёт ответа панели, а не просто паузы (%s)" % name,
          "api/health" in at.split("SETTLE_LEFT=90")[1][:400],
          "пауза вслепую ничего не гарантирует")

print()
print("=== проверки судят по делу, а не по настройке ===")
for name, path in (("мастера", "/nodescripts/host_audit.sh"),
                   ("Германии", "/descripts/host_audit.sh")):
    if not os.path.exists(path):
        continue
    at = open(path, encoding="utf-8").read()
    # Предупреждение про пароль было не про пароль, а про перебор. Перебор
    # закрывает fail2ban — значит и судить надо по нему, иначе проверка врёт.
    check("вход по паролю смотрит на стража перебора (%s)" % name,
          "fail2ban-client status sshd" in at,
          "иначе «уязвимо к брутфорсу» при живом страже")
    check("нет стража — это ошибка, а не примечание (%s)" % name,
          'страж перебора не работает' in at)
    # Мгновенный замер процессора ничего не значит: проверка часто идёт сразу
    # после сборки образов.
    check("загрузка судится по среднему за минуту (%s)" % name,
          "loadavg" in at and "LOAD_X100" in at,
          "мгновенный замер показывает 100% на ровном месте")
    check("заплатки знают про ежедневный проход (%s)" % name,
          "vpn-security-upgrade.timer" in at)

hm = "/scripts/ensure_host_maintenance.sh"
if os.path.exists(hm):
    mt = open(hm, encoding="utf-8").read()
    print()
    print("=== ежедневный проход по заплаткам ===")
    check("берёт только ветку безопасности",
          "/^Inst/ && /security/" in mt,
          "«обнови всё» задело бы docker и порвало туннель")
    check("ничего не устанавливает заново",
          "--only-upgrade" in mt,
          "тогда и удалять ничего не придётся")
    check("ждёт замок apt", "DPkg::Lock::Timeout" in mt)
    check("ежедневно, а не раз в неделю",
          "OnCalendar=*-*-* 03:40" in mt)
    print()
    print("=== лишний порт 22 снимается осторожно ===")
    check("только если SSH переехал", "SSH_EFF_PORT" in mt)
    check("и только если его никто не слушает",
          "ss -lnt" in mt and "ufw delete allow 22/tcp" in mt,
          "закрывать вход под собой нельзя")

print()
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
