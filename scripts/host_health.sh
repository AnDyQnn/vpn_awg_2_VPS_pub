#!/bin/bash
# Проверка состояния самого хоста — то, чего уборщик мусора не делал.
#
# Мусор он чистил, а вот следит ли кто за самим сервером — не следил никто: место,
# inode-таблица, разросшиеся журналы, зависшие процессы. На немецкой ноде диска всего
# 10 ГБ, там это особенно чувствительно.
#
# Пишет отчёт в volumes/flags/host_health.json — оттуда его забирает бот, чтобы
# показать в сводке и поднять тревогу при выходе за пороги. Работает и сам по себе:
# вызывается из еженедельной уборки, ничего не требует и ничего не меняет.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_DIR="${1:-$(dirname "$SCRIPT_DIR")}"
OUT_DIR="$NODE_DIR/volumes/flags"
OUT="$OUT_DIR/host_health.json"
mkdir -p "$OUT_DIR"

# Место на диске и inode-таблица корня
DISK_PCT=$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')
INODE_PCT=$(df -Pi / | awk 'NR==2 {gsub("%","",$5); print $5}')
DISK_FREE_MB=$(df -Pm / | awk 'NR==2 {print $4}')

# Журналы и данные проекта
LOG_MB=$(du -sm /var/log 2>/dev/null | awk '{print $1}')
VOLUMES_MB=$(du -sm "$NODE_DIR/volumes" 2>/dev/null | awk '{print $1}')
DOCKER_MB=$(du -sm /var/lib/docker 2>/dev/null | awk '{print $1}')

# Зависшие процессы и нагрузка
ZOMBIES=$(ps -eo stat= 2>/dev/null | grep -c '^Z' || echo 0)
LOAD=$(awk '{print $1}' /proc/loadavg)
CORES=$(nproc 2>/dev/null || echo 1)

# Требуется ли перезагрузка после обновлений — раньше этот флаг никто не смотрел
REBOOT_REQUIRED=false
[ -f /var/run/reboot-required ] && REBOOT_REQUIRED=true

# Сколько пакетов ждут обновления
UPGRADABLE=$(apt list --upgradable 2>/dev/null | grep -c upgradable || echo 0)

WARN=""
[ "${DISK_PCT:-0}" -ge 85 ] && WARN="${WARN}диск занят ${DISK_PCT}%; "
[ "${INODE_PCT:-0}" -ge 85 ] && WARN="${WARN}inode-таблица занята ${INODE_PCT}%; "
[ "${LOG_MB:-0}" -ge 1024 ] && WARN="${WARN}журналы разрослись до ${LOG_MB} МБ; "
[ "${ZOMBIES:-0}" -ge 20 ] && WARN="${WARN}зависших процессов ${ZOMBIES}; "
[ "$REBOOT_REQUIRED" = "true" ] && WARN="${WARN}нужна перезагрузка после обновлений; "

cat > "$OUT" <<JSON
{
  "ts": $(date +%s),
  "node": "$(basename "$NODE_DIR")",
  "disk_used_pct": ${DISK_PCT:-0},
  "disk_free_mb": ${DISK_FREE_MB:-0},
  "inode_used_pct": ${INODE_PCT:-0},
  "var_log_mb": ${LOG_MB:-0},
  "volumes_mb": ${VOLUMES_MB:-0},
  "docker_mb": ${DOCKER_MB:-0},
  "zombies": ${ZOMBIES:-0},
  "load": "${LOAD:-0}",
  "cores": ${CORES:-1},
  "reboot_required": ${REBOOT_REQUIRED},
  "packages_upgradable": ${UPGRADABLE:-0},
  "warning": "${WARN}"
}
JSON

if [ -n "$WARN" ]; then
    echo "[health] ВНИМАНИЕ: $WARN"
else
    echo "[health] Хост в норме: диск ${DISK_PCT}%, inode ${INODE_PCT}%, журналы ${LOG_MB} МБ."
fi
