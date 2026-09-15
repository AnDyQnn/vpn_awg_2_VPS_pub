#!/bin/bash

# Включаем глобальный форвардинг
sysctl -w net.ipv4.ip_forward=1

echo "🚀 Starting RU Master Node..."

# Создаём оба набора заранее, чтобы правила iptables в api.py не падали на отсутствии set.
#   ru_nets      — гео-IP РФ (идёт напрямую)
#   blocked_nets — блокировки РКН из antifilter (принудительно в Германию)
ipset create ru_nets hash:net family inet hashsize 4096 maxelem 1000000 -exist
ipset create blocked_nets hash:net family inet hashsize 4096 maxelem 1000000 -exist

# Тёплый старт из кэша (volume переживает рестарт): маршрутизация работает сразу,
# не дожидаясь первого сетевого обновления.
CACHE_DIR="/etc/amnezia/amneziawg/cache"
if [ -s "$CACHE_DIR/ru_nets.cidr" ]; then
    grep -E '^[0-9.]+/[0-9]+$' "$CACHE_DIR/ru_nets.cidr" | sed 's/^/add ru_nets /' | ipset restore -!
fi
if [ -s "$CACHE_DIR/blocked_nets.cidr" ]; then
    grep -E '^[0-9.]+/[0-9]+$' "$CACHE_DIR/blocked_nets.cidr" | sed 's/^/add blocked_nets /' | ipset restore -!
fi

# Фоновые обновления списков — НЕ в первые секунды жизни узла.
#
# У узла одно ядро, и в первую минуту оно нужно на то, ради чего он вообще
# существует: поднять туннель и панель. Списки в это время только мешают —
# категория «adult» одна весит под миллион строк, и их разбор отнимает ровно те
# секунды, в которые проверка после обновления ждёт ответа панели.
#
# Замерено на живом узле: панель отвечала на 57-й секунде вместо тридцатой, и
# обновление откатывалось как больное, будучи здоровым.
#
# Ждать не страшно: маршрутизация стартует из кэша выше, а списки фильтров
# лежат в томе с прошлого раза. Обновиться они успеют — у них впереди сутки.
STARTUP_QUIET=120

(
  sleep "$STARTUP_QUIET"
  while true; do
    bash /app/update_ru_ips.sh
    sleep 43200
  done
) &

# DNS-фильтр: отдельный процесс. Поднимается всегда, но пока никому не включены
# категории, он просто пересылает запросы наверх и ничего не держит в памяти.
# Заворачивать на него 53-й порт узел будет только для тех, у кого фильтры есть.
/opt/venv/bin/python3 -u /app/dnsfilter.py &

# Обновление списков категорий раз в 12 часов — только тех, что реально включены.
(
  sleep "$STARTUP_QUIET"
  while true; do
    CATS="$(/opt/venv/bin/python3 - <<'PY'
import json, os
p = "/etc/amnezia/amneziawg/dns_filter.json"
cats = set()
try:
    with open(p) as f:
        for v in (json.load(f) or {}).get("clients", {}).values():
            cats.update(v)
except Exception:
    pass
print(" ".join(sorted(cats)))
PY
)"
    [ -n "$CATS" ] && bash /app/update_dns_lists.sh "$CATS"
    sleep 43200
  done
) &

# Запуск API
exec /opt/venv/bin/python3 -u -m uvicorn api:app --host 0.0.0.0 --port 8000 --app-dir /app
