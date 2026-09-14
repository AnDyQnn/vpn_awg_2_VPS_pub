#!/bin/sh
# ЗАПУСК: внутри контейнера агента (привилегированный)
# Проверка ровно того, на чём споткнулся сторож на боевом узле:
# панель должна отвечать по петле и отдавать /api/health без токена,
# оставаясь закрытой для всех остальных.
#
# Внешнюю сторону этот скрипт намеренно не проверяет: запрос с локального
# адреса на локальный идёт через петлю, поэтому «чужим» его изобразить нельзя.
# Настоящую проверку снаружи делает de_outside_test.sh — из соседнего контейнера.
set -e
export API_TOKEN=secret-for-test

# Правила ставим точно так же, как их ставит run_api.sh на узле.
sh -c "$(sed -n '/БЕЗОПАСНОСТЬ: панель агента/,/dport 8000 -j DROP || true/p' /run_api.sh)" \
    2>/dev/null || true

echo "=== правила ==="
iptables -S INPUT | grep 8000

/opt/venv/bin/python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 --app-dir /app \
    >/tmp/api.log 2>&1 &
sleep 4

echo
echo "=== сторож проверяет панель по петле ==="
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:8000/api/health)
echo "127.0.0.1 /api/health -> $code"
[ "$code" = "200" ] || { echo "ПРОВАЛ: сторож снова не достучится"; exit 1; }

echo
echo "=== и именно так, как он это делает ==="
if curl -sf --max-time 5 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "curl -sf проходит: ок"
else
    echo "ПРОВАЛ: curl -sf не проходит — сторож считает панель мёртвой"
    exit 1
fi

echo
echo "=== остальное без токена закрыто ==="
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:8000/api/system_stats)
echo "127.0.0.1 /api/system_stats -> $code"
[ "$code" = "401" ] || { echo "ПРОВАЛ: панель отдаёт данные без токена"; exit 1; }

echo
echo "=== с токеном отдаёт ==="
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    -H "X-Api-Key: $API_TOKEN" http://127.0.0.1:8000/api/system_stats)
echo "с ключом -> $code"
[ "$code" = "200" ] || { echo "ПРОВАЛ: ключ не принимается"; exit 1; }

echo
echo "ВСЁ ПРОШЛО"
