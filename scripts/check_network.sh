#!/bin/bash
# Проверка сети узла — одна команда, чтобы понять, где порвалось.
#
#   bash scripts/check_network.sh          — узел определится сам (RU или DE)
#   bash scripts/check_network.sh ru|de    — указать явно
#
# Ничего не меняет: только смотрит и пишет ✅ / ⚠️ / ❌ по каждому пункту.
# Идёт снизу вверх — хост, файрвол, контейнеры, туннель, выход в мир, — чтобы
# первая же красная строка показывала место обрыва.

set -u

if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите с правами root: sudo bash $0"
    exit 1
fi

OK=0; WARN=0; FAIL=0
ok()   { echo "  ✅ $*"; OK=$((OK+1)); }
warn() { echo "  ⚠️ $*"; WARN=$((WARN+1)); }
fail() { echo "  ❌ $*"; FAIL=$((FAIL+1)); }
section() { echo ""; echo "── $* ──"; }

running() { [ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" = "true" ]; }

NODE="${1:-}"
if [ -z "$NODE" ]; then
    if docker inspect vpn_wireguard >/dev/null 2>&1; then NODE=ru
    elif docker inspect de_vpn_agent >/dev/null 2>&1; then NODE=de
    else
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        ROOT_DIR="$(dirname "$SCRIPT_DIR")"
        if [ -f "$ROOT_DIR/VPS_RU/.env" ]; then NODE=ru
        elif [ -f "$ROOT_DIR/VPS_DE/.env" ]; then NODE=de
        fi
    fi
fi
case "$NODE" in
    ru|RU) NODE=ru; WG=vpn_wireguard ;;
    de|DE) NODE=de; WG=de_vpn_agent ;;
    *) echo "❌ Не понял, какой это узел. Укажите явно: bash $0 ru|de"; exit 1 ;;
esac
echo "🔎 Проверка сети узла: $(echo "$NODE" | tr a-z A-Z)  ($(hostname), $(date '+%F %T'))"

# ───────────────────────── Хост ─────────────────────────
section "Хост"
DEF_IF=$(ip -4 route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev"){print $(i+1); exit}}')
if [ -n "$DEF_IF" ]; then
    ok "Маршрут по умолчанию: через $DEF_IF ($(ip -4 route show default | awk '{print $3; exit}'))"
else
    fail "Нет маршрута по умолчанию — сервер не знает, куда слать трафик"
fi

if ping -c 2 -W 2 1.1.1.1 >/dev/null 2>&1 || ping -c 2 -W 2 8.8.8.8 >/dev/null 2>&1; then
    ok "Пинг наружу (1.1.1.1 / 8.8.8.8) проходит"
else
    warn "Пинг наружу не проходит (ICMP могут резать — смотрите строки ниже)"
fi

if getent hosts github.com >/dev/null 2>&1; then
    ok "DNS на хосте работает (github.com резолвится)"
else
    fail "DNS на хосте не работает: github.com не резолвится (/etc/resolv.conf)"
fi

HOST_IP=$(curl -4 -s --max-time 6 https://api.ipify.org 2>/dev/null)
if [ -n "$HOST_IP" ]; then
    ok "HTTPS наружу работает, внешний адрес хоста: $HOST_IP"
else
    fail "HTTPS наружу с хоста не проходит"
fi

GH=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://github.com 2>/dev/null)
case "$GH" in
    2*|3*) ok "GitHub доступен (HTTP $GH) — обновления скачаются" ;;
    *)     warn "GitHub с хоста не отвечает (HTTP ${GH:-нет}) — обновления не скачаются" ;;
esac

if [ "$(sysctl -n net.ipv4.ip_forward 2>/dev/null)" = "1" ]; then
    ok "Пересылка пакетов на хосте включена (ip_forward=1)"
else
    warn "ip_forward=0 на хосте (контейнер включает свой, но Docker обычно ставит 1 сам)"
fi

MODS=$(lsmod 2>/dev/null | awk 'NR>1{print $1}')
MISS=""
# Узлам нужны разные модули: российский метит и сортирует трафик по спискам,
# немецкий только выпускает его наружу.
if [ "$NODE" = "ru" ]; then
    NEED_MODS="ip_tables iptable_filter iptable_nat iptable_mangle ip_set xt_set xt_mark xt_conntrack"
else
    NEED_MODS="ip_tables iptable_filter iptable_nat iptable_mangle xt_MASQUERADE"
fi
for M in $NEED_MODS; do
    echo "$MODS" | grep -qx "$M" || MISS="$MISS $M"
done
if [ -z "$MISS" ]; then
    ok "Модули файрвола ядра загружены"
else
    warn "Не загружены модули ядра:$MISS (их грузит ensure_host_maintenance.sh)"
fi

# ───────────────────────── SSH и файрвол ─────────────────────────
section "SSH и файрвол"
if [ -x /usr/sbin/sshd ]; then
    SSH_P=$(sshd -T 2>/dev/null | awk '/^port /{print $2; exit}')
    SSH_P=${SSH_P:-22}
    if ss -ltnH "sport = :$SSH_P" 2>/dev/null | grep -q .; then
        ok "SSH слушает порт $SSH_P"
    else
        fail "SSH настроен на порт $SSH_P, но его никто не слушает"
    fi
else
    fail "OpenSSH не установлен — доступ только из консоли хостера"
fi

if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
    # Порт VPN публикует Docker, и его правила стоят раньше ufw: пакеты на
    # 51820/udp до ufw не доходят. Правило в ufw не нужно и ничего не решает.
    ok "ufw включён (51820/udp пропускает Docker мимо ufw)"
    if [ -n "${SSH_P:-}" ] && ! ufw status 2>/dev/null | grep -qE "^$SSH_P(/tcp)? "; then
        warn "ufw включён, а порт SSH $SSH_P в нём не открыт"
    fi
else
    ok "ufw выключен — порты не режутся на хосте"
fi

if ss -lunH "sport = :51820" 2>/dev/null | grep -q . || iptables -t nat -S DOCKER 2>/dev/null | grep -q "dport 51820"; then
    ok "Порт VPN 51820/udp проброшен в контейнер"
else
    fail "Порт 51820/udp никто не слушает и он не проброшен"
fi

# ───────────────────────── Контейнеры ─────────────────────────
section "Контейнеры"
if ! systemctl is-active --quiet docker 2>/dev/null; then
    fail "Docker не запущен"
fi
if [ "$NODE" = "ru" ]; then CONTAINERS="vpn_wireguard vpn_bot vpn_db"; else CONTAINERS="de_vpn_agent"; fi
for C in $CONTAINERS; do
    if running "$C"; then
        RC=$(docker inspect -f '{{.RestartCount}}' "$C" 2>/dev/null)
        UP=$(docker inspect -f '{{.State.StartedAt}}' "$C" 2>/dev/null | cut -c1-19 | tr T ' ')
        if [ "$(docker inspect -f '{{.State.Restarting}}' "$C" 2>/dev/null)" = "true" ]; then
            fail "$C перезапускается по кругу (рестартов: $RC)"
        else
            ok "$C работает (с $UP UTC, рестартов: $RC)"
        fi
    else
        fail "$C не запущен"
    fi
done

if ! running "$WG"; then
    echo ""
    echo "Контейнер туннеля не работает — дальше проверять нечего."
    echo "Смотрите: docker logs --tail 50 $WG"
    echo ""
    echo "Итог: ✅ $OK  ⚠️ $WARN  ❌ $FAIL"
    exit 1
fi

X() { docker exec "$WG" sh -c "$1" 2>/dev/null; }

H=$(X 'curl -s --max-time 4 http://127.0.0.1:8000/api/health')
if echo "$H" | grep -q '"ok"\|"status"'; then
    ok "API узла отвечает"
else
    fail "API узла (127.0.0.1:8000 в контейнере) не отвечает"
fi

if [ "$NODE" = "ru" ] && running vpn_db; then
    if docker exec vpn_db pg_isready -q 2>/dev/null; then
        ok "База данных принимает соединения"
    else
        fail "База данных не принимает соединения"
    fi
fi

# ───────────────────────── Туннель ─────────────────────────
section "Туннель (wg0)"
if ! X 'wg show wg0' >/dev/null; then
    fail "Интерфейс wg0 не поднят"
else
    PEERS=$(X 'wg show wg0 peers' | grep -c .)
    LISTEN=$(X 'wg show wg0 listen-port')
    ok "wg0 поднят, порт $LISTEN, пиров: $PEERS"

    NOW=$(date +%s)
    # Пир-партнёр: на RU это Германия (10.13.13.254), на DE — российский узел.
    if [ "$NODE" = "ru" ]; then
        PARTNER=$(X 'wg show wg0 allowed-ips' | awk '/10\.13\.13\.254\/32/{print $1; exit}')
        PNAME="Германия"
    else
        PARTNER=$(X 'wg show wg0 peers' | head -1)
        PNAME="российский узел"
    fi
    if [ -z "$PARTNER" ]; then
        fail "Пира «$PNAME» в wg0 нет — узлы не связаны"
    else
        HS=$(X 'wg show wg0 latest-handshakes' | awk -v p="$PARTNER" '$1==p{print $2}')
        HS=${HS:-0}
        AGE=$((NOW - HS))
        if [ "$HS" = "0" ]; then
            fail "С «$PNAME» не было ни одного рукопожатия"
        elif [ "$AGE" -le 180 ]; then
            ok "Рукопожатие с «$PNAME» ${AGE} с назад"
        else
            fail "Последнее рукопожатие с «$PNAME» $((AGE/60)) мин назад — связь между узлами пропала"
        fi
        TR=$(X 'wg show wg0 transfer' | awk -v p="$PARTNER" '$1==p{printf "%.1f МБ принято, %.1f МБ отправлено", $2/1048576, $3/1048576}')
        [ -n "$TR" ] && echo "     $TR"
    fi

    if [ "$NODE" = "ru" ]; then
        PEER_IP=10.13.13.254
    else
        PEER_IP=10.13.13.1
    fi
    if X "ping -c 2 -W 2 $PEER_IP" >/dev/null; then
        ok "Пинг до «$PNAME» по туннелю ($PEER_IP) проходит"
    else
        warn "Пинг до $PEER_IP по туннелю не проходит"
    fi

    ACTIVE=$(X 'wg show wg0 latest-handshakes' | awk -v n="$NOW" '$2>0 && n-$2<=180' | grep -c .)
    echo "     Активных клиентов за 3 мин: $ACTIVE"
fi

if [ "$(X 'sysctl -n net.ipv4.ip_forward')" = "1" ]; then
    ok "Пересылка пакетов в контейнере включена"
else
    fail "ip_forward=0 в контейнере — клиенты не выйдут в сеть"
fi

if X 'iptables -t nat -S POSTROUTING' | grep -q MASQUERADE; then
    ok "NAT (MASQUERADE) настроен"
else
    fail "Нет NAT (MASQUERADE) — трафик клиентов не выйдет наружу"
fi

# ───────────────────────── Маршрутизация ─────────────────────────
if [ "$NODE" = "ru" ]; then
    section "Маршрутизация RU → DE"
    for S in ru_nets blocked_nets; do
        N=$(X "ipset list -t $S" | awk '/Number of entries/{print $4}')
        N=${N:-0}
        if [ "$N" -ge 100 ]; then
            ok "Список $S: $N сетей"
        elif [ "$S" = "ru_nets" ]; then
            fail "Список ru_nets почти пуст ($N) — российские сайты пойдут через Германию"
        else
            warn "Список $S почти пуст ($N)"
        fi
    done

    if X 'ip rule' | grep -q "fwmark 0xc8 lookup 200"; then
        ok "Правило маршрутизации по метке 200 есть"
    else
        fail "Нет правила «fwmark 200 → table 200» — мир не пойдёт в Германию"
    fi
    T200=$(X 'ip route show table 200' | head -1)
    case "$T200" in
        *"dev wg0"*) ok "Таблица 200: мир уходит в туннель ($T200)" ;;
        "")          fail "Таблица 200 пуста" ;;
        *)           warn "Таблица 200: $T200 — мир идёт напрямую, не через Германию (режим обхода?)" ;;
    esac

    OUT_IP=$(X 'curl -4 -s --max-time 8 https://api.ipify.org')
    if [ -z "$OUT_IP" ]; then
        fail "Из контейнера мир недоступен — через Германию не выходит"
    elif [ -n "$HOST_IP" ] && [ "$OUT_IP" = "$HOST_IP" ]; then
        warn "Мир из контейнера выходит с адреса самого узла ($OUT_IP), а не через Германию"
    else
        ok "Мир выходит через Германию (внешний адрес: $OUT_IP)"
    fi

    TG=$(X "curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://api.telegram.org")
    case "$TG" in
        2*|3*|4*) ok "Telegram API доступен (HTTP $TG) — бот достучится" ;;
        *)        fail "Telegram API недоступен (HTTP ${TG:-нет}) — бот не работает" ;;
    esac

    YA=$(X "curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://ya.ru")
    case "$YA" in
        2*|3*) ok "Российские сайты открываются напрямую (ya.ru, HTTP $YA)" ;;
        *)     warn "ya.ru из контейнера не открылся (HTTP ${YA:-нет})" ;;
    esac

    # Бот в цикле перезапусков уже отмечен выше, а зайти в него нельзя —
    # без этой оговорки та же беда второй раз выдавалась за «нет базы».
    if running vpn_bot && [ "$(docker inspect -f '{{.State.Restarting}}' vpn_bot 2>/dev/null)" != "true" ]; then
        if docker exec vpn_bot python -c "import socket; socket.create_connection(('172.20.0.5', 5432), 3)" 2>/dev/null; then
            ok "Бот видит базу (172.20.0.5:5432)"
        else
            fail "Бот не достаёт до базы 172.20.0.5:5432"
        fi
    fi
else
    section "Выход в мир (DE)"
    OUT_IP=$(X 'curl -4 -s --max-time 8 https://api.ipify.org')
    if [ -n "$OUT_IP" ]; then
        ok "Из контейнера мир доступен (внешний адрес: $OUT_IP)"
    else
        fail "Из контейнера мир недоступен"
    fi
    TG=$(X "curl -s -o /dev/null -w '%{http_code}' --max-time 8 https://api.telegram.org")
    case "$TG" in
        2*|3*|4*) ok "Telegram API доступен (HTTP $TG)" ;;
        *)        fail "Telegram API недоступен (HTTP ${TG:-нет})" ;;
    esac
fi

echo ""
echo "════════════════════════════════════"
echo "Итог: ✅ $OK  ⚠️ $WARN  ❌ $FAIL"
if [ "$FAIL" -gt 0 ]; then
    echo "Начинайте с первой ❌ сверху — остальные часто её следствие."
    exit 1
fi
exit 0
