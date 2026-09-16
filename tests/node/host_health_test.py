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
print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
