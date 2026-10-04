#!/bin/bash
# Уборка докера, которая не выбрасывает кэш сборки.
#
# Раньше здесь стоял `docker system prune -af`, и он уносил кэш сборки целиком.
# Каждая следующая выкладка собирала образы с нуля: заново качала все пакеты
# Python, а из России PyPI отдаёт по 200–350 КБ/с. Выкладка шла 5–8 минут,
# и всё это время единственное ядро узла было занято сборкой — тормозил VPN,
# а бот, не дождавшись узла, показывал «списки не загрузились».
#
# Теперь уходит то, что действительно мусор:
#   • остановленные контейнеры;
#   • образы прежних версий проекта, которыми не пользуется ни один контейнер;
#   • висячие слои;
#   • кэш сборки сверх потолка — самый старый первым.
# Потолок зависит от диска: на большом 3 ГБ, на маленьком 1,5 ГБ. И в любом
# случае на диске остаётся не меньше 2 ГБ свободного места.
#
#   docker_gc.sh            — убрать
#   docker_gc.sh --dry-run  — только показать, что занято
set -u

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

CAP="${DOCKER_CACHE_CAP:-}"
if [ -z "$CAP" ]; then
    TOTAL_KB=$(df -Pk / 2>/dev/null | awk 'NR==2 {print $2}')
    if [ "${TOTAL_KB:-0}" -gt 20000000 ]; then CAP=3gb; else CAP=1500mb; fi
fi

if [ "$DRY" = "1" ]; then
    docker system df 2>/dev/null
    echo "потолок кэша сборки: $CAP"
    exit 0
fi

docker container prune -f >/dev/null 2>&1

# Образы проекта помечены версией, и каждая выкладка оставляла бы прежнюю.
# Убираем те, на которых не стоит ни один контейнер, — включая остановленные:
# их образ может понадобиться для отката.
USED=$(docker ps -a --format '{{.Image}}' 2>/dev/null | sort -u)
docker images --format '{{.Repository}}:{{.Tag}}' 2>/dev/null \
    | grep -E '^vpn-(ru|de)-' \
    | while read -r IMG; do
        printf '%s\n' "$USED" | grep -qxF "$IMG" || docker rmi "$IMG" >/dev/null 2>&1
    done

docker image prune -f >/dev/null 2>&1

docker builder prune -af --max-used-space "$CAP" --min-free-space 2gb >/dev/null 2>&1 \
    || docker builder prune -af --keep-storage "$CAP" >/dev/null 2>&1
exit 0
