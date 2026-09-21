#!/bin/bash
# Сторож узла: следит за тем, что туннель действительно живой, и лечит по нарастающей.
#
# ПОЧЕМУ ОТДЕЛЬНОЙ СЛУЖБОЙ НА ХОСТЕ, А НЕ В БОТЕ.
# Раньше за здоровьем следил сам бот. Если контейнер бота лежал — лечить было некому,
# то есть сторож умирал вместе с тем, что должен сторожить. Здесь служба systemd:
# она переживает падение любого контейнера и поднимается сама после перезагрузки.
#
# ПОЧЕМУ СТАРАЯ ПРОВЕРКА НИЧЕГО НЕ ПРОВЕРЯЛА.
# Проверкой здоровья было `ip link show wg0` — то есть ответ «жив» означал всего лишь
# «интерфейс существует». Зависший туннель с поднятым интерфейсом такую проверку
# проходит всегда, а виснет он обычно именно так.
#
# ЧТО СМОТРИМ ВМЕСТО ЭТОГО (любой сбой = повод лечить):
#   1. контейнер запущен;
#   2. панель отвечает;
#   3. рукопожатие с соседним узлом свежее — туннель между нодами постоянный и обязан
#      обновляться каждые пару минут, это самый честный признак живого канала;
#   4. правила маршрутизации на месте: метка, правило и таблица;
#   5. списки маршрутизации не пустые.
#
# ЛЕСТНИЦА ЛЕЧЕНИЯ — с нарастающей паузой, а не одно и то же каждые девять минут:
#   L1 перезалить правила → L2 перезапустить контейнер → L3 перезапустить docker →
#   L4 перезагрузить хост (не чаще раза в 6 часов).
# Состояние и журнал попыток лежат в volumes/flags — бот читает их и показывает историю
# вместо одинаковых уведомлений.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_DIR="${WATCHDOG_NODE_DIR:-$(dirname "$SCRIPT_DIR")}"
FLAGS_DIR="$NODE_DIR/volumes/flags"
STATE="$FLAGS_DIR/watchdog.json"
LOGF="$FLAGS_DIR/watchdog.log"

INTERVAL="${WATCHDOG_INTERVAL:-30}"        # секунд между проверками
FAILS_TO_ACT=2                              # столько подряд неудач — начинаем лечить
HANDSHAKE_MAX_AGE=240                       # свежесть рукопожатия с соседним узлом, сек
REBOOT_COOLDOWN=$((6 * 3600))               # не чаще раза в шесть часов

mkdir -p "$FLAGS_DIR"

if [ -f "$NODE_DIR/docker-compose.yml" ] && grep -q "ru_wireguard" "$NODE_DIR/docker-compose.yml" 2>/dev/null; then
    CONTAINER="vpn_wireguard"; SERVICE="ru_wireguard"; PEER_IP="10.13.13.254"
    IS_MASTER=1
else
    CONTAINER="de_vpn_agent";  SERVICE="de_wireguard"; PEER_IP="10.13.13.1"
    IS_MASTER=0
fi

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOGF"; }

trim_log() {
    # журнал не должен расти бесконечно на диске в 10 ГБ
    if [ -f "$LOGF" ] && [ "$(wc -l < "$LOGF")" -gt 2000 ]; then
        tail -n 500 "$LOGF" > "$LOGF.tmp" && mv "$LOGF.tmp" "$LOGF"
    fi
}

# --- проверки ------------------------------------------------------------
check_container() {
    [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" = "true" ]
}

check_api() {
    docker exec "$CONTAINER" curl -sf --max-time 5 http://127.0.0.1:8000/api/health >/dev/null 2>&1
}

check_handshake() {
    # Постоянный туннель между узлами: рукопожатие обязано освежаться. Если ему больше
    # четырёх минут — канал мёртв, каким бы живым ни выглядел интерфейс.
    local dump age now
    dump=$(docker exec "$CONTAINER" wg show wg0 dump 2>/dev/null | tail -n +2)
    [ -z "$dump" ] && return 1
    now=$(date +%s)
    age=$(echo "$dump" | awk -F'\t' -v ip="$PEER_IP" -v now="$now" '
        index($4, ip) > 0 { if ($5 > 0) print now - $5; else print 999999 }' | head -1)
    [ -z "$age" ] && return 0          # соседний узел ещё не заведён — не наша беда
    [ "$age" -lt "$HANDSHAKE_MAX_AGE" ]
}

# Дальше проверки расходятся: узлы делают разную работу, и мерить их одной
# меркой нельзя. Мастер заворачивает мир-трафик в Германию — у него метка,
# таблица 200 и списки сетей. Немецкий узел сам и есть выход: ничего этого у
# него нет и быть не должно, там своя пара признаков жизни.
check_routing() {
    [ "$IS_MASTER" = "1" ] || return 0
    docker exec "$CONTAINER" sh -c '
        ip rule show 2>/dev/null | grep -q "fwmark 0xc8\|fwmark 200" || exit 1
        ip route show table 200 2>/dev/null | grep -q "dev wg0" || exit 1
        exit 0' >/dev/null 2>&1
}

# Охрана порта подписки. Не «проблема», а восстановление: правила живут в
# цепочке DOCKER-USER, а её стирает любой перезапуск демона докера — в том
# числе тот, который делает этот же сторож третьей ступенью лечения. Без этой
# проверки порт остался бы открытым настежь до следующего тика таймера
# продления, то есть до полусуток.
#
# Возвращаем молча и сразу: ступени лечения тут ни при чём, чинится это одной
# командой и никого не трогает.
ensure_subguard() {
    [ "$IS_MASTER" = "1" ] || return 0
    # Нет сертификата — подписка наружу не открыта, и охранять нечего.
    [ -s "$NODE_DIR/volumes/certs/fullchain.pem" ] || return 0
    iptables -C DOCKER-USER -j VPN_SUB 2>/dev/null && return 0
    log "Охрана порта подписки пропала из DOCKER-USER — возвращаю"
    bash "$SCRIPT_DIR/public_sub.sh" firewall "$NODE_DIR" >/dev/null 2>&1
}

# Мост Xray на Германии — отдельный контейнер, и он не должен лежать молча.
#
# Лечим его ОТДЕЛЬНО от узла и не даём влиять на решение о лечении самого узла:
# упавший мост означает, что люди на Xray идут прежним путём через общий
# туннель, — это неприятно, но связь у них есть. Ронять из-за него весь узел
# было бы лекарством хуже болезни.
#
# Мастер этой проверки не касается: моста там нет.
check_bridge() {
    [ "$IS_MASTER" = "0" ] || return 0
    # Контейнера нет вовсе — значит канал не разворачивали, сторожить нечего.
    docker inspect de_vpn_xray >/dev/null 2>&1 || return 0
    [ "$(docker inspect -f '{{.State.Running}}' de_vpn_xray 2>/dev/null)" = "true" ] \
        && return 0
    log "Мост Xray не работает — поднимаю"
    docker start de_vpn_xray >/dev/null 2>&1 || true
}

check_ipsets() {
    [ "$IS_MASTER" = "1" ] || return 0
    local n
    n=$(docker exec "$CONTAINER" sh -c 'ipset list ru_nets 2>/dev/null | grep -c "^[0-9]"' 2>/dev/null)
    [ "${n:-0}" -gt 100 ]
}

# Немецкий узел: адрес в туннеле на месте и есть подмена адреса на выходе.
# Если пропало одно из двух, люди остаются без интернета, хотя туннель на вид
# живой, — это и стоит ловить вместо чужих проверок.
check_exit() {
    [ "$IS_MASTER" = "0" ] || return 0
    docker exec "$CONTAINER" sh -c '
        ip -4 addr show wg0 2>/dev/null | grep -q "inet " || exit 1
        iptables -t nat -S POSTROUTING 2>/dev/null | grep -q "MASQUERADE" || exit 1
        exit 0' >/dev/null 2>&1
}

# --- лечение -------------------------------------------------------------
heal_reload_rules() {
    log "L1: перезаливаю правила через панель"
    docker exec "$CONTAINER" curl -sf --max-time 10 -X POST http://127.0.0.1:8000/api/reload >/dev/null 2>&1
}

heal_restart_container() {
    log "L2: перезапускаю контейнер $CONTAINER"
    cd "$NODE_DIR" && docker compose restart "$SERVICE" >/dev/null 2>&1
}

heal_restart_docker() {
    log "L3: перезапускаю docker"
    systemctl restart docker >/dev/null 2>&1
}

heal_reboot() {
    local last now
    now=$(date +%s)
    last=$(cat "$FLAGS_DIR/watchdog.last_reboot" 2>/dev/null || echo 0)
    if [ $((now - last)) -lt "$REBOOT_COOLDOWN" ]; then
        log "L4: перезагрузка пропущена — прошлая была меньше шести часов назад"
        return 1
    fi
    echo "$now" > "$FLAGS_DIR/watchdog.last_reboot"
    log "L4: перезагружаю хост"
    /usr/sbin/reboot
}

write_state() {
    cat > "$STATE" <<JSON
{
  "ts": $(date +%s),
  "node": "$(basename "$NODE_DIR")",
  "healthy": $1,
  "problem": "$2",
  "fails": $3,
  "level": $4,
  "last_action": "$5"
}
JSON
}

# --- основной цикл -------------------------------------------------------
fails=0
level=0
last_action="нет"
log "Сторож запущен: узел $(basename "$NODE_DIR"), контейнер $CONTAINER, сосед $PEER_IP"

while true; do
    problem=""
    if ! check_container; then problem="контейнер не запущен"
    elif ! check_api;     then problem="панель не отвечает"
    elif ! check_handshake; then problem="нет свежего рукопожатия с соседним узлом"
    elif ! check_routing; then problem="потеряны правила маршрутизации"
    elif ! check_ipsets;  then problem="списки маршрутизации пусты"
    elif ! check_exit;    then problem="узел не выпускает трафик наружу"
    fi

    if [ -z "$problem" ]; then
        check_bridge
        if [ "$fails" -gt 0 ] || [ "$level" -gt 0 ]; then
            log "Восстановлено. Проверки снова проходят."
        fi
        fails=0; level=0; last_action="нет"
        write_state true "" 0 0 "$last_action"
    else
        fails=$((fails + 1))
        log "Проблема: $problem (подряд: $fails)"
        if [ "$fails" -ge "$FAILS_TO_ACT" ]; then
            level=$((level + 1))
            case "$level" in
                1) heal_reload_rules;    last_action="перезалиты правила" ;;
                2) heal_restart_container; last_action="перезапущен контейнер" ;;
                3) heal_restart_docker;  last_action="перезапущен docker" ;;
                *) heal_reboot && last_action="перезагрузка хоста" || last_action="перезагрузка отложена"
                   level=3 ;;      # дальше четвёртого не поднимаемся
            esac
            fails=0
            # Пауза растёт со ступенью: не долбим одним и тем же каждые полминуты.
            sleep $((INTERVAL * level * 2))
        fi
        write_state false "$problem" "$fails" "$level" "$last_action"
    fi

    ensure_subguard

    trim_log
    sleep "$INTERVAL"
done
