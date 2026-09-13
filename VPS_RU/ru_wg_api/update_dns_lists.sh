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

declare -A SOURCES
SOURCES[ads]="https://raw.githubusercontent.com/blocklistproject/Lists/master/ads.txt"
SOURCES[adult]="https://raw.githubusercontent.com/blocklistproject/Lists/master/porn.txt"
SOURCES[gambling]="https://raw.githubusercontent.com/blocklistproject/Lists/master/gambling.txt"
SOURCES[malware]="https://raw.githubusercontent.com/blocklistproject/Lists/master/malware.txt https://raw.githubusercontent.com/blocklistproject/Lists/master/phishing.txt"
SOURCES[social]="https://raw.githubusercontent.com/blocklistproject/Lists/master/facebook.txt https://raw.githubusercontent.com/blocklistproject/Lists/master/tiktok.txt"

CATS="$1"
if [ -z "$CATS" ]; then
    echo "[dns-lists] включённых категорий нет — качать нечего"
    exit 0
fi

for cat in $CATS; do
    urls="${SOURCES[$cat]}"
    if [ -z "$urls" ]; then
        echo "[dns-lists] неизвестная категория: $cat"
        continue
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
