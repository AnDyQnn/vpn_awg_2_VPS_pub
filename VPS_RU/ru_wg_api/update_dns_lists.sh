#!/bin/bash
# Загрузка списков доменов по категориям.
#
# Качаем ТОЛЬКО те категории, которые кем-то включены: список категорий приходит
# первым аргументом от панели узла. На узле одно ядро и два гигабайта — держать
# сотни тысяч доменов «на всякий случай» незачем.
#
# Неудачная загрузка НЕ обнуляет кэш: фильтровать по вчерашнему списку лучше,
# чем молча перестать фильтровать. Новый файл заменяет старый только целиком
# и только если в нём набралось разумное число строк.

CACHE_DIR="/etc/amnezia/amneziawg/cache/dns"
mkdir -p "$CACHE_DIR"

MIN_LINES=200        # меньше — это страница ошибки, а не список

# Откуда качать — спрашиваем у самого узла, а не держим вторую копию.
#
# Копия здесь и была: в коде узла категорий стало четырнадцать, а в этом
# файле осталось пять. Девять новых не качались, а выглядели рабочими.
SOURCES_RAW="$(python3 - <<'PYLIST' 2>/dev/null
import sys
sys.path.insert(0, '/app')
from dnsfilter import CATEGORIES
for key, meta in CATEGORIES.items():
    print(key, ' '.join(meta.get('urls') or []))
PYLIST
)"

declare -A SOURCES
while read -r key urls; do
    [ -n "$key" ] && SOURCES[$key]="$urls"
done <<< "$SOURCES_RAW"

if [ ${#SOURCES[@]} -eq 0 ]; then
    echo "[dns-lists] перечень категорий из dnsfilter.py не прочитался"
    exit 1
fi

CATS="$1"
if [ -z "$CATS" ]; then
    echo "[dns-lists] включённых категорий нет — качать нечего"
    exit 0
fi

# По очереди, а не наперегонки. Каждое переключение категории в боте зовёт
# этот скрипт; десяток нажатий подряд запускал десяток одновременных
# скачиваний одних и тех же сотен мегабайт — процессор узла уходил в потолок,
# и DNS переставал отвечать людям.
exec 9>/tmp/update_dns_lists.lock
flock 9

# Свежий список не перекачиваем. Качаем то, чего нет, и то, что старше 12
# часов; плановое обновление раз в 12 часов идёт с FORCE=1 и берёт всё.
# Раньше каждое нажатие перекачивало и заново разбирало ВСЕ включённые
# категории — мегабайты рекламы и взрослого на каждую галочку.
FRESH_SECONDS=43200
now=$(date +%s)

for cat in $CATS; do
    urls="${SOURCES[$cat]}"
    if [ -z "$urls" ]; then
        echo "[dns-lists] неизвестная категория: $cat"
        continue
    fi
    if [ "${FORCE:-0}" != "1" ] && [ -s "$CACHE_DIR/$cat.txt" ]; then
        age=$(( now - $(date -r "$CACHE_DIR/$cat.txt" +%s 2>/dev/null || echo 0) ))
        if [ "$age" -lt "$FRESH_SECONDS" ]; then
            continue
        fi
    fi
    tmp="$(mktemp)"
    ok=0
    for url in $urls; do
        if curl -fsSL --max-time 60 "$url" >> "$tmp" 2>/dev/null; then
            ok=1
        else
            echo "[dns-lists] не скачалось: $url"
        fi
    done
    lines="$(wc -l < "$tmp" 2>/dev/null || echo 0)"
    if [ "$ok" = "1" ] && [ "$lines" -ge "$MIN_LINES" ]; then
        mv "$tmp" "$CACHE_DIR/$cat.txt"
        echo "[dns-lists] $cat обновлён: $lines строк"
    else
        rm -f "$tmp"
        if [ -s "$CACHE_DIR/$cat.txt" ]; then
            echo "[dns-lists] $cat не обновился, остаётся прошлый кэш"
        else
            echo "[dns-lists] $cat не загружен и кэша нет — категория пока не фильтрует"
        fi
    fi
done
