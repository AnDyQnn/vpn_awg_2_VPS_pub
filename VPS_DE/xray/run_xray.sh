#!/bin/sh
# Мост Xray: держит процесс и следит за конфигом.
#
# Доступа к докеру у контейнера нет и быть не должно. Поэтому перезапуск здесь
# устроен иначе: агент кладёт новый конфиг в общий том, а мы замечаем, что файл
# изменился, и поднимаем процесс заново сами.
#
# Два правила, ради которых всё и написано:
#
#   1. Битый конфиг не должен оставлять мост лежать. Новый проверяется ДО
#      остановки рабочего процесса; не прошёл — продолжаем на прежнем, а
#      причина уходит в состояние, чтобы владелец увидел её в боте.
#   2. Состояние пишется в файл, а не держится в голове. Агент живёт в другом
#      контейнере и о нашем процессе знать иначе не может.
set -u

DIR="/etc/xray"
CONF="$DIR/xray.json"
GOOD="$DIR/.last_good.json"
STATUS="$DIR/status.json"
LOG="$DIR/xray.log"
PERIOD="${XRAY_WATCH_SECONDS:-5}"

XRAY=/usr/local/bin/xray
PID=""
SEEN=""
ERR=""
BACKOFF=0
RETRY_AT=0

mkdir -p "$DIR"

now() { date +%s; }

stamp() {   # stamp <работает 0/1> <отпечаток конфига>
    running=$1
    fp=$2
    # Из текста ошибки вычищаем всё, что рвёт JSON: кавычки, слэши, переводы
    # строк. Иначе агент перестал бы читать состояние целиком — и мост выглядел
    # бы мёртвым не потому, что лёг, а потому что неудачно пожаловался.
    safe=$(printf '%s' "$ERR" | tr -d '"\\' | tr '\n\r\t' '   ' | cut -c1-300)
    cat > "$STATUS.tmp" <<EOF
{"running": $running, "config_stamp": "$fp", "checked_at": $(now),
 "error": "$safe", "congestion": "$CC"}
EOF
    mv "$STATUS.tmp" "$STATUS"
}

fingerprint() {
    [ -f "$CONF" ] || { echo ""; return; }
    # Размер и время правки: содержимое читать незачем, а хеш тянул бы за собой
    # лишнюю зависимость в образ.
    stat -c '%s-%Y' "$CONF" 2>/dev/null || echo "?"
}

alive() {
    [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null
}

stop_xray() {
    alive || return 0
    kill "$PID" 2>/dev/null
    i=0
    while [ $i -lt 20 ] && alive; do sleep 0.2; i=$((i + 1)); done
    alive && kill -9 "$PID" 2>/dev/null
    PID=""
}

start_xray() {   # start_xray <файл>
    "$XRAY" run -c "$1" >> "$LOG" 2>&1 &
    PID=$!
    sleep 1
    if alive; then
        ERR=""
        return 0
    fi
    PID=""
    ERR="процесс не удержался, смотри $LOG"
    return 1
}

# Каким способом управления перегрузкой мы пользуемся. Задать его отсюда
# нельзя — контейнер непривилегированный, и /proc/sys только на чтение. Он
# достаётся по наследству от хоста в момент СОЗДАНИЯ контейнера: поменяли на
# хосте потом — сюда это не попадёт до пересоздания.
#
# Поэтому просто показываем. Иначе выяснять, почему у моста cubic при bbr на
# хосте, придётся раскопками.
CC=$(cat /proc/sys/net/ipv4/tcp_congestion_control 2>/dev/null || echo "?")
echo "Мост Xray: управление перегрузкой — $CC"
echo "Мост Xray: жду конфиг в $CONF"

while :; do
    fp="$(fingerprint)"

    if [ -z "$fp" ]; then
        # Конфига ещё нет — это не поломка, а «мастер пока не настроил».
        stop_xray
        ERR=""
        SEEN=""      # забываем виденное: вернувшийся файл надо перечитать
        stamp 0 ""
        sleep "$PERIOD"
        continue
    fi

    if [ "$fp" != "$SEEN" ]; then
        echo "Конфиг изменился, проверяю..."
        if "$XRAY" run -test -c "$CONF" >/tmp/check.log 2>&1; then
            cp "$CONF" "$GOOD"
            stop_xray
            if start_xray "$GOOD"; then
                echo "Мост поднят на новом конфиге."
            else
                echo "Новый конфиг верен, но процесс не встал."
            fi
        else
            ERR="конфиг не принят: $(tail -2 /tmp/check.log | tr '\n' ' ')"
            echo "$ERR"
            # Рабочий процесс не трогаем: он живёт на прежнем конфиге, и людям
            # лучше старый рабочий мост, чем новый неработающий.
        fi
        SEEN="$fp"
    fi

    # Процесс мог упасть сам — поднимаем на последнем принятом конфиге.
    #
    # С отступом: падающий сразу после запуска процесс иначе поднимался бы
    # каждые несколько секунд вечно и завалил бы журнал, похоронив под собой
    # настоящую причину. Отступ растёт до минуты и сбрасывается, как только
    # процесс продержался.
    if ! alive && [ -f "$GOOD" ]; then
        if [ "$(now)" -ge "$RETRY_AT" ]; then
            echo "Процесс не работает — поднимаю заново."
            if start_xray "$GOOD"; then
                BACKOFF=0
                RETRY_AT=0
            else
                if [ "$BACKOFF" -eq 0 ]; then BACKOFF=5; else BACKOFF=$((BACKOFF * 2)); fi
                [ "$BACKOFF" -gt 60 ] && BACKOFF=60
                RETRY_AT=$(( $(now) + BACKOFF ))
                echo "Не встал, следующая попытка через ${BACKOFF} с."
            fi
        fi
    else
        BACKOFF=0
        RETRY_AT=0
    fi

    if alive; then stamp 1 "$fp"; else stamp 0 "$fp"; fi

    # Журнал не должен съесть диск: узел маленький, а мост живёт месяцами.
    if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG" 2>/dev/null || echo 0)" -gt 2000000 ]; then
        tail -c 500000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
    fi

    sleep "$PERIOD"
done
