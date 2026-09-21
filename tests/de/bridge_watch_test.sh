#!/bin/sh
# ЗАПУСК: хост
#
# Мост Xray живёт своим контейнером и слушается не команд, а файла: агент
# кладёт конфиг в общий том, мост подхватывает его сам. Доступа к докеру у него
# нет намеренно — иначе он мог бы трогать соседей, а вся затея в том, чтобы
# каналы не делили судьбу.
#
# Проверяется то, из-за чего связь рвётся по-настоящему:
#
#   1. положили конфиг — мост поднялся;
#   2. положили БИТЫЙ — мост остался работать на прежнем, а причину записал.
#      Это главное: опечатка в генераторе не должна оставлять людей без связи;
#   3. убрали конфиг — мост остановился и не считает себя работающим;
#   4. процесс убили — мост поднял его заново сам.
set -u

IMG=vpn-de-xray-test
NAME=de-xray-watch-test
D="$(cd "$(dirname "$0")" && pwd)/.bridge_stand"
FAIL=0

say()  { printf '%s\n' "$*"; }
ok()   { say "  $1: ок"; }
bad()  { say "  ПРОВАЛ: $1"; FAIL=1; }

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; rm -rf "$D"; }
trap cleanup EXIT

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
rm -rf "$D"; mkdir -p "$D"

# Докер под Windows не понимает путей вида /c/Users — переводим в C:/Users.
# На Linux (в том числе на самой ноде) путь остаётся как есть.
dpath() {
    case "$(uname -s)" in
        MINGW*|MSYS*|CYGWIN*)
            case "$1" in
                /?/*) printf '%s:%s' "$(printf '%s' "$1" | cut -c2)" \
                                     "$(printf '%s' "$1" | cut -c3-)" ;;
                *) printf '%s' "$1" ;;
            esac ;;
        *) printf '%s' "$1" ;;
    esac
}
MNT="$(dpath "$D")"

docker build -q -t "$IMG" "$(dpath "$ROOT")/VPS_DE/xray" >/dev/null

docker run -d --name "$NAME" -e XRAY_WATCH_SECONDS=2 \
    -v "$MNT:/etc/xray" "$IMG" >/dev/null

# Ждём появления состояния — так понятно, что мост вообще ожил.
i=0
while [ $i -lt 20 ] && [ ! -f "$D/status.json" ]; do sleep 1; i=$((i + 1)); done
[ -f "$D/status.json" ] || { bad "мост не подал признаков жизни"; exit 1; }

state() { cat "$D/status.json" 2>/dev/null; }
running() { state | grep -q '"running": 1'; }

say "=== без конфига мост ждёт, а не падает ==="
running && bad "считает себя работающим без конфига" || ok "не работает и не врёт"

say ""
say "=== рабочий конфиг подхватывается сам ==="
cat > "$D/xray.json" <<'EOF'
{
  "log": {"loglevel": "warning"},
  "outbounds": [{"protocol": "freedom", "tag": "out"}]
}
EOF
i=0
while [ $i -lt 25 ] && ! running; do sleep 1; i=$((i + 1)); done
if running; then ok "поднялся"; else bad "не поднялся на верном конфиге"; fi

say ""
say "=== БИТЫЙ конфиг не роняет работающий мост ==="
# Это главная проверка: опечатка в генераторе не должна оставлять людей без
# связи. Мост обязан остаться на прежнем конфиге и назвать причину.
printf '%s' '{"outbounds": [{"protocol": "такого-нет"}]}' > "$D/xray.json"
sleep 8
if running; then
    ok "продолжает работать на прежнем"
else
    bad "лёг из-за битого конфига — люди остались бы без связи"
fi
if state | grep -q '"error": ""'; then
    bad "причина не записана — владелец не поймёт, что случилось"
else
    say "  причина записана: $(state | tr -d '\n' | sed 's/.*"error": "\([^"]*\)".*/\1/' | cut -c1-70)"
    ok "причина видна"
fi

say ""
say "=== процесс убили — мост поднял его заново ==="
cat > "$D/xray.json" <<'EOF'
{
  "log": {"loglevel": "warning"},
  "outbounds": [{"protocol": "freedom", "tag": "out"}]
}
EOF
i=0
while [ $i -lt 25 ] && ! running; do sleep 1; i=$((i + 1)); done
docker exec "$NAME" sh -c 'kill -9 $(pidof xray) 2>/dev/null' >/dev/null 2>&1
sleep 8
if running; then ok "поднялся сам"; else bad "остался лежать"; fi

say ""
say "=== конфиг убрали — мост остановился ==="
rm -f "$D/xray.json"
sleep 8
if running; then bad "работает без конфига"; else ok "остановился"; fi

say ""
say "=== конфиг вернули — мост поднялся снова ==="
# Мост помнит, какой файл он уже видел. Если после удаления это не забыть,
# вернувшийся конфиг может показаться тем же самым, и мост останется лежать.
cat > "$D/xray.json" <<'EOF'
{
  "log": {"loglevel": "warning"},
  "outbounds": [{"protocol": "freedom", "tag": "out"}]
}
EOF
i=0
while [ $i -lt 25 ] && ! running; do sleep 1; i=$((i + 1)); done
if running; then ok "поднялся после возврата"; else bad "не заметил вернувшийся конфиг"; fi

say ""
say "=== состояние остаётся читаемым даже после ошибки ==="
# Текст ошибки идёт в файл состояния, который читает агент. Кавычка или слэш
# внутри сообщения порвали бы его — и агент перестал бы понимать состояние
# вовсе, то есть мост выглядел бы мёртвым не из-за поломки, а из-за жалобы.
printf '%s' '{"outbounds": [{"protocol": "C:\\путь\"кавычка"}]}' > "$D/xray.json"
sleep 8
# Путь отдаём в том же виде, что и докеру: под Windows обычный интерпретатор
# не понимает путей вида /c/Users, и проверка падала бы на ровном месте.
JSONCHECK='import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))'
if python3 -c "$JSONCHECK" "$MNT/status.json" 2>/dev/null    || python -c "$JSONCHECK" "$MNT/status.json" 2>/dev/null; then
    ok "состояние разбирается"
else
    say "  содержимое: $(cat "$D/status.json" | tr -d '\n' | cut -c1-200)"
    bad "состояние перестало быть читаемым после ошибки"
fi
if running; then ok "мост при этом продолжает работать"; else bad "лёг из-за битого конфига"; fi

say ""
if [ "$FAIL" = "0" ]; then say "ВСЁ ПРОШЛО"; else say "ЕСТЬ ПРОВАЛЫ"; fi
