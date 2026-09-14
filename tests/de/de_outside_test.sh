#!/bin/sh
# ЗАПУСК: хост (сам поднимает контейнеры)
# Панель агента снаружи должна молчать. Проверяем по-настоящему: агент в одном
# контейнере, проверяющий — в другом, между ними обычная сеть.
set -e
export MSYS_NO_PATHCONV=1

docker rm -f de-probe-agent >/dev/null 2>&1 || true
docker network inspect deprobe >/dev/null 2>&1 || docker network create deprobe >/dev/null

docker run -d --name de-probe-agent --network deprobe --privileged --entrypoint sh \
  -e API_TOKEN=secret-for-test vpn-de-test -c '
    sh -c "$(sed -n "/БЕЗОПАСНОСТЬ: панель агента/,/dport 8000 -j DROP || true/p" /run_api.sh)" 2>/dev/null || true
    /opt/venv/bin/python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 --app-dir /app
  ' >/dev/null
sleep 6

IP=$(docker inspect de-probe-agent --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
echo "адрес агента в сети: $IP"

echo
echo "=== изнутри самого агента панель жива ==="
docker exec de-probe-agent curl -s -o /dev/null -w "  /api/health -> %{http_code}\n" --max-time 5 http://127.0.0.1:8000/api/health

echo
echo "=== из соседнего контейнера — не должна отвечать ==="
# Запускаем именно curl. Без --entrypoint аргументы уходят в run_api.sh —
# тот их игнорирует и поднимает веб-сервер, контейнер живёт вечно, а тест
# просто висит: ни падения, ни прохода. Так он и висел.
#
# И смотрим на код ОТВЕТА, а не на код возврата докера: второй про то,
# ответила ли панель, не говорит ничего.
CODE=$(docker run --rm --network deprobe --entrypoint curl vpn-de-test \
         -s -o /dev/null -w '%{http_code}' --max-time 5 \
         "http://$IP:8000/api/health" 2>/dev/null) || CODE=""
# 000 — curl не получил ответа; пусто — не смог даже запуститься. И то и другое
# для нас успех: панель снаружи молчит.
echo "  снаружи -> ${CODE:-нет ответа}"
if [ -n "$CODE" ] && [ "$CODE" != "000" ]; then
    echo "  ПРОВАЛ: панель открыта соседям по сети"
    docker rm -f de-probe-agent >/dev/null 2>&1
    docker network rm deprobe >/dev/null 2>&1
    exit 1
fi
echo "  не ответила: ок"

docker rm -f de-probe-agent >/dev/null 2>&1 || true
docker network rm deprobe >/dev/null 2>&1 || true
echo
echo "ВСЁ ПРОШЛО"
