# -*- coding: utf-8 -*-
"""Выкладку не убивает перезапуск демона, который её запустил.

Владелец нажал «обновить», бот отчитался, версия в репозитории сменилась — а
контейнеры остались на прежней. Ни отката, ни ошибки, ни сообщения.

Что произошло. Демон обновления запускал deploy.sh своим ребёнком. В конце
выкладки deploy.sh планирует перезапуск этого демона — отложенный на пятнадцать
секунд, чтобы тот подхватил новый код. Пока выкладка одна, всё сходится: она уже
закончилась, перезапускать безопасно.

Но выкладки шли подряд: первая завершилась в 10:34:05 и запланировала
перезапуск, демон тут же увидел вторую метку и в 10:34:11 начал вторую выкладку.
В 10:35:12 сработал отложенный перезапуск — и systemd, останавливая службу,
снёс всё её дерево процессов. Вторая выкладка умерла между `git pull` и
сборкой: код новый, образы старые.

Молча — потому что убитый процесс не пишет прощальных слов, а метку «обновление
удалось» ставит только успешный конец.

Починка: выкладка живёт своей службой. Демон перезапускается сколько угодно —
выкладка этого не замечает. Одно имя службы на всех заодно делает две
одновременные выкладки невозможными.

Проверяем не текстом, а поведением: достаём функцию из скрипта как есть и
запускаем с подставными systemd-run и systemctl.
"""
import os
import re
import subprocess
import sys

ok = True
RU = "/nodescripts/host_updater.sh"
DE = "/descripts/host_updater.sh"
RU_DEPLOY = "/nodescripts/deploy.sh"
DE_DEPLOY = "/descripts/deploy.sh"
STAND = "/tmp/du"


def check(name, cond, detail=""):
    global ok
    ok = ok and cond
    print("  %s %-52s %s" % ("•" if cond else "ПРОВАЛ:", name, detail))


def sh(cmd):
    r = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def func_body(path):
    """Текст функции run_deploy из самого скрипта — без копий и пересказов."""
    src = read(path)
    m = re.search(r"^run_deploy\(\) \{.*?^\}$", src, re.S | re.M)
    return m.group(0) if m else ""


def stand(systemd_run=True, deploy_running=False):
    """Стенд: подставные systemd-run и systemctl, подставной deploy.sh."""
    sh("rm -rf %s; mkdir -p %s/bin" % (STAND, STAND))
    with open(STAND + "/deploy.sh", "w") as f:
        f.write("#!/bin/sh\necho ВЫКЛАДКА-ПОШЛА >> %s/ran\n" % STAND)
    with open(STAND + "/bin/systemctl", "w") as f:
        f.write("#!/bin/sh\necho \"systemctl $*\" >> %s/calls\n"
                "exit %d\n" % (STAND, 0 if deploy_running else 1))
    if systemd_run:
        with open(STAND + "/bin/systemd-run", "w") as f:
            # Настоящий systemd-run запускает то, что ему передали. Повторяем:
            # иначе «запустили службу» было бы не отличить от «ничего не сделали».
            f.write("#!/bin/sh\n"
                    "echo \"systemd-run $*\" >> %s/calls\n"
                    "for a in \"$@\"; do p=\"$c\"; c=\"$a\"; done\n"
                    "\"$p\" \"$c\"\n" % STAND)
    sh("chmod +x %s/bin/* %s/deploy.sh" % (STAND, STAND))


def run(path):
    """Запускает run_deploy из скрипта на стенде и возвращает, что случилось."""
    harness = "%s/h.sh" % STAND
    with open(harness, "w", encoding="utf-8") as f:
        f.write("#!/bin/bash\n")
        f.write("PATH=%s/bin:$PATH\n" % STAND)
        f.write("SCRIPT_DIR=%s\n" % STAND)
        f.write(func_body(path) + "\n")
        f.write("run_deploy\n")
    code, out = sh("bash %s" % harness)
    calls = read(STAND + "/calls") if os.path.exists(STAND + "/calls") else ""
    ran = os.path.exists(STAND + "/ran")
    return code, out, calls, ran


for name, path, deploy_path in (("мастер", RU, RU_DEPLOY),
                                ("Германия", DE, DE_DEPLOY)):
    print("=== %s ===" % name)
    body = func_body(path)
    check("выкладка вынесена в run_deploy", bool(body),
          "иначе она снова ребёнок демона")

    upd = read(path)
    branch = upd[upd.index("UPDATE_FLAG\" ]"):] if "UPDATE_FLAG\" ]" in upd else ""
    branch = branch[:400]
    check("метка обновления зовёт run_deploy",
          "run_deploy" in branch and 'bash "$SCRIPT_DIR/deploy.sh"' not in branch,
          "прямой вызов делает выкладку ребёнком демона")

    stand()
    code, out, calls, ran = run(path)
    check("выкладка запущена", ran, out.strip()[:60])
    check("и запущена отдельной службой", "systemd-run" in calls)
    check("у службы своё имя", "--unit=vpn-deploy" in calls,
          "перезапуск демона по имени её не заденет")
    check("демон дожидается конца", "--wait" in calls,
          "иначе метка снимется раньше, чем выкладка сделает дело")
    check("служба убирается за собой", "--collect" in calls,
          "иначе второе обновление упрётся в занятое имя")
    check("код возврата доходит", code == 0, "код %d" % code)

    stand(deploy_running=True)
    code, out, calls, ran = run(path)
    check("вторую выкладку поверх идущей не начинаем", not ran,
          "две сборки разом — это гонка за один и тот же тег образа")

    stand(systemd_run=False)
    code, out, calls, ran = run(path)
    check("без systemd выкладка всё равно идёт", ran,
          "запасной путь важнее удобства")

    dep = read(deploy_path)
    m = re.search(r"systemctl restart \"?([a-z-]+)", dep)
    restarted = m.group(1) if m else ""
    # Имя демона на нодах разное (vpn-updater и de-agent-updater), а вот
    # выкладка зовётся одинаково — и не должна совпасть ни с одним из них.
    check("в конце перезапускается именно демон, а не выкладка",
          restarted.endswith("updater"), restarted or "не нашли")
    check("демон и выкладка — разные службы", restarted != "vpn-deploy",
          "совпади имена — перезапуск снова убивал бы выкладку")

    sched = dep[dep.index("systemd-run --on-active"):][:400]
    # У таймеров systemd погрешность по умолчанию — минута: «через 15 секунд»
    # срабатывало через 65 и попадало в середину следующей выкладки.
    check("срок перезапуска настоящий, а не «плюс-минус минута»",
          "AccuracySec" in sched, "иначе 15 секунд превращаются в 65")
    # Имя единицы постоянное. Без уборки следующее планирование упирается в
    # занятое имя, и демон не перезапускается вовсе — молча.
    check("отработавшая единица убирается", "--collect" in sched,
          "иначе второй раз назначить перезапуск не выйдет")
    check("неудача планирования не глотается",
          "|| true" not in sched and "Не удалось назначить" in dep,
          "молчание здесь означает демон на старом коде")
    print()

print("ВСЁ ПРОШЛО" if ok else "ЕСТЬ ПРОВАЛЫ")
sys.exit(0 if ok else 1)
