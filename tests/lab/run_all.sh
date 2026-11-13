#!/bin/bash
# Стенд установки: чистая Ubuntu → install.sh RU и DE → туннель → всё остальное.
#
#   bash tests/lab/run_all.sh                  — 22.04 24.04 25.04 25.10 26.04
#   bash tests/lab/run_all.sh 24.04 26.04      — выборочно
#
# Каждая версия — пара контейнеров с systemd и своим docker внутри, как
# настоящие VPS: apt, ufw, sshd, fail2ban, systemd-службы проекта. Репозиторий
# клонируется с GitHub, как у людей, а поверх кладётся рабочий код этой
# машины — проверяется то, что ещё не запушено.
#
# Этап 1 (run_pair.sh): установка обоих узлов с ответами на вопросы, перенос
#   ключа для Германии, рукопожатие, check_network.sh.
# Этап 2 (stage2.sh): службы, аудит, проверка хоста, уборка, сверка; обновление
#   «как по кнопке» (ставит код с GitHub!); падение соседа и сторож;
#   перезагрузка обоих серверов; повторная установка RU; fail2ban.
#
# Нужен docker с правом на --privileged (Docker Desktop или Linux). Итоги —
# в tests/out/lab/<версия>-summary.log, подробности — рядом.
#
# Чего стенд не воспроизводит: AppArmor и сжатые модули ядра Ubuntu (ядро
# здесь хостовое), настоящий внешний адрес узла (ключ для DE получает адрес
# контейнера RU) и Telegram (токен бота выдуманный — бот перезапускается).
set -u
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$(dirname "$HERE")")"
L="${LAB_LOGS:-$ROOT/tests/out/lab}"; mkdir -p "$L"
VERSIONS="${*:-22.04 24.04 25.04 25.10 26.04}"

for v in $VERSIONS; do
    docker build -q --build-arg REL="$v" -t "vpnlab:$v" "$HERE" >/dev/null \
        || { echo "образ $v не собрался"; exit 1; }
done
for v in $VERSIONS; do
    ( bash "$HERE/run_pair.sh" "$v" > "$L/run-$v.out" 2>&1
      bash "$HERE/stage2.sh" "$v" > "$L/stage2-$v.out" 2>&1 ) &
done
wait
for v in $VERSIONS; do
    echo "=================== $v"
    grep -v "systemd:" "$L/$v-summary.log"
done
echo
echo "Пары контейнеров оставлены для разбора: docker ps --filter name=vpnlab"
echo "Убрать: docker ps -aq --filter name=vpnlab | xargs -r docker rm -f -v"
