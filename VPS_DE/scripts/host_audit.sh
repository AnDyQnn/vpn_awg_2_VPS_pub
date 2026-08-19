#!/bin/bash
# Аудит немецкой ноды (агент-выход). Расширенный, по образцу RU-аудита, но с прицелом
# на роль exit-ноды: принимает трафик от RU (пир 10.13.13.x) и выпускает его в мир (NAT).

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLAG_DIR="$APP_DIR/volumes/flags"
REPORT_FILE="$FLAG_DIR/audit_report.json"
STATUS_FILE="$FLAG_DIR/audit_status"

mkdir -p "$FLAG_DIR"
rm -f "$REPORT_FILE"

clean() {
    local text="$1"
    text="${text//$'\n'/ }"
    text="${text//$'\r'/}"
    text="${text//$'\t'/ }"
    text="${text//\\/\\\\}"
    text="${text//\"/\\\"}"
    text=$(printf "%s" "$text" | tr -d '\000-\037')
    printf "%s" "$text"
}

CAT_NET=""
CAT_HOST=""
CAT_DOCKER=""
CAT_VPN=""
CAT_STORAGE=""
CAT_SEC=""

add_check() {
    local cat_var=$1
    local name=$(clean "$2")
    local status=$(clean "$3")
    local msg=$(clean "$4")
    local json_str="{\"name\":\"$name\",\"status\":\"$status\",\"msg\":\"$msg\"},"
    printf -v "$cat_var" "%s" "${!cat_var}${json_str}"
}

CONT="de_vpn_agent"

# ---------------- СЕТЬ ----------------
echo "network" > "$STATUS_FILE"

ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_NET "Ping Google DNS (8.8.8.8)" "ok" "Доступно" || add_check CAT_NET "Ping Google DNS (8.8.8.8)" "error" "Таймаут"

ping -c 1 -W 2 google.com >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_NET "DNS разрешение имён" "ok" "Работает" || add_check CAT_NET "DNS разрешение имён" "error" "Сбой DNS"

FWD=$(sysctl -n net.ipv4.ip_forward 2>/dev/null || echo "0")
[ "$FWD" = "1" ] && add_check CAT_NET "IPv4 Forwarding (выход трафика)" "ok" "Включено" || add_check CAT_NET "IPv4 Forwarding (выход трафика)" "error" "Выключено (клиенты без интернета!)"

GW=$(ip route show default | awk '{print $3}' | head -n 1)
[ -n "$GW" ] && add_check CAT_NET "Шлюз по умолчанию" "ok" "$GW" || add_check CAT_NET "Шлюз по умолчанию" "error" "Не найден"

DEF_IFACE=$(ip route show default | awk '{print $5}' | head -n 1)
MTU=$(cat /sys/class/net/$DEF_IFACE/mtu 2>/dev/null)
[ -n "$MTU" ] && add_check CAT_NET "MTU внешнего интерфейса ($DEF_IFACE)" "ok" "$MTU" || add_check CAT_NET "MTU внешнего интерфейса" "warning" "Не определён"

curl -s -m 4 -o /dev/null https://mirror.yandex.ru 2>/dev/null
[ $? -eq 0 ] && add_check CAT_NET "Зеркало пакетов (mirror.yandex.ru)" "ok" "Доступно" || add_check CAT_NET "Зеркало пакетов (mirror.yandex.ru)" "warning" "Недоступно"

# conntrack: для exit-ноды критично (весь клиентский трафик через NAT). Переполнение = обрывы.
CT_COUNT=$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null)
CT_MAX=$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null)
if [ -n "$CT_COUNT" ] && [ -n "$CT_MAX" ] && [ "${CT_MAX:-0}" -gt 0 ]; then
    CT_PCT=$(( CT_COUNT * 100 / CT_MAX ))
    [ "$CT_PCT" -lt 80 ] && add_check CAT_NET "Таблица соединений (conntrack)" "ok" "${CT_COUNT}/${CT_MAX} (${CT_PCT}%)" || add_check CAT_NET "Таблица соединений (conntrack)" "warning" "Заполнена ${CT_PCT}% — риск обрывов"
fi
sleep 1

# ---------------- ХОСТ ----------------
echo "host" > "$STATUS_FILE"

CPU_IDLE=$(vmstat 1 2 | tail -1 | awk '{print $15}')
CPU_USE=$(( 100 - ${CPU_IDLE:-0} ))
[ "$CPU_USE" -lt 90 ] && add_check CAT_HOST "Загрузка CPU" "ok" "${CPU_USE}%" || add_check CAT_HOST "Загрузка CPU" "warning" "Высокая: ${CPU_USE}%"

LOAD=$(awk '{print $1}' /proc/loadavg)
add_check CAT_HOST "Load Average (1m)" "ok" "$LOAD"

RAM_USE=$(free -m | awk 'NR==2{if($2>0) printf "%d", $3*100/$2; else print "0"}')
[ "${RAM_USE:-0}" -lt 95 ] && add_check CAT_HOST "Оперативная память (RAM)" "ok" "${RAM_USE:-0}% занято" || add_check CAT_HOST "Оперативная память (RAM)" "error" "Критично: ${RAM_USE:-0}%"

SWAP=$(free -m | awk 'NR==3{if($2>0) printf "%d", $3*100/$2; else print "0"}')
add_check CAT_HOST "Файл подкачки (Swap)" "ok" "${SWAP:-0}% занято"

UPTIME=$(awk '{print int($1/86400)"d "int(($1%86400)/3600)"h"}' /proc/uptime)
add_check CAT_HOST "Аптайм сервера" "ok" "$UPTIME"

TIMEDATE=$(timedatectl show 2>/dev/null | grep NTPSynchronized | cut -d= -f2)
[ "$TIMEDATE" = "yes" ] && add_check CAT_HOST "Синхронизация времени (NTP)" "ok" "Включена" || add_check CAT_HOST "Синхронизация времени (NTP)" "warning" "Не синхронизировано"

KERNEL=$(uname -r)
add_check CAT_HOST "Версия ядра Linux" "ok" "$KERNEL"

CORES=$(nproc 2>/dev/null || echo "?")
add_check CAT_HOST "Ядер CPU" "ok" "$CORES"

RAM_TOTAL=$(free -m | awk 'NR==2{print $2}')
add_check CAT_HOST "Всего RAM" "ok" "${RAM_TOTAL:-?} MB"

OOM=$(dmesg 2>/dev/null | grep -i "killed process" | wc -l)
[ "$OOM" -eq 0 ] && add_check CAT_HOST "OOM Killer (нехватка памяти)" "ok" "Не зафиксировано" || add_check CAT_HOST "OOM Killer (нехватка памяти)" "warning" "Были случаи"
sleep 1

# ---------------- DOCKER ----------------
echo "docker" > "$STATUS_FILE"

systemctl is-active --quiet docker
[ $? -eq 0 ] && add_check CAT_DOCKER "Служба Docker Daemon" "ok" "Active" || add_check CAT_DOCKER "Служба Docker Daemon" "error" "Остановлен"

STAT=$(docker inspect -f '{{.State.Status}}' "$CONT" 2>/dev/null || echo "missing")
[ "$STAT" = "running" ] && add_check CAT_DOCKER "Контейнер $CONT" "ok" "Running" || add_check CAT_DOCKER "Контейнер $CONT" "error" "$STAT"

RESTARTS=$(docker inspect -f '{{.RestartCount}}' "$CONT" 2>/dev/null || echo "?")
[ "${RESTARTS:-0}" -le 3 ] 2>/dev/null && add_check CAT_DOCKER "Перезапуски контейнера" "ok" "${RESTARTS}" || add_check CAT_DOCKER "Перезапуски контейнера" "warning" "Часто: ${RESTARTS} (нестабильность)"

EXITED=$(docker ps -aq -f status=exited | wc -l)
[ "$EXITED" -eq 0 ] && add_check CAT_DOCKER "Остановленные контейнеры" "ok" "0" || add_check CAT_DOCKER "Остановленные контейнеры" "warning" "$EXITED шт. (тратят место)"

D_SPACE=$(docker system df --format '{{.Size}}' | head -n 1)
add_check CAT_DOCKER "Объём данных Docker" "ok" "${D_SPACE:-?}"

IMG_COUNT=$(docker images -q 2>/dev/null | wc -l)
[ "${IMG_COUNT:-0}" -le 10 ] && add_check CAT_DOCKER "Docker-образов" "ok" "${IMG_COUNT} шт." || add_check CAT_DOCKER "Docker-образов" "warning" "${IMG_COUNT} шт. (prune)"

DE_ERR=$(docker logs --tail 150 "$CONT" 2>&1 | grep -iE "error|fatal|exception|traceback" | grep -viE "CancelledError" | tail -n 1)
if [ -n "$DE_ERR" ]; then
    add_check CAT_DOCKER "Логи агента" "warning" "$(clean "${DE_ERR:0:80}")"
else
    add_check CAT_DOCKER "Логи агента" "ok" "Чисто"
fi
sleep 1

# ---------------- VPN (exit-нода) ----------------
echo "vpn" > "$STATUS_FILE"

docker exec "$CONT" ip link show wg0 >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_VPN "Интерфейс wg0" "ok" "Поднят" || add_check CAT_VPN "Интерфейс wg0" "error" "Упал"

WG_IP=$(docker exec "$CONT" ip -4 addr show wg0 2>/dev/null | grep -oP 'inet \K[\d.]+')
[ -n "$WG_IP" ] && add_check CAT_VPN "IP туннеля wg0" "ok" "$WG_IP" || add_check CAT_VPN "IP туннеля wg0" "error" "Не назначен"

WG_MTU=$(docker exec "$CONT" cat /sys/class/net/wg0/mtu 2>/dev/null)
[ -n "$WG_MTU" ] && add_check CAT_VPN "MTU туннеля wg0" "ok" "${WG_MTU}" || add_check CAT_VPN "MTU туннеля wg0" "warning" "Неизвестно"

MASQ=$(docker exec "$CONT" iptables -t nat -S 2>/dev/null | grep MASQUERADE)
[ -n "$MASQ" ] && add_check CAT_VPN "NAT Masquerade (выход в мир)" "ok" "Настроено" || add_check CAT_VPN "NAT Masquerade (выход в мир)" "error" "Отсутствует (нет выхода!)"

MSS=$(docker exec "$CONT" iptables -t mangle -S 2>/dev/null | grep -i "TCPMSS")
[ -n "$MSS" ] && add_check CAT_VPN "MSS-clamping (анти-тормоза)" "ok" "Активно" || add_check CAT_VPN "MSS-clamping (анти-тормоза)" "warning" "Не найдено"

WG_DUMP=$(docker exec "$CONT" wg show wg0 dump 2>/dev/null | wc -l)
[ "${WG_DUMP:-0}" -ge 1 ] && add_check CAT_VPN "Ответ ядра WireGuard" "ok" "Успешно" || add_check CAT_VPN "Ответ ядра WireGuard" "error" "Ядро не отвечает"

RP=$(docker exec "$CONT" sysctl -n net.ipv4.conf.all.rp_filter 2>/dev/null)
[ "$RP" = "0" ] && add_check CAT_VPN "rp_filter (асимм. маршрутизация)" "ok" "0 (верно)" || add_check CAT_VPN "rp_filter (асимм. маршрутизация)" "warning" "${RP:-?} — должно быть 0"

PEERS_TOTAL=$(docker exec "$CONT" wg show wg0 peers 2>/dev/null | grep -c .)
add_check CAT_VPN "Пиры WireGuard" "ok" "Всего: ${PEERS_TOTAL:-0} (ожидается 1 — мастер RU)"

# Свежесть хэндшейка с RU (мастер — единственный пир exit-ноды)
DE_HS=$(docker exec "$CONT" wg show wg0 latest-handshakes 2>/dev/null | awk '{if($2>m)m=$2} END{print m+0}')
if [ "${DE_HS:-0}" -gt 0 ]; then
    HS_AGE=$(( $(date +%s) - DE_HS ))
    [ "$HS_AGE" -lt 180 ] && add_check CAT_VPN "Хэндшейк с RU (мастер)" "ok" "Свежий (${HS_AGE}s назад)" || add_check CAT_VPN "Хэндшейк с RU (мастер)" "warning" "Устарел (${HS_AGE}s) — RU молчит?"
else
    add_check CAT_VPN "Хэндшейк с RU (мастер)" "warning" "Нет свежих хэндшейков"
fi

TUN=$(ls /dev/net/tun 2>/dev/null)
[ -n "$TUN" ] && add_check CAT_VPN "Модуль TUN/TAP" "ok" "Доступен" || add_check CAT_VPN "Модуль TUN/TAP" "error" "Не найден"
sleep 1

# ---------------- ХРАНИЛИЩЕ ----------------
echo "storage" > "$STATUS_FILE"

ROOT_DISK=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
[ "${ROOT_DISK:-0}" -lt 95 ] && add_check CAT_STORAGE "Свободное место на диске (/)" "ok" "${ROOT_DISK:-0}% занято" || add_check CAT_STORAGE "Свободное место на диске (/)" "error" "Критично: ${ROOT_DISK:-0}%"

touch /tmp/de_audit_rw 2>/dev/null && rm -f /tmp/de_audit_rw 2>/dev/null
[ $? -eq 0 ] && add_check CAT_STORAGE "Права записи на диск" "ok" "Доступно (R/W)" || add_check CAT_STORAGE "Права записи на диск" "error" "Read-Only!"

ENV_PERM=$(stat -c "%a" "$APP_DIR/.env" 2>/dev/null)
[ -z "$ENV_PERM" ] && ENV_PERM="none"
if [ "$ENV_PERM" = "600" ] || [ "$ENV_PERM" = "640" ]; then
    add_check CAT_STORAGE "Права доступа к .env" "ok" "Безопасные ($ENV_PERM)"
else
    add_check CAT_STORAGE "Права доступа к .env" "warning" "Открыты: $ENV_PERM (рекомендуется 600)"
fi
sleep 1

# ---------------- БЕЗОПАСНОСТЬ ----------------
echo "security" > "$STATUS_FILE"

ROOT_SSH=$(grep "^PermitRootLogin yes" /etc/ssh/sshd_config 2>/dev/null)
[ -n "$ROOT_SSH" ] && add_check CAT_SEC "SSH Root Login" "warning" "Разрешён (рекомендуется отключить)" || add_check CAT_SEC "SSH Root Login" "ok" "Защищён"

UFW_STAT=$(ufw status 2>/dev/null | grep -i "active")
IPT_STAT=$(iptables -L -n 2>/dev/null | grep "Chain INPUT" | wc -l)
if [ -n "$UFW_STAT" ]; then
    add_check CAT_SEC "Межсетевой экран" "ok" "UFW активен"
elif [ "$IPT_STAT" -gt 0 ]; then
    add_check CAT_SEC "Межсетевой экран" "ok" "Iptables настроен"
else
    add_check CAT_SEC "Межсетевой экран" "warning" "Не обнаружен"
fi

F2B=$(systemctl is-active fail2ban 2>/dev/null)
[ "$F2B" = "active" ] && add_check CAT_SEC "Служба Fail2Ban" "ok" "Защищает от брутфорса" || add_check CAT_SEC "Служба Fail2Ban" "warning" "Не установлена"

# ---------------- JSON ----------------
CAT_NET="[${CAT_NET%,}]"
CAT_HOST="[${CAT_HOST%,}]"
CAT_DOCKER="[${CAT_DOCKER%,}]"
CAT_VPN="[${CAT_VPN%,}]"
CAT_STORAGE="[${CAT_STORAGE%,}]"
CAT_SEC="[${CAT_SEC%,}]"

cat <<EOF > "$REPORT_FILE"
{
  "network": $CAT_NET,
  "host": $CAT_HOST,
  "docker": $CAT_DOCKER,
  "vpn": $CAT_VPN,
  "storage": $CAT_STORAGE,
  "security": $CAT_SEC
}
EOF

echo "done" > "$STATUS_FILE"
