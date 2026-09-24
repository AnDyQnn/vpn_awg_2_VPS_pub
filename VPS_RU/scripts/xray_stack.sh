#!/bin/bash
# Стек Xray (панель 3X-UI) — приводит контейнер в соответствие с .env.
#
#   xray_stack.sh prepare <папка ноды>   — до `docker compose up`: скачать образ
#   xray_stack.sh settle  <папка ноды>   — после: убрать контейнер, если выключен
#
# Включён стек или нет, решает одна строка в .env — `COMPOSE_PROFILES=xray`.
# Её пишет бот (кнопка в «Протоколах»), а compose по ней поднимает сервис xui.
#
# Зачем отдельный шаг, если compose и так всё делает:
#
#   • скачать заранее. Образ весит почти полгигабайта, а пересоздание по
#     просьбе бота ограничено пятью минутами — на медленном канале первое
#     включение упёрлось бы в этот предел. Качаем здесь, со своим запасом;
#
#   • убрать выключенное. Сервис, чей профиль сняли, compose не останавливает:
#     он перестаёт его поднимать, но уже запущенный контейнер не трогает. Без
#     этого шага «выключить» ничего бы не выключало.
set -u

MODE="${1:-settle}"
NODE_DIR="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CONTAINER=vpn_xui

enabled() {
    grep -qE '^COMPOSE_PROFILES=["'"'"']?([^"'"'"']*,)?xray(,[^"'"'"']*)?["'"'"']?[[:space:]]*$'         "$NODE_DIR/.env" 2>/dev/null
}

case "$MODE" in
  prepare)
    enabled || exit 0
    echo "[xray] стек включён — проверяю образ панели"
    # Образ уже на месте — pull только сверит слои и выйдет быстро.
    if (cd "$NODE_DIR" && timeout 1200 docker compose pull -q xui >/dev/null 2>&1); then
        echo "[xray] образ панели на месте"
    else
        echo "[xray] ⚠️  образ панели скачать не вышло — compose попробует сам"
    fi
    ;;
  settle)
    if enabled; then
        exit 0
    fi
    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
        docker rm -f "$CONTAINER" >/dev/null 2>&1 &&
            echo "[xray] стек выключен — контейнер панели убран"
    fi
    ;;
  status)
    if enabled; then echo "включён"; else echo "выключен"; fi
    docker ps -a --format '{{.Names}} {{.Status}}' 2>/dev/null | grep "^$CONTAINER " || echo "контейнера нет"
    ;;
  *)
    echo "использование: xray_stack.sh prepare|settle|status [папка ноды]"
    exit 1
    ;;
esac
