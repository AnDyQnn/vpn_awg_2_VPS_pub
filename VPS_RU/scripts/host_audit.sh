#!/bin/bash

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLAG_DIR="$APP_DIR/volumes/flags"
REPORT_FILE="$FLAG_DIR/audit_report.json"
STATUS_FILE="$FLAG_DIR/audit_status"

mkdir -p "$FLAG_DIR"
rm -f "$REPORT_FILE"

# Надежная очистка текста для JSON
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
CAT_LOGS=""

add_check() {
    local cat_var=$1
    local name=$(clean "$2")
    local status=$(clean "$3")
    local msg=$(clean "$4")
    local json_str="{\"name\":\"$name\",\"status\":\"$status\",\"msg\":\"$msg\"},"
    printf -v "$cat_var" "%s" "${!cat_var}${json_str}"
}

echo "network" > "$STATUS_FILE"

ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_NET "Ping Google DNS (8.8.8.8)" "ok" "Доступно" || add_check CAT_NET "Ping Google DNS (8.8.8.8)" "error" "Таймаут"

ping -c 1 -W 2 1.1.1.1 >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_NET "Ping Cloudflare (1.1.1.1)" "ok" "Доступно" || add_check CAT_NET "Ping Cloudflare (1.1.1.1)" "warning" "Таймаут"

ping -c 1 -W 2 google.com >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_NET "DNS Разрешение имен" "ok" "Работает" || add_check CAT_NET "DNS Разрешение имен" "error" "Сбой DNS"

# ИСПРАВЛЕНО: Telegram заблокирован в РФ - это норма, ставим warning вместо error
curl -s -m 3 https://api.telegram.org >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_NET "Доступность Telegram API" "ok" "Связь есть" || add_check CAT_NET "Доступность Telegram API" "warning" "Заблокировано (Норма для РФ)"

curl -s -m 3 https://github.com >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_NET "Доступность GitHub" "ok" "Связь есть" || add_check CAT_NET "Доступность GitHub" "warning" "Недоступен"

# RU-дружественная проба (ТСПУ иногда режет 8.8.8.8/1.1.1.1, поэтому проверяем и RU-цель)
ping -c 1 -W 2 77.88.8.8 >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_NET "Ping Yandex DNS (77.88.8.8)" "ok" "Доступно" || add_check CAT_NET "Ping Yandex DNS (77.88.8.8)" "warning" "Таймаут"

# Резервные зеркала пакетов (заранее видим, если ТСПУ/провайдер их режет — сборка бы упала)
curl -s -m 4 -o /dev/null https://mirror.yandex.ru 2>/dev/null
[ $? -eq 0 ] && add_check CAT_NET "Зеркало пакетов (mirror.yandex.ru)" "ok" "Доступно" || add_check CAT_NET "Зеркало пакетов (mirror.yandex.ru)" "warning" "Недоступно"

curl -s -m 4 -o /dev/null https://raw.githubusercontent.com 2>/dev/null
[ $? -eq 0 ] && add_check CAT_NET "Зеркало списков (raw.githubusercontent)" "ok" "Доступно" || add_check CAT_NET "Зеркало списков (raw.githubusercontent)" "warning" "Недоступно"

FWD=$(sysctl -n net.ipv4.ip_forward 2>/dev/null || echo "0")
[ "$FWD" = "1" ] && add_check CAT_NET "IPv4 Forwarding (Маршрутизация)" "ok" "Включено" || add_check CAT_NET "IPv4 Forwarding (Маршрутизация)" "error" "Выключено"

GW=$(ip route show default | awk '{print $3}' | head -n 1)
[ -n "$GW" ] && add_check CAT_NET "Шлюз по умолчанию" "ok" "$GW" || add_check CAT_NET "Шлюз по умолчанию" "error" "Не найден"

TCP_CONN=$(ss -s 2>/dev/null | grep TCP: | grep -oP 'estab \K\d+')
[ -z "$TCP_CONN" ] && TCP_CONN=0
[ "$TCP_CONN" -lt 1000 ] && add_check CAT_NET "Активные TCP сессии" "ok" "$TCP_CONN" || add_check CAT_NET "Активные TCP сессии" "warning" "Высокая нагрузка: $TCP_CONN"

# conntrack: таблица отслеживания соединений NAT. Для VPN-шлюза критично — при переполнении
# новые соединения молча дропаются («интернет пропал» у части клиентов).
CT_COUNT=$(cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null)
CT_MAX=$(cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null)
if [ -n "$CT_COUNT" ] && [ -n "$CT_MAX" ] && [ "${CT_MAX:-0}" -gt 0 ]; then
    CT_PCT=$(( CT_COUNT * 100 / CT_MAX ))
    [ "$CT_PCT" -lt 80 ] && add_check CAT_NET "Таблица соединений (conntrack)" "ok" "${CT_COUNT}/${CT_MAX} (${CT_PCT}%)" || add_check CAT_NET "Таблица соединений (conntrack)" "warning" "Заполнена ${CT_PCT}% — риск обрыва новых соединений"
fi

DEF_IFACE=$(ip route show default | awk '{print $5}' | head -n 1)
MTU=$(cat /sys/class/net/$DEF_IFACE/mtu 2>/dev/null)
[ -n "$MTU" ] && add_check CAT_NET "MTU внешнего интерфейса ($DEF_IFACE)" "ok" "$MTU" || add_check CAT_NET "MTU внешнего интерфейса" "warning" "Не определен"

sleep 1

echo "host" > "$STATUS_FILE"

CPU_IDLE=$(vmstat 1 2 | tail -1 | awk '{print $15}')
CPU_USE=$(( 100 - ${CPU_IDLE:-0} ))
[ "$CPU_USE" -lt 90 ] && add_check CAT_HOST "Загрузка CPU" "ok" "${CPU_USE}%" || add_check CAT_HOST "Загрузка CPU" "warning" "Высокая: ${CPU_USE}%"

IO_WAIT=$(vmstat 1 2 | tail -1 | awk '{print $16}')
[ "${IO_WAIT:-0}" -lt 15 ] && add_check CAT_HOST "Дисковый I/O Wait" "ok" "${IO_WAIT:-0}%" || add_check CAT_HOST "Дисковый I/O Wait" "warning" "${IO_WAIT:-0}% (Медленный диск)"

LOAD=$(awk '{print $1}' /proc/loadavg)
add_check CAT_HOST "Load Average (1m)" "ok" "$LOAD"

RAM_USE=$(free -m | awk 'NR==2{if($2>0) printf "%d", $3*100/$2; else print "0"}')
[ -z "$RAM_USE" ] && RAM_USE=0
[ "$RAM_USE" -lt 95 ] && add_check CAT_HOST "Оперативная память (RAM)" "ok" "${RAM_USE}% занято" || add_check CAT_HOST "Оперативная память (RAM)" "error" "Критично: ${RAM_USE}%"

SWAP=$(free -m | awk 'NR==3{if($2>0) printf "%d", $3*100/$2; else print "0"}')
[ -z "$SWAP" ] && SWAP=0
add_check CAT_HOST "Файл подкачки (Swap)" "ok" "${SWAP}% занято"

FD_TOTAL=$(cat /proc/sys/fs/file-nr 2>/dev/null | awk '{print $1}')
add_check CAT_HOST "Открытые файловые дескрипторы" "ok" "$FD_TOTAL"

ZOMBIES=$(ps aux | awk '$8 ~ /Z/ {count++} END {print count+0}')
[ "$ZOMBIES" -eq 0 ] && add_check CAT_HOST "Зомби-процессы" "ok" "0" || add_check CAT_HOST "Зомби-процессы" "warning" "Найдено: $ZOMBIES"

UPTIME=$(awk '{print int($1/86400)"d "int(($1%86400)/3600)"h"}' /proc/uptime)
add_check CAT_HOST "Аптайм сервера" "ok" "$UPTIME"

TIMEDATE=$(timedatectl show 2>/dev/null | grep NTPSynchronized | cut -d= -f2)
[ "$TIMEDATE" = "yes" ] && add_check CAT_HOST "Синхронизация времени (NTP)" "ok" "Включена" || add_check CAT_HOST "Синхронизация времени (NTP)" "warning" "Не синхронизировано"

KERNEL=$(uname -r)
add_check CAT_HOST "Версия Ядра Linux" "ok" "$KERNEL"

CORES=$(nproc 2>/dev/null || echo "?")
add_check CAT_HOST "Ядер CPU" "ok" "$CORES"

RAM_TOTAL=$(free -m | awk 'NR==2{print $2}')
add_check CAT_HOST "Всего RAM" "ok" "${RAM_TOTAL:-?} MB"

sleep 1

echo "docker" > "$STATUS_FILE"

systemctl is-active --quiet docker
[ $? -eq 0 ] && add_check CAT_DOCKER "Служба Docker Daemon" "ok" "Active" || add_check CAT_DOCKER "Служба Docker Daemon" "error" "Остановлен"

docker compose version >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_DOCKER "Плагин Docker Compose" "ok" "Установлен" || add_check CAT_DOCKER "Плагин Docker Compose" "error" "Не найден"

check_cont() {
    local stat=$(docker inspect -f '{{.State.Status}}' "$1" 2>/dev/null || echo "missing")
    [ "$stat" = "running" ] && add_check CAT_DOCKER "Контейнер $1" "ok" "Running" || add_check CAT_DOCKER "Контейнер $1" "error" "$stat"
}

check_cont "vpn_bot"
check_cont "vpn_wireguard"
check_cont "vpn_db"

NET_EXISTS=$(docker network ls | grep vpn)
[ -n "$NET_EXISTS" ] && add_check CAT_DOCKER "Изолированная сеть Docker" "ok" "Существует" || add_check CAT_DOCKER "Изолированная сеть Docker" "error" "Не найдена"

D_SPACE=$(docker system df --format '{{.Size}}' | head -n 1)
add_check CAT_DOCKER "Объем данных Docker" "ok" "$D_SPACE"

IMG_COUNT=$(docker images -q 2>/dev/null | wc -l)
[ "${IMG_COUNT:-0}" -le 12 ] && add_check CAT_DOCKER "Docker-образов" "ok" "${IMG_COUNT} шт." || add_check CAT_DOCKER "Docker-образов" "warning" "${IMG_COUNT} шт. (лишние тратят диск — prune)"

EXITED=$(docker ps -aq -f status=exited | wc -l)
[ "$EXITED" -eq 0 ] && add_check CAT_DOCKER "Остановленные контейнеры" "ok" "0" || add_check CAT_DOCKER "Остановленные контейнеры" "warning" "$EXITED шт. (Тратят место)"

API_PORT=$(ss -tuln 2>/dev/null | grep -q ":8000 "; echo $?)
[ $API_PORT -ne 0 ] && add_check CAT_DOCKER "Порты внутри моста (API)" "ok" "Закрыты снаружи" || add_check CAT_DOCKER "Порты внутри моста (API)" "warning" "Торчат наружу!"

sleep 1

echo "vpn" > "$STATUS_FILE"

WG_PORT=$(ss -uln 2>/dev/null | grep ":51820")
[ -n "$WG_PORT" ] && add_check CAT_VPN "Прослушивание UDP 51820" "ok" "Открыт" || add_check CAT_VPN "Прослушивание UDP 51820" "error" "Порт закрыт/Не слушается"

docker exec vpn_wireguard ip link show wg0 >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_VPN "Сетевой интерфейс wg0" "ok" "Поднят" || add_check CAT_VPN "Сетевой интерфейс wg0" "error" "Не найден в контейнере"

WG_IP=$(docker exec vpn_wireguard ip -4 addr show wg0 2>/dev/null | grep -oP 'inet \K[\d.]+')
[ -n "$WG_IP" ] && add_check CAT_VPN "IP-адрес ядра VPN" "ok" "$WG_IP" || add_check CAT_VPN "IP-адрес ядра VPN" "error" "Не назначен"

WG_MTU=$(docker exec vpn_wireguard cat /sys/class/net/wg0/mtu 2>/dev/null)
[ "$WG_MTU" = "1280" ] && add_check CAT_VPN "MTU туннеля wg0" "ok" "1280 (Оптимально)" || add_check CAT_VPN "MTU туннеля wg0" "warning" "Текущий: ${WG_MTU:-unknown}"

CONF_FILE="/volumes/wireguard/wg0.conf"
[ -f "$APP_DIR$CONF_FILE" ] && add_check CAT_VPN "Конфиг wg0.conf" "ok" "Существует" || add_check CAT_VPN "Конфиг wg0.conf" "error" "Отсутствует"

[ -f "$APP_DIR/volumes/wireguard/public.key" ] && add_check CAT_VPN "Ключи шифрования (Server)" "ok" "Существуют" || add_check CAT_VPN "Ключи шифрования (Server)" "error" "Отсутствуют"

OBFUSCATION=$(grep -E "Jc|Jmin|Jmax" "$APP_DIR$CONF_FILE" 2>/dev/null)
[ -n "$OBFUSCATION" ] && add_check CAT_VPN "Обфускация AmneziaWG" "ok" "Активна (Анти-DPI)" || add_check CAT_VPN "Обфускация AmneziaWG" "warning" "Параметры не найдены"

MASQ=$(docker exec vpn_wireguard iptables -t nat -S 2>/dev/null | grep MASQUERADE)
[ -n "$MASQ" ] && add_check CAT_VPN "NAT Masquerade (Трафик)" "ok" "Настроено" || add_check CAT_VPN "NAT Masquerade (Трафик)" "error" "Отсутствует"

# --- ГИБРИДНАЯ МАРШРУТИЗАЦИЯ И DE-FAILOVER (ядро обхода) ---
FWMARK_RULE=$(docker exec vpn_wireguard sh -c 'ip rule show 2>/dev/null | grep -i "fwmark 0xc8"')
[ -n "$FWMARK_RULE" ] && add_check CAT_VPN "Правило fwmark→table 200 (обход)" "ok" "На месте" || add_check CAT_VPN "Правило fwmark→table 200 (обход)" "error" "Отсутствует"

DE_ROUTE=$(docker exec vpn_wireguard ip route show table 200 2>/dev/null | grep '^default')
if echo "$DE_ROUTE" | grep -q "dev wg0"; then
    add_check CAT_VPN "Маршрут мир/РКН → Германия" "ok" "Через DE (норма)"
elif [ -n "$DE_ROUTE" ]; then
    add_check CAT_VPN "Маршрут мир/РКН → Германия" "warning" "FALLBACK: напрямую через RU (DE недоступен)"
else
    add_check CAT_VPN "Маршрут мир/РКН → Германия" "error" "table 200 пуста"
fi

RU_SET=$(docker exec vpn_wireguard ipset list ru_nets 2>/dev/null | grep -cE '^[0-9]+\.')
[ "${RU_SET:-0}" -ge 100 ] && add_check CAT_VPN "Гео-RU список (ru_nets)" "ok" "${RU_SET} сетей" || add_check CAT_VPN "Гео-RU список (ru_nets)" "warning" "Мало/пусто: ${RU_SET:-0}"

BL_SET=$(docker exec vpn_wireguard ipset list blocked_nets 2>/dev/null | grep -cE '^[0-9]+\.')
[ "${BL_SET:-0}" -ge 100 ] && add_check CAT_VPN "Блокировки РКН (blocked_nets)" "ok" "${BL_SET} сетей" || add_check CAT_VPN "Блокировки РКН (blocked_nets)" "warning" "Мало/пусто: ${BL_SET:-0}"

MSS=$(docker exec vpn_wireguard iptables -t mangle -S 2>/dev/null | grep -i "TCPMSS")
[ -n "$MSS" ] && add_check CAT_VPN "MSS-clamping (анти-тормоза)" "ok" "Активно" || add_check CAT_VPN "MSS-clamping (анти-тормоза)" "warning" "Не найдено (возможны тормоза)"

# rp_filter должен быть 0: гибридная маршрутизация асимметрична (ответы из мира приходят
# через туннель), при rp_filter=1 ядро их дропает и обход ломается.
RP=$(docker exec vpn_wireguard sysctl -n net.ipv4.conf.all.rp_filter 2>/dev/null)
[ "$RP" = "0" ] && add_check CAT_VPN "rp_filter (асимм. маршрутизация)" "ok" "0 (верно)" || add_check CAT_VPN "rp_filter (асимм. маршрутизация)" "warning" "${RP:-?} — должно быть 0, иначе рвётся обход"

PEERS_TOTAL=$(docker exec vpn_wireguard wg show wg0 peers 2>/dev/null | grep -c .)
PEERS_ACT=$(docker exec vpn_wireguard wg show wg0 latest-handshakes 2>/dev/null | awk -v n="$(date +%s)" '$2>0 && (n-$2)<180{c++} END{print c+0}')
add_check CAT_VPN "Пиры WireGuard" "ok" "Всего: ${PEERS_TOTAL:-0}, онлайн: ${PEERS_ACT:-0}"

DE_HS=$(docker exec vpn_wireguard wg show wg0 latest-handshakes 2>/dev/null | awk '{if($2>m)m=$2} END{print m+0}')
if [ "${DE_HS:-0}" -gt 0 ]; then
    HS_AGE=$(( $(date +%s) - DE_HS ))
    [ "$HS_AGE" -lt 180 ] && add_check CAT_VPN "Активность туннеля (хэндшейк)" "ok" "Свежий (${HS_AGE}s назад)" || add_check CAT_VPN "Активность туннеля (хэндшейк)" "warning" "Устарел (${HS_AGE}s)"
else
    add_check CAT_VPN "Активность туннеля (хэндшейк)" "warning" "Нет свежих хэндшейков"
fi

WG_DUMP=$(docker exec vpn_wireguard wg show wg0 dump 2>/dev/null | wc -l)
[ "$WG_DUMP" -ge 1 ] && add_check CAT_VPN "Ответ ядра WireGuard" "ok" "Успешно" || add_check CAT_VPN "Ответ ядра WireGuard" "error" "Ядро зависло/не отвечает"

TUN=$(ls /dev/net/tun 2>/dev/null)
[ -n "$TUN" ] && add_check CAT_VPN "Модуль TUN/TAP" "ok" "Доступен" || add_check CAT_VPN "Модуль TUN/TAP" "error" "Не найден"

sleep 1

echo "storage" > "$STATUS_FILE"

ROOT_DISK=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
[ -z "$ROOT_DISK" ] && ROOT_DISK=0
[ "$ROOT_DISK" -lt 95 ] && add_check CAT_STORAGE "Свободное место на диске (/)" "ok" "${ROOT_DISK}% занято" || add_check CAT_STORAGE "Свободное место на диске (/)" "error" "Критично: ${ROOT_DISK}%"

INODES=$(df -i / | awk 'NR==2 {print $5}' | tr -d '%')
[ -z "$INODES" ] && INODES=0
[ "$INODES" -lt 95 ] && add_check CAT_STORAGE "Индексные дескрипторы (Inodes)" "ok" "${INODES}% занято" || add_check CAT_STORAGE "Индексные дескрипторы (Inodes)" "error" "Заканчиваются: ${INODES}%"

touch /tmp/audit_rw_test 2>/dev/null && rm /tmp/audit_rw_test 2>/dev/null
[ $? -eq 0 ] && add_check CAT_STORAGE "Права записи на диск" "ok" "Доступно (R/W)" || add_check CAT_STORAGE "Права записи на диск" "error" "Диск в режиме Read-Only!"

[ -d "$APP_DIR/volumes/database" ] && add_check CAT_STORAGE "Директория БД (/database)" "ok" "Смонтирована" || add_check CAT_STORAGE "Директория БД (/database)" "error" "Отсутствует"

# ИСПРАВЛЕНО: проверяем коннект с правильным пользователем БД vpn_admin
docker exec vpn_db pg_isready -U vpn_admin -d vpndb >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_STORAGE "Соединение с PostgreSQL" "ok" "Принимает запросы" || add_check CAT_STORAGE "Соединение с PostgreSQL" "error" "Отказ в обслуживании"

DB_SIZE=$(docker exec vpn_db sh -c 'psql -U vpn_admin -d vpndb -tAc "SELECT pg_size_pretty(pg_database_size(current_database()))"' 2>/dev/null | tr -d ' \r')
[ -n "$DB_SIZE" ] && add_check CAT_STORAGE "Размер базы данных" "ok" "$DB_SIZE" || add_check CAT_STORAGE "Размер базы данных" "warning" "Не удалось получить"

BK_COUNT=$(ls -1 "$APP_DIR/volumes/backups"/*.sql.gz "$APP_DIR/volumes/backups"/*.tar.gz 2>/dev/null | wc -l)
[ "${BK_COUNT:-0}" -ge 1 ] && add_check CAT_STORAGE "Файлов бэкапов" "ok" "${BK_COUNT} шт." || add_check CAT_STORAGE "Файлов бэкапов" "warning" "Нет файлов бэкапа"

[ -d "$APP_DIR/volumes/backups" ] && add_check CAT_STORAGE "Директория резервных копий" "ok" "Существует" || add_check CAT_STORAGE "Директория резервных копий" "warning" "Отсутствует"

# Проверка искала `backup_latest.tar.gz` — имя БЕЗ расширения шифрования. А
# когда пароль архива задан (как и положено), файл называется
# `backup_latest.tar.gz.gpg`, и проверка не находила его никогда. То есть она
# ломалась ровно в том случае, когда всё настроено правильно.
#
# На живом узле так и было: свежий шифрованный архив лежал на месте, а отчёт
# писал «Бэкап не найден» — строкой ниже собственного «Файлов бэкапов: 6».
BACKUP_DIR="$APP_DIR/volumes/backups"
NEWEST_BACKUP=""
for CAND in "$BACKUP_DIR/backup_latest.tar.gz.gpg" "$BACKUP_DIR/backup_latest.tar.gz"; do
    [ -f "$CAND" ] && { NEWEST_BACKUP="$CAND"; break; }
done
# Копии под привычным именем нет — смотрим историю: она пишется теми же
# сборками и годится не хуже.
[ -z "$NEWEST_BACKUP" ] && NEWEST_BACKUP=$(ls -t "$BACKUP_DIR"/archive/*.tar.gz* 2>/dev/null | head -1)

if [ -z "$NEWEST_BACKUP" ]; then
    add_check CAT_STORAGE "Актуальность Бэкапа" "warning" "Бэкап не найден"
else
    case "$NEWEST_BACKUP" in
        *.gpg) BK_KIND="шифрованный" ;;
        *)     BK_KIND="БЕЗ ШИФРОВАНИЯ" ;;
    esac
    if [ -n "$(find "$NEWEST_BACKUP" -mtime -2 2>/dev/null)" ]; then
        # Незашифрованный архив — это ключ сервера и конфиги всех людей
        # открытым текстом, и «ок» тут ставить нельзя.
        case "$NEWEST_BACKUP" in
            *.gpg) add_check CAT_STORAGE "Актуальность Бэкапа" "ok" "Свежий (< 48ч), $BK_KIND" ;;
            *)     add_check CAT_STORAGE "Актуальность Бэкапа" "warning" "Свежий, но $BK_KIND" ;;
        esac
    else
        add_check CAT_STORAGE "Актуальность Бэкапа" "warning" "Устарел (> 48ч), $BK_KIND"
    fi
fi

[ -d "$APP_DIR/volumes/configs" ] && add_check CAT_STORAGE "Хранилище конфигов" "ok" "Доступно" || add_check CAT_STORAGE "Хранилище конфигов" "error" "Удалено"

ENV_PERM=$(stat -c "%a" "$APP_DIR/.env" 2>/dev/null)
[ -z "$ENV_PERM" ] && ENV_PERM="none"
if [ "$ENV_PERM" = "600" ] || [ "$ENV_PERM" = "640" ]; then
    add_check CAT_STORAGE "Права доступа к .env" "ok" "Безопасные ($ENV_PERM)"
else
    add_check CAT_STORAGE "Права доступа к .env" "warning" "Открыты всем: $ENV_PERM (рекомендуется 600)"
fi

sleep 1

echo "security" > "$STATUS_FILE"

# Спрашиваем у самого sshd, а не грепаем файл. Настройки живут ещё и в
# /etc/ssh/sshd_config.d/ — туда их кладёт хостинг при выдаче машины, и там у
# нас стояли `PasswordAuthentication yes` и `PermitRootLogin yes`, пока аудит
# рапортовал «Защищён» и «по ключам». Проверка защиты, которая не видит
# половину настроек, хуже отсутствующей: она успокаивает.
SSHD_EFF=$(sshd -T 2>/dev/null)
if [ -z "$SSHD_EFF" ]; then
    # sshd -T требует root и корректного конфига. Не ответил — так и говорим,
    # а не додумываем за него.
    add_check CAT_SEC "SSH Root Login" "warning" "Не удалось прочитать настройки sshd"
    add_check CAT_SEC "Вход по паролю (SSH)" "warning" "Не удалось прочитать настройки sshd"
    SSH_PORT=$(grep -iE "^Port\s+" /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}')
else
    ROOT_SSH=$(echo "$SSHD_EFF" | grep -i "^permitrootlogin " | awk '{print $2}')
    case "$ROOT_SSH" in
        yes)
            add_check CAT_SEC "SSH Root Login" "warning" "Разрешен (Рекомендуется отключить)" ;;
        prohibit-password|without-password)
            add_check CAT_SEC "SSH Root Login" "ok" "Только по ключу" ;;
        *)
            add_check CAT_SEC "SSH Root Login" "ok" "Защищен" ;;
    esac

    SSH_PASS=$(echo "$SSHD_EFF" | grep -i "^passwordauthentication " | awk '{print $2}')
    SSH_KBD=$(echo "$SSHD_EFF" | grep -i "^kbdinteractiveauthentication " | awk '{print $2}')
    if [ "$SSH_PASS" = "yes" ] || [ "$SSH_KBD" = "yes" ]; then
        # Проверяем обе: клавиатурный вход — это тот же пароль, просто спрошенный
        # иначе, и отключив только первую, защиты не получаешь.
        add_check CAT_SEC "Вход по паролю (SSH)" "warning" "Разрешен (Уязвимо к брутфорсу)"
    else
        add_check CAT_SEC "Вход по паролю (SSH)" "ok" "Отключен (по ключам)"
    fi

    SSH_PORT=$(echo "$SSHD_EFF" | grep -i "^port " | awk '{print $2}' | head -1)
fi
[ "${SSH_PORT:-22}" = "22" ] && add_check CAT_SEC "Порт SSH" "warning" "Стандартный 22 (Риск)" || add_check CAT_SEC "Порт SSH" "ok" "Нестандартный (${SSH_PORT:-22})"

UFW_STAT=$(ufw status 2>/dev/null | grep -i "active")
IPT_STAT=$(iptables -L -n 2>/dev/null | grep "Chain INPUT" | wc -l)
if [ -n "$UFW_STAT" ]; then
    add_check CAT_SEC "Межсетевой экран (Firewall)" "ok" "UFW Активен"
elif [ "$IPT_STAT" -gt 0 ]; then
    add_check CAT_SEC "Межсетевой экран (Firewall)" "ok" "Iptables настроен"
else
    add_check CAT_SEC "Межсетевой экран (Firewall)" "warning" "Не обнаружен"
fi

F2B=$(systemctl is-active fail2ban 2>/dev/null)
[ "$F2B" = "active" ] && add_check CAT_SEC "Служба Fail2Ban" "ok" "Защищает от брутфорса" || add_check CAT_SEC "Служба Fail2Ban" "warning" "Не установлена"

EMPTY_PW=$(awk -F: '($2 == "") {print $1}' /etc/shadow 2>/dev/null)
[ -z "$EMPTY_PW" ] && add_check CAT_SEC "Пустые пароли пользователей" "ok" "Не обнаружены" || add_check CAT_SEC "Пустые пароли пользователей" "error" "ОПАСНОСТЬ: Есть аккаунты без пароля"

visudo -c >/dev/null 2>&1
[ $? -eq 0 ] && add_check CAT_SEC "Синтаксис Sudoers" "ok" "Корректен" || add_check CAT_SEC "Синтаксис Sudoers" "error" "Сломан файл sudoers!"

TODAY_STR=$(date '+%b %e' | sed 's/  / /')
FAILED_TOTAL=$(grep "Failed password" /var/log/auth.log 2>/dev/null | wc -l)
FAILED_TODAY=$(grep "Failed password" /var/log/auth.log 2>/dev/null | grep "^$TODAY_STR" | wc -l)

if [ "$FAILED_TOTAL" -gt 50 ]; then
    add_check CAT_SEC "Брутфорс атаки (SSH)" "warning" "За сегодня: $FAILED_TODAY | Всего: $FAILED_TOTAL"
else
    add_check CAT_SEC "Брутфорс атаки (SSH)" "ok" "За сегодня: $FAILED_TODAY | Всего: $FAILED_TOTAL"
fi

sleep 1

echo "services" > "$STATUS_FILE"

systemctl is-active --quiet vpn-updater
[ $? -eq 0 ] && add_check CAT_LOGS "Демон vpn-updater" "ok" "Active" || add_check CAT_LOGS "Демон vpn-updater" "error" "Остановлен"

# Расписание в проекте держится на таймерах systemd: уборка, обновления,
# проверка хоста. Cron нам не нужен вовсе, и ругаться на его отсутствие значит
# каждую неделю показывать предупреждение, на которое нечего ответить.
#
# Проверяем то, что действительно важно: живы ли НАШИ таймеры.
TIMERS_DEAD=""
for T in vpn-cleanup.timer apt-daily-upgrade.timer; do
    systemctl list-unit-files "$T" >/dev/null 2>&1 || continue
    [ "$(systemctl is-active "$T" 2>/dev/null)" = "active" ] || TIMERS_DEAD="$TIMERS_DEAD $T"
done
if [ -n "$TIMERS_DEAD" ]; then
    add_check CAT_LOGS "Таймеры обслуживания" "warning" "Не запущены:$TIMERS_DEAD"
else
    add_check CAT_LOGS "Таймеры обслуживания" "ok" "Уборка и обновления по расписанию"
fi

CRON_STAT=$(systemctl is-active cron 2>/dev/null || systemctl is-active crond 2>/dev/null)
[ "$CRON_STAT" = "active" ] && add_check CAT_LOGS "Планировщик (Cron)" "ok" "Работает" || add_check CAT_LOGS "Планировщик (Cron)" "ok" "Не используется (расписание на таймерах systemd)"

JOURNAL_STAT=$(systemctl is-active systemd-journald 2>/dev/null)
[ "$JOURNAL_STAT" = "active" ] && add_check CAT_LOGS "Системный Журнал (Journald)" "ok" "Работает" || add_check CAT_LOGS "Системный Журнал (Journald)" "error" "Остановлен"

FAILED_UNITS=$(systemctl list-units --state=failed --no-legend 2>/dev/null | wc -l)
[ "$FAILED_UNITS" -eq 0 ] && add_check CAT_LOGS "Упавшие службы Linux" "ok" "0" || add_check CAT_LOGS "Упавшие службы Linux" "warning" "Найдено: $FAILED_UNITS"

OOM=$(dmesg 2>/dev/null | grep -i "killed process" | wc -l)
[ "$OOM" -eq 0 ] && add_check CAT_LOGS "OOM Killer (Нехватка памяти)" "ok" "Не зафиксировано" || add_check CAT_LOGS "OOM Killer (Нехватка памяти)" "warning" "Были утечки памяти"

check_logs() {
    local errs=$(docker logs --tail 150 "$1" 2>&1 | grep -iE "error|fatal|exception|traceback" | grep -viE "Task was destroyed|CancelledError" | tail -n 1)
    if [ -n "$errs" ]; then
        local short_errs="${errs:0:80}"
        [ "${#errs}" -gt 80 ] && short_errs="${short_errs}..."
        local cln=$(clean "$short_errs")
        add_check CAT_LOGS "Логи контейнера $1" "warning" "$cln"
    else
        add_check CAT_LOGS "Логи контейнера $1" "ok" "Чисто"
    fi
}

check_logs "vpn_bot"
check_logs "vpn_wireguard"
check_logs "vpn_db"

UPDATES=$(apt-get -s upgrade 2>/dev/null | grep -Po "^Inst \K[^ ]+" | wc -l)
[ "${UPDATES:-0}" -eq 0 ] && add_check CAT_LOGS "Системные обновления ОС" "ok" "Все установлено" || add_check CAT_LOGS "Системные обновления ОС" "warning" "Доступно $UPDATES пакетов"

# --- Сверка базы с тем, что реально стоит ---------------------------------
# Проверки выше отвечают на «живо ли». Эта — на «то ли живо, что мы думаем»:
# есть ли на узле все пиры из базы и нет ли лишних, разложены ли имена, стоят
# ли правила ролей, считается ли трафик, не отстала ли Германия по версии.
#
# Живёт в контейнере бота: только там есть и база, и связь с узлом, и знание
# про вторую ноду. Отдаёт строки вида «состояние|название|подробности».
CONTRACT="/app/tests/contract/node_contract.py"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx vpn_bot; then
    CONTRACT_OUT=$(docker exec vpn_bot python3 "$CONTRACT" 2>/dev/null) || true
    if [ -n "$CONTRACT_OUT" ]; then
        # Без конвейера: через «|» цикл ушёл бы в подоболочку, и собранные
        # в нём проверки не дожили бы до сборки отчёта.
        OLD_IFS="$IFS"
        IFS='
'
        for line in $CONTRACT_OUT; do
            case "$line" in ok\|*|warning\|*|error\|*) ;; *) continue ;; esac
            c_status=$(printf '%s' "$line" | cut -d'|' -f1)
            c_name=$(printf '%s' "$line" | cut -d'|' -f2)
            c_msg=$(printf '%s' "$line" | cut -d'|' -f3-)
            add_check CAT_VPN "$c_name" "$c_status" "$c_msg"
        done
        IFS="$OLD_IFS"
    else
        add_check CAT_VPN "Сверка базы с узлом" "warning" "не дала ответа"
    fi
else
    add_check CAT_VPN "Сверка базы с узлом" "warning" "контейнер бота не запущен"
fi

# --- Отчёты недельного обслуживания ---------------------------------------
# Сборщик мусора и проверка хоста пишут свои отчёты сюда же, в volumes/flags,
# раз в неделю. Аудит их читает, а не перемеряет: так видно не только текущее
# состояние, но и то, что обслуживание вообще происходит. Молчащий таймер
# раньше выглядел ровно как исправный.

jget() {   # jget <файл> <поле> — одно значение из плоского JSON, без jq
    grep -o "\"$2\"[[:space:]]*:[[:space:]]*\"\?[^,\"}]*" "$1" 2>/dev/null         | head -n 1 | sed 's/.*:[[:space:]]*"\?//; s/[[:space:]]*$//'
}
jint() {   # то же, но числом; мусор и пустоту считаем нулём
    local v
    v=$(jget "$1" "$2" | tr -d ' ')
    case "$v" in ''|-|*[!0-9-]*) echo 0;; *) echo "$v";; esac
}

NOW_TS=$(date +%s)
STALE_DAYS=9   # таймер недельный; девять дней — это уже пропуск, а не разброс

GC_FILE="$FLAG_DIR/gc.json"
if [ -f "$GC_FILE" ]; then
    GC_TS=$(jint "$GC_FILE" ts)
    GC_AGE=$(( (NOW_TS - GC_TS) / 86400 ))
    GC_FREED=$(jint "$GC_FILE" freed_mb)
    if [ "$GC_TS" -le 0 ]; then
        add_check CAT_STORAGE "Уборка мусора" "warning" "Отчёт не читается — файл повреждён"
    elif [ "$GC_AGE" -gt "$STALE_DAYS" ]; then
        add_check CAT_STORAGE "Уборка мусора" "warning" "Последняя ${GC_AGE} дн. назад — таймер не сработал"
    elif [ "$GC_FREED" -gt 0 ]; then
        add_check CAT_STORAGE "Уборка мусора" "ok" "${GC_AGE} дн. назад, освободила ${GC_FREED} МБ"
    else
        add_check CAT_STORAGE "Уборка мусора" "ok" "${GC_AGE} дн. назад, заметного мусора не было"
    fi
else
    add_check CAT_STORAGE "Уборка мусора" "warning" "Ещё не отрабатывала"
fi

HH_FILE="$FLAG_DIR/host_health.json"
if [ -f "$HH_FILE" ]; then
    HH_TS=$(jint "$HH_FILE" ts)
    HH_AGE=$(( (NOW_TS - HH_TS) / 86400 ))
    if [ "$HH_TS" -le 0 ]; then
        add_check CAT_HOST "Недельная проверка хоста" "warning" "Отчёт не читается — файл повреждён"
    elif [ "$HH_AGE" -gt "$STALE_DAYS" ]; then
        add_check CAT_HOST "Недельная проверка хоста" "warning" "Последняя ${HH_AGE} дн. назад — таймер не сработал"
    else
        add_check CAT_HOST "Недельная проверка хоста" "ok" "${HH_AGE} дн. назад"
    fi

    # Остальное имеет смысл только если отчёт прочитался: из пустых
    # значений нельзя делать вывод «всё в порядке».
    if [ "$HH_TS" -gt 0 ]; then
        # Флаг ядра после обновлений. Его не смотрел никто, а плановая перезагрузка
        # идёт по часам и о нём не знает: если она почему-то не случилась, флаг
        # висит неделями, и обновления лежат применёнными наполовину.
        if [ "$(jget "$HH_FILE" reboot_required)" = "true" ]; then
            add_check CAT_HOST "Перезагрузка после обновлений" "warning" "Требуется — плановая не применила обновления"
        else
            add_check CAT_HOST "Перезагрузка после обновлений" "ok" "Не требуется"
        fi

        HH_UPG=$(jint "$HH_FILE" packages_upgradable)
        if [ "$HH_UPG" -gt 50 ]; then
            add_check CAT_HOST "Пакеты в очереди на обновление" "warning" "${HH_UPG} шт. — ночной apt не справляется"
        else
            add_check CAT_HOST "Пакеты в очереди на обновление" "ok" "${HH_UPG} шт."
        fi

        # /var/log — это НЕ журнал systemd, его чистит вакуум. Здесь файлы служб,
        # за которыми до появления ротации не следил никто.
        HH_LOG=$(jint "$HH_FILE" var_log_mb)
        if [ "$HH_LOG" -ge 1024 ]; then
            add_check CAT_STORAGE "Каталог /var/log" "warning" "${HH_LOG} МБ — ротация не справляется"
        else
            add_check CAT_STORAGE "Каталог /var/log" "ok" "${HH_LOG} МБ"
        fi
    fi
else
    add_check CAT_HOST "Недельная проверка хоста" "warning" "Ещё не отрабатывала"
fi

# ---- ПОДГОТОВКА JSON И ИСПРАВЛЕНИЕ RACE CONDITION ----

CAT_NET="[${CAT_NET%,}]"
CAT_HOST="[${CAT_HOST%,}]"
CAT_DOCKER="[${CAT_DOCKER%,}]"
CAT_VPN="[${CAT_VPN%,}]"
CAT_STORAGE="[${CAT_STORAGE%,}]"
CAT_SEC="[${CAT_SEC%,}]"
CAT_LOGS="[${CAT_LOGS%,}]"

cat <<EOF > "$REPORT_FILE"
{
  "network": $CAT_NET,
  "host": $CAT_HOST,
  "docker": $CAT_DOCKER,
  "vpn": $CAT_VPN,
  "storage": $CAT_STORAGE,
  "security": $CAT_SEC,
  "services": $CAT_LOGS
}
EOF

# ТОЛЬКО ПОСЛЕ сохранения файла сообщаем боту, что данные готовы!
echo "done" > "$STATUS_FILE"