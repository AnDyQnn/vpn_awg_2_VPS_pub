#!/bin/bash
# Второй этап: всё, что идёт после установки, на той же паре узлов.
#   stage2.sh 24.04
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"
REL="$1"; N="vpnlab-${REL//./}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
L="${LAB_LOGS:-$ROOT/tests/out/lab}"; mkdir -p "$L"
D=/root/vpn_awg_2_VPS_pub
log() { echo "[$(date +%H:%M:%S)] $REL: $*" | tee -a "$L/$REL-summary.log"; }
X() { docker exec "$N-$1" bash -c "$2"; }

# 1. Службы хоста на месте и живы
for R in ru de; do
  U=vpn-updater; [ $R = de ] && U=de-agent-updater
  st=$(X $R "for u in $U vpn-watchdog docker fail2ban ssh; do printf '%s=%s ' \$u \$(systemctl is-active \$u); done; for t in vpn-cleanup.timer vpn-security-upgrade.timer apt-daily.timer; do printf '%s=%s ' \$t \$(systemctl is-active \$t); done")
  log "$R службы: $st"
  wd=$(X $R "systemctl show vpn-watchdog -p Environment --value")
  log "$R сторож: $wd"
  X $R "tail -3 $D/VPS_${R^^}/volumes/flags/watchdog.log 2>/dev/null" > "$L/$REL-$R-watchdog.log" 2>&1
done

# 2. Аудит хоста — JSON должен разбираться
X ru "rm -f $D/VPS_RU/volumes/flags/host_audit*.json; touch $D/VPS_RU/volumes/flags/do_audit"
for i in $(seq 1 60); do X ru "ls $D/VPS_RU/volumes/flags/ | grep -q audit.*json" && break; sleep 3; done
A=$(X ru "ls $D/VPS_RU/volumes/flags/ | grep -i audit")
J=$(X ru "f=\$(ls -t $D/VPS_RU/volumes/flags/*audit*.json 2>/dev/null | head -1); [ -n \"\$f\" ] && python3 -c \"import json,sys; d=json.load(open(sys.argv[1])); print('JSON ок, ключей', len(d))\" \"\$f\" 2>&1 || echo нет файла")
log "аудит RU: $A | $J"

# 3. Проверка хоста, уборка (вхолостую), сверка
for R in ru de; do
  ND=$D/VPS_${R^^}
  h=$(X $R "bash $D/scripts/host_health.sh $ND >/dev/null 2>&1; python3 -c \"import json; d=json.load(open('$ND/volumes/flags/host_health.json')); print('host_health JSON ок')\" 2>&1 | tail -1")
  g=$(X $R "bash $D/scripts/gc.sh --dry-run 2>&1 | tail -1")
  c=$(X $R "bash $D/scripts/contract_check.sh $ND 2>&1 | tail -2 | tr '\n' ' '")
  log "$R: $h | gc: $g | сверка: $c"
done

# 4. Обновление «как по кнопке»: метка do_update → демон → deploy.sh
for R in ru de; do
  ND=$D/VPS_${R^^}
  X $R "touch $ND/volumes/flags/do_update"
done
sleep 20
for R in ru de; do
  for i in $(seq 1 120); do
    X $R "systemctl is-active --quiet vpn-deploy" || break; sleep 10
  done
  X $R "journalctl -u vpn-deploy --no-pager -o cat" > "$L/$REL-$R-deploy.log" 2>&1
  res=$(grep -E "Обновление успешно завершено|ОТКАТ|Сборка не удалась|Новая версия нездорова" "$L/$REL-$R-deploy.log" | tail -2 | tr '\n' ' ')
  log "$R деплой: ${res:-нет итога (см. $REL-$R-deploy.log)}"
done

# 5. Сторож вживую: Германия легла
X de "docker stop de_vpn_agent >/dev/null"
log "DE остановлен, жду 6 мин"
sleep 360
X ru "tail -8 $D/VPS_RU/volumes/flags/watchdog.log" > "$L/$REL-ru-watchdog-de-down.log" 2>&1
X ru "docker inspect -f '{{.RestartCount}} {{.State.StartedAt}}' vpn_wireguard; systemctl show docker -p NRestarts --value; cat $D/VPS_RU/volumes/flags/watchdog.last_reboot 2>/dev/null || echo 'перезагрузок нет'" >> "$L/$REL-ru-watchdog-de-down.log" 2>&1
log "сторож RU при лежащей DE: $(grep -cE 'L3|L4' "$L/$REL-ru-watchdog-de-down.log") строк L3/L4"
X de "docker start de_vpn_agent >/dev/null"

# 6. Перезагрузка обоих серверов: всё должно подняться само
sleep 60
docker restart "$N-ru" "$N-de" >/dev/null
log "серверы перезагружены, жду 3 мин"
sleep 180
for R in ru de; do
  U=vpn-updater; [ $R = de ] && U=de-agent-updater
  st=$(X $R "for u in $U vpn-watchdog docker ssh; do printf '%s=%s ' \$u \$(systemctl is-active \$u); done; sshd -T 2>/dev/null | awk '/^port /{printf \"ssh-port=%s \", \$2}'; docker ps --format '{{.Names}}:{{.Status}}' | tr '\n' ' '")
  log "$R после перезагрузки: $st"
  X $R "bash $D/scripts/check_network.sh" > "$L/$REL-$R-check-after-reboot.log" 2>&1
  log "$R check_network после перезагрузки: $(grep -E '^Итог' "$L/$REL-$R-check-after-reboot.log")"
done

# 7. Повторный запуск установщика RU: Enter на вопросе о порте
LOGF="$L/$REL-ru-reinstall.log"
X ru "psql_n() { docker exec vpn_db sh -c 'psql -U \$POSTGRES_USER -d \$POSTGRES_DB -tAc \"select count(*) from users\"'; }; psql_n" > "$L/$REL-users-before" 2>&1
X ru "rm -f /tmp/in; mkfifo /tmp/in"
docker exec "$N-ru" bash -c "cd $D/VPS_RU && exec 3<>/tmp/in; timeout 3600 script -qfec 'bash install.sh' /dev/null <&3" > "$LOGF" 2>&1 &
pid=$!; sent=
while kill -0 $pid 2>/dev/null; do
  if [ -z "$sent" ] && grep -q "Введите новый порт" "$LOGF"; then sleep 1; X ru "echo > /tmp/in"; sent=1; fi
  sleep 3
done
wait $pid; rc=$?
ub=$(cat "$L/$REL-users-before"); ua=$(X ru "docker exec vpn_db sh -c 'psql -U \$POSTGRES_USER -d \$POSTGRES_DB -tAc \"select count(*) from users\"'" 2>&1)
port=$(X ru "sshd -T 2>/dev/null | awk '/^port /{print \$2; exit}'")
log "повторная установка RU: код $rc, людей в базе до/после: $ub/$ua, SSH-порт: $port, $(tr -d '\r' < "$LOGF" | grep -oE 'ЗАВЕРШЕНА|НЕ СОБРАЛИСЬ|БАЗА ДАННЫХ НЕ ПОДНЯЛАСЬ|Пароль записан|Пароль не задан' | sort -u | tr '\n' ' ')"
log "ЭТАП 2 ГОТОВ"

# 8. fail2ban: 8 неудачных входов с DE → бан → настоящий порт SSH закрыт
RU_IP=$(docker inspect -f "{{(index .NetworkSettings.Networks \"$N\").IPAddress}}" "$N-ru")
docker exec "$N-de" bash -c "for i in \$(seq 8); do timeout 5 ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=3 -p 22222 f\$i@$RU_IP true 2>/dev/null; done"
sleep 5
f2b=$(X ru "systemctl is-active fail2ban; grep -h '^port' /etc/fail2ban/jail.d/zz-vpn-sshd.local 2>/dev/null")
closed=$(docker exec "$N-de" bash -c "timeout 4 bash -c '</dev/tcp/$RU_IP/22222' 2>/dev/null && echo ОТКРЫТ || echo закрыт")
log "fail2ban RU: $(echo $f2b) | 22222 для забаненного: $closed"
log "ФИНАЛ"
