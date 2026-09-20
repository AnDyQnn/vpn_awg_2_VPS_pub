#!/bin/bash
# Сверка базы с тем, что реально стоит на узле — по расписанию.
#
# Ту же сверку зовёт аудит по кнопке, и там она видна сразу. Но кнопку нажимают
# редко, а расходится состояние само: от перезапуска контейнера, от правки
# руками, от команды, которая не доехала. Между двумя нажатиями узел может
# неделями стоять с доступом, которого никто не выдавал.
#
# Поэтому то же самое раз в неделю, из уборки. Результат кладётся рядом с
# остальными отчётами; ошибки дополнительно уходят в журнал системы, чтобы их
# было видно обычным `journalctl -u vpn-cleanup`.
#
# Ничего не меняет — только читает.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_DIR="${1:-$(dirname "$SCRIPT_DIR")}"
OUT_DIR="$NODE_DIR/volumes/flags"
OUT="$OUT_DIR/contract.json"
mkdir -p "$OUT_DIR"

# Сверка живёт в контейнере бота: только там есть и база, и связь с узлом.
# На ноде без бота (Германия) сверять нечем — её проверяет мастер, с той
# стороны туннеля, и это правильное место: про базу она не знает ничего.
if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx vpn_bot; then
    echo "[contract] бота на этой ноде нет — сверку делает мастер"
    exit 0
fi

RAW=$(docker exec vpn_bot python3 /app/tests/contract/node_contract.py 2>/dev/null) || true
LINES=$(printf '%s\n' "$RAW" | grep -E '^(ok|warning|error)\|') || true

if [ -z "$LINES" ]; then
    echo "[contract] сверка не дала ответа"
    printf '{"ts": %s, "ok": 0, "warning": 0, "error": 0, "answered": false}\n' \
        "$(date +%s)" > "$OUT"
    exit 0
fi

# Охрана порта подписки — единственная проверка отсюда, с хоста: правила живут
# в iptables, и из контейнера бота их не видно.
#
# Смотреть на её счётчики надо потому, что отбивает она молча. Предел на
# соединения с одного адреса оказался тесен для телефона, который тянет
# гео-файлы в несколько потоков: человек получал обрыв, приложение считало
# профиль испорченным, и не работало вообще ничего. Со стороны это выглядело
# как «Xray сломался», а на деле его резала своя же защита.
#
# Счётчики обнуляются при каждой выкладке — цепочка пересоздаётся. Значит число
# здесь означает «с прошлого обновления», и это ровно тот масштаб, что нужен.
if iptables -L VPN_SUB -n >/dev/null 2>&1; then
    DROPPED=$(iptables -L VPN_SUB -n -v -x 2>/dev/null         | awk '/DROP/ {s += $1} END {print s + 0}')
    if [ "${DROPPED:-0}" -gt 0 ]; then
        LINES="$LINES
warning|Подписка наружу · охрана порта|отбито пакетов: $DROPPED — если люди жалуются на гео-файлы, предел тесен"
    else
        LINES="$LINES
ok|Подписка наружу · охрана порта|ничего не отбито"
    fi
fi

# Сайты-маски REALITY. Тоже проверка с хоста: нужен бинарь Xray из контейнера
# узла, и нужен он именно оттуда — важно, как сайт выглядит С УЗЛА.
#
# Почему это вообще проверяется. В REALITY клиент проверяет сертификат маски
# как настоящий; не проверился — соединение оборвано. Сбербанк отдаёт
# сертификат российского удостоверяющего центра, которого нет в хранилищах
# телефонов, и вход с такой маской не работал никогда. Глазами это не видно:
# в России такой сертификат доверенный, и владелец видит «сайт открывается»
# там, где у людей рвётся связь.
#
# Проверяем ровно то, что делает клиент: рукопожатие с SNI.
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx vpn_wireguard; then
    DESTS=$(docker exec vpn_wireguard sh -c         'grep -o "\"dest\": \"[^\"]*\"" /etc/amnezia/amneziawg/xray.json' 2>/dev/null         | sed 's/.*: *"//; s/"$//; s/:443$//' | sort -u)
    # Имя узла: им же проверяется своя заглушка.
    SELF_DOMAIN=$(grep -E "^PUBLIC_DOMAIN=" "$NODE_DIR/.env" 2>/dev/null |
                  tail -1 | cut -d= -f2- | tr -d "\"' \r")
    for D in $DESTS; do
        # Своя заглушка живёт на петле внутри контейнера — постучаться к ней
        # снаружи нечем. Зато можно проверить весь путь ровно так, как его
        # проходит клиент: рукопожатие с именем узла на его же 443, где стоит
        # Xray и уводит к заглушке. Это даже честнее прямой проверки: она
        # подтвердила бы, что заглушка жива, но не что до неё доходит.
        case "$D" in
            127.0.0.1:*|localhost:*)
                if [ -z "$SELF_DOMAIN" ]; then
                    LINES="$LINES
error|Маска REALITY · свой сайт|выбрана своя заглушка, а имени узла в .env нет"
                    continue
                fi
                D="$SELF_DOMAIN"
                ;;
        esac
        OUT=$(docker exec vpn_wireguard sh -c "/usr/local/bin/xray tls ping $D 2>&1" 2>/dev/null)
        SNI=$(printf '%s' "$OUT" | sed -n '/Pinging with SNI/,$p')
        if printf '%s' "$SNI" | grep -q "Handshake failure"; then
            WHY=$(printf '%s' "$SNI" | grep -m1 "Handshake failure" | cut -c1-90)
            LINES="$LINES
error|Маска REALITY · $D|$WHY"
        elif printf '%s' "$SNI" | grep -q "TLS 1.3"; then
            LINES="$LINES
ok|Маска REALITY · $D|рукопожатие с SNI, TLS 1.3"
        else
            LINES="$LINES
warning|Маска REALITY · $D|рукопожатие есть, но не TLS 1.3 — Reality требует его"
        fi
    done
fi


N_OK=$(printf '%s\n' "$LINES" | grep -c '^ok|') || true
N_WARN=$(printf '%s\n' "$LINES" | grep -c '^warning|') || true
N_ERR=$(printf '%s\n' "$LINES" | grep -c '^error|') || true

# Ошибки — в журнал системы, чтобы их было видно без бота и без кнопки.
printf '%s\n' "$LINES" | grep '^error|' | while IFS='|' read -r _ name msg; do
    echo "[contract] РАСХОЖДЕНИЕ: $name — $msg"
done

{
    printf '{"ts": %s, "ok": %s, "warning": %s, "error": %s, "answered": true,\n' \
        "$(date +%s)" "${N_OK:-0}" "${N_WARN:-0}" "${N_ERR:-0}"
    printf ' "lines": ['
    printf '%s\n' "$LINES" | awk -F'|' '{
        gsub(/"/, "", $2); gsub(/"/, "", $3);
        printf "%s{\"status\":\"%s\",\"name\":\"%s\",\"msg\":\"%s\"}",
               (NR > 1 ? ",\n          " : ""), $1, $2, $3
    }'
    printf ']}\n'
} > "$OUT"

echo "[contract] в порядке ${N_OK:-0}, предупреждений ${N_WARN:-0}, расхождений ${N_ERR:-0}"
exit 0
