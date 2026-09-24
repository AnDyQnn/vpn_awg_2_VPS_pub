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
