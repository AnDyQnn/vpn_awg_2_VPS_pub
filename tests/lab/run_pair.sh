#!/bin/bash
# Полный прогон установки RU + DE на одной версии Ubuntu.
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"
#   run_pair.sh 24.04 [ветка]
REL="$1"; BR="${2:-main}"
N="vpnlab-${REL//./}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
L="${LAB_LOGS:-$ROOT/tests/out/lab}"; mkdir -p "$L"
REPO="https://github.com/AnDyQnn/vpn_awg_2_VPS_pub.git"
D=/root/vpn_awg_2_VPS_pub
SRC="${SRC:-$ROOT}"
log() { echo "[$(date +%H:%M:%S)] $REL: $*" | tee -a "$L/$REL-summary.log"; }
: > "$L/$REL-summary.log"

docker rm -f -v "$N-ru" "$N-de" >/dev/null 2>&1
docker network rm "$N" >/dev/null 2>&1
docker network create "$N" >/dev/null
for R in ru de; do
  docker run -d --name "$N-$R" --hostname "lab-$R-${REL//./}" --network "$N" \
    --privileged --cgroupns=host -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
    --tmpfs /run --tmpfs /run/lock -v /var/lib/docker -v /var/lib/containerd \
    "vpnlab:$REL" >/dev/null || { log "контейнер $R не стартовал"; exit 1; }
done
for R in ru de; do
  for i in $(seq 1 60); do
    s=$(docker exec "$N-$R" systemctl is-system-running 2>/dev/null)
    case "$s" in running|degraded) break ;; esac; sleep 1
  done
  log "$R systemd: $s"
  docker exec "$N-$R" bash -c "git clone -q -b $BR $REPO $D" || { log "$R: git clone упал"; exit 1; }
  # Поверх клона — рабочий код с этой машины (то, что проверяем). Через
  # временный индекс git: там всё в LF, как у людей после git clone.
  ( cd "$SRC" && TI=$(mktemp) && cp .git/index "$TI" && GIT_INDEX_FILE="$TI" git add -A     && TREE=$(GIT_INDEX_FILE="$TI" git write-tree) && rm -f "$TI"     && git -c core.autocrlf=false -c core.eol=lf archive "$TREE" )     | docker exec -i "$N-$R" tar -xf - -C $D
done

# .env по README
docker exec "$N-ru" bash -c "cd $D/VPS_RU && cp .env.example .env && sed -i 's/^BOT_TOKEN=.*/BOT_TOKEN=123456789:AAlabFakeTokenForInstallTest_xxxxxxxxx/; s/^ADMIN_ID=.*/ADMIN_ID=111111/' .env"
docker exec "$N-de" bash -c "cd $D/VPS_DE && cp .env.example .env"

# Установка «как человек по SSH»: псевдотерминал, ответы на вопросы.
inst() {  # $1=ru|de $2=каталог $3=порт SSH $4=пароль архива
  local t0=$(date +%s) LOGF="$L/$REL-$1-install.log"
  docker exec "$N-$1" bash -c "rm -f /tmp/in; mkfifo /tmp/in"
  docker exec "$N-$1" bash -c "cd $D/$2 && exec 3<>/tmp/in; timeout 5400 script -qfec 'bash install.sh' /dev/null <&3" > "$LOGF" 2>&1 &
  local pid=$! port_sent= pass_sent= dlg=
  while kill -0 $pid 2>/dev/null; do
    if [ -z "$port_sent" ] && grep -q "Введите новый порт" "$LOGF" 2>/dev/null; then
      sleep 1; docker exec "$N-$1" bash -c "echo '$3' > /tmp/in"; port_sent=1
    fi
    if [ -n "$4" ] && [ -z "$pass_sent" ] && grep -q "Введите пароль" "$LOGF" 2>/dev/null; then
      sleep 1; docker exec "$N-$1" bash -c "echo '$4' > /tmp/in"; pass_sent=1
    fi
    # Любой полноэкранный диалог (needrestart, конфликт конфигов) — это зависание.
    if grep -qE "Daemons using outdated|Which services should be restarted|What do you want to do about modified configuration" "$LOGF" 2>/dev/null; then
      if [ -z "$dlg" ]; then log "$1: ДИАЛОГ apt — установка ждёт человека (жму Enter)"; dlg=1; fi
      docker exec "$N-$1" bash -c "echo > /tmp/in"; sleep 10
    fi
    sleep 3
  done
  wait $pid; local rc=$?
  log "$1 install.sh: код $rc, $(( $(date +%s) - t0 )) с"
}
inst ru VPS_RU 22222 labBackupPass1 &
inst de VPS_DE 22222 '' &
wait

# Ключ для Германии: адрес RU-контейнера вместо внешнего IP (в стенде иначе никак).
RU_IP=$(docker inspect -f "{{(index .NetworkSettings.Networks \"$N\").IPAddress}}" "$N-ru")
if docker exec "$N-ru" test -s $D/VPS_RU/DE_AGENT_CONFIG.txt; then
  docker exec "$N-ru" cat $D/VPS_RU/DE_AGENT_CONFIG.txt | sed -E "s#^Endpoint *=.*#Endpoint = $RU_IP:51820#" > "$L/$REL-de-wg0.conf"
  docker exec -i "$N-de" bash -c "cat > $D/VPS_DE/volumes/wireguard/wg0.conf" < "$L/$REL-de-wg0.conf"
  docker exec "$N-de" docker restart de_vpn_agent >/dev/null
  log "ключ для DE перенесён, жду рукопожатие"
  for i in $(seq 1 36); do
    hs=$(docker exec "$N-ru" docker exec vpn_wireguard sh -c 'wg show wg0 dump' 2>/dev/null | awk -F'\t' '$4 ~ /10\.13\.13\.254/{print $5}')
    [ -n "$hs" ] && [ "$hs" != 0 ] && break; sleep 5
  done
  log "рукопожатие RU-DE: ${hs:-нет}"
else
  log "DE_AGENT_CONFIG.txt НЕТ"
fi
sleep 20
for R in ru de; do
  docker exec "$N-$R" bash $D/scripts/check_network.sh > "$L/$REL-$R-check.log" 2>&1
  log "$R check_network: $(grep -E '^Итог' "$L/$REL-$R-check.log")"
done
log "ГОТОВО"
