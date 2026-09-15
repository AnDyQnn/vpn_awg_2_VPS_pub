#!/bin/sh
# Прогон тестов проекта.
#
#   tests/run.sh              — бот, узел и Германия
#   tests/run.sh bot          — только бот (нужна база, поднимется сама)
#   tests/run.sh node         — только узел (нужен привилегированный контейнер)
#   tests/run.sh de           — только агент Германии
#   tests/run.sh contract     — сверка базы с узлом, на стенде из двух контейнеров
#   tests/run.sh bot verdict_test.py ...   — выборочно
#   tests/run.sh -f bot       — пересоздать базу с нуля
#
# Тесты бота гоняются в образе бота на одноразовой базе: настоящий код,
# настоящие запросы, чистые данные каждый раз. Тесты узла — в привилегированном
# контейнере с настоящим iptables, каждый в своём, чтобы правила одного не
# достались другому.
#
# Проверки контракта живут отдельно, в scripts/node_contract.sh: они не
# поднимают ничего, а смотрят на УЖЕ работающий узел, поэтому запускаются на
# самой ноде — из аудита и из недельной уборки.
set -e
export MSYS_NO_PATHCONV=1

TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$TESTS_DIR")"

# Докер под Windows не понимает путей вида /c/Users — переводим в C:/Users.
# На Linux (в том числе на самой ноде) возвращаем путь как есть.
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
        dpath() {
            case "$1" in
                /?/*) printf '%s:%s' "$(printf '%s' "$1" | cut -c2)" "$(printf '%s' "$1" | cut -c3-)" ;;
                *) printf '%s' "$1" ;;
            esac
        } ;;
    *)
        dpath() { printf '%s' "$1"; } ;;
esac

FRESH=""
if [ "$1" = "-f" ]; then FRESH=1; shift; fi

WHAT="${1:-all}"
case "$WHAT" in bot|node|de|contract|all) shift 2>/dev/null || true;; *) WHAT="all";; esac

PASS=0
FAIL=0
FAILED=""

report() {   # report <имя> <вывод>
    if printf '%s' "$2" | grep -qE "ВСЁ ПРОШЛО|ВСЕ ПРОШЛО"; then
        PASS=$((PASS + 1)); echo "  прошёл  $1"
    else
        FAIL=$((FAIL + 1)); FAILED="$FAILED $1"
        echo "  УПАЛ    $1"
        # Сначала то, ради чего сюда смотрят: сами провалы и обрыв кода.
        # Хвост из шести строк прятал их, если тест успевал напечатать что-то
        # после — и приходилось перезапускать его вручную, чтобы увидеть.
        FOUND=$(printf '%s' "$2" | grep -E "ПРОВАЛ|Traceback|Error|error:" | head -12)
        if [ -n "$FOUND" ]; then
            printf '%s
' "$FOUND" | sed 's/^/          /'
        else
            # Сначала то, ради чего сюда смотрят: сами провалы и обрыв кода.
        # Хвост из шести строк прятал их, если тест успевал напечатать что-то
        # после, и приходилось перезапускать тест вручную, чтобы увидеть.
        FOUND=$(printf '%s' "$2" | grep -E "ПРОВАЛ|Traceback|Error|error:" | head -12)
        if [ -n "$FOUND" ]; then
            printf '%s
' "$FOUND" | sed 's/^/          /'
        else
            printf '%s' "$2" | tail -6 | sed 's/^/          /'
        fi
        fi
    fi
}

# ---------------------------------------------------------------- бот -----
run_bot() {
    [ -n "$FRESH" ] && docker rm -f vpntest-db >/dev/null 2>&1 || true
    docker network inspect vpntest >/dev/null 2>&1 || docker network create vpntest >/dev/null
    if ! docker ps --format '{{.Names}}' | grep -qx vpntest-db; then
        docker rm -f vpntest-db >/dev/null 2>&1 || true
        docker run -d --name vpntest-db --network vpntest \
            -e POSTGRES_USER=vpn -e POSTGRES_PASSWORD=vpnpass -e POSTGRES_DB=vpndb \
            -v "$(dpath "$ROOT")/VPS_RU/db/init.sql:/docker-entrypoint-initdb.d/init.sql" \
            postgres:15-alpine >/dev/null
        printf '  жду базу'
        i=0
        while [ $i -lt 60 ]; do
            docker exec vpntest-db pg_isready -U vpn -d vpndb >/dev/null 2>&1 && break
            printf '.'; sleep 1; i=$((i + 1))
        done
        sleep 2; echo ' готова'
    fi
    docker build -q -t vpn-bot-test "$(dpath "$ROOT")/VPS_RU/bot" >/dev/null

    mkdir -p "$TESTS_DIR/out"
    for t in "$@"; do
        out=$(docker run --rm --network vpntest --entrypoint python3 \
            -e DATABASE_URL=postgres://vpn:vpnpass@vpntest-db:5432/vpndb \
            -e BOT_TOKEN=test -e ADMIN_ID=1 \
            -v "$(dpath "$TESTS_DIR")/bot/$t:/app/$t" \
            -v "$(dpath "$ROOT")/VPS_RU/ru_wg_api/dnsfilter.py:/app/node_dnsfilter.py" \
            -v "$(dpath "$TESTS_DIR")/out:/out" \
            -v "$(dpath "$TESTS_DIR")/contract/node_contract.py:/app/node_contract.py" \
            -v "$(dpath "$ROOT")/CHANGELOG.md:/app/CHANGELOG.md" \
            -v "$(dpath "$ROOT")/VERSION:/app/VERSION_FILE" \
            vpn-bot-test "/app/$t" 2>&1) || true
        report "$t" "$out"
    done
}

# --------------------------------------------------------------- узел -----
run_node() {
    docker build -q -t vpn-wg-test "$(dpath "$ROOT")/VPS_RU/ru_wg_api" >/dev/null
    for t in "$@"; do
        out=$(docker run --rm --privileged --entrypoint sh \
            -v "$(dpath "$TESTS_DIR")/node/$t:/t.py" vpn-wg-test \
            -c "apk add --no-cache -q curl >/dev/null 2>&1;                 PY=/opt/venv/bin/python3; [ -x \$PY ] || PY=python3;                 \$PY /t.py" 2>&1) || true
        report "$t" "$out"
    done
}

# ------------------------------------------------------------ Германия ----
run_de() {
    docker build -q -t vpn-de-test "$(dpath "$ROOT")/VPS_DE/de_agent_api" >/dev/null
    for t in "$@"; do
        # Способ запуска написан в самом файле, второй строкой.
        if head -3 "$TESTS_DIR/de/$t" | grep -q "ЗАПУСК: хост"; then
            out=$(cd "$TESTS_DIR/de" && sh "./$t" 2>&1) || true
        else
            case "$t" in
                *.py) cmd="/opt/venv/bin/python3 -m pip install -q httpx 2>/dev/null; /opt/venv/bin/python3 /t" ;;
                *)    cmd="apk add --no-cache -q curl iptables >/dev/null 2>&1; sh /t" ;;
            esac
            out=$(docker run --rm --privileged --entrypoint sh                 -v "$(dpath "$TESTS_DIR")/de/$t:/t" vpn-de-test -c "$cmd" 2>&1) || true
        fi
        report "$t" "$out"
    done
}

if [ "$WHAT" = "bot" ] || [ "$WHAT" = "all" ]; then
    echo "=== тесты бота ==="
    if [ $# -gt 0 ] && [ "$WHAT" = "bot" ]; then
        run_bot "$@"
    else
        run_bot $(cd "$TESTS_DIR/bot" && ls *.py)
    fi
fi

if [ "$WHAT" = "node" ] || [ "$WHAT" = "all" ]; then
    echo "=== тесты узла ==="
    if [ $# -gt 0 ] && [ "$WHAT" = "node" ]; then
        run_node "$@"
    else
        run_node $(cd "$TESTS_DIR/node" && ls *.py)
    fi
fi

# ------------------------------------------------------------ сверка -----
run_contract() {
    docker build -q -t vpn-wg-test "$(dpath "$ROOT")/VPS_RU/ru_wg_api" >/dev/null
    docker build -q -t vpn-bot-test "$(dpath "$ROOT")/VPS_RU/bot" >/dev/null
    docker rm -f ctr-node >/dev/null 2>&1 || true
    docker run -d --name ctr-node --privileged --network vpntest         -e API_TOKEN= vpn-wg-test >/dev/null
    i=0
    while [ $i -lt 30 ]; do
        docker exec ctr-node curl -sf --max-time 2             http://127.0.0.1:8000/api/health >/dev/null 2>&1 && break
        sleep 1; i=$((i + 1))
    done
    # Сетевое пространство общее с узлом — так же, как в боевом compose.
    out=$(docker run --rm --network container:ctr-node --entrypoint python3         -e DATABASE_URL=postgres://vpn:vpnpass@vpntest-db:5432/vpndb         -e BOT_TOKEN=test -e ADMIN_ID=1         -e WG_API_URL=http://127.0.0.1:8000/api         -v "$(dpath "$TESTS_DIR")/contract/node_contract.py:/app/node_contract.py"         vpn-bot-test /app/node_contract.py 2>&1) || true
    docker rm -f ctr-node >/dev/null 2>&1 || true
    echo "$out" | grep -E '^(ok|warning|error)\|' | sed 's/^/    /'
    if echo "$out" | grep -qE '^(ok|warning|error)\|'; then
        report "сверка отвечает" "ВСЁ ПРОШЛО"
    else
        report "сверка отвечает" "$out"
    fi
}

if [ "$WHAT" = "de" ] || [ "$WHAT" = "all" ]; then
    echo "=== тесты агента Германии ==="
    if [ $# -gt 0 ] && [ "$WHAT" = "de" ]; then
        run_de "$@"
    else
        run_de $(cd "$TESTS_DIR/de" && ls *.py *.sh 2>/dev/null)
    fi
fi

if [ "$WHAT" = "contract" ] || [ "$WHAT" = "all" ]; then
    echo "=== сверка базы с узлом (стенд) ==="
    run_contract
fi

echo "------------------------------------"
echo "прошло: $PASS, упало: $FAIL"
[ "$FAIL" -gt 0 ] && { echo "упали:$FAILED"; exit 1; }
exit 0
