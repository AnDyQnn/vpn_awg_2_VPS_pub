#!/bin/bash
# Демон хоста (слушает команды от Telegram-бота)

# Определяем пути динамически
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_DIR="$(dirname "$SCRIPT_DIR")"
FLAGS_DIR="$NODE_DIR/volumes/flags"

# Флаги
UPDATE_FLAG="$FLAGS_DIR/do_update"
REBOOT_FLAG="$FLAGS_DIR/do_reboot"
AUDIT_FLAG="$FLAGS_DIR/do_audit"
RESTART_WG_FLAG="$FLAGS_DIR/do_restart_wg"
CLEANUP_FLAG="$FLAGS_DIR/do_cleanup"

echo "[Updater] Демон запущен для ноды: $(basename "$NODE_DIR")"
echo "[Updater] Ожидание флагов в директории: $FLAGS_DIR"

# Убедимся, что папка для флагов существует
mkdir -p "$FLAGS_DIR"

# Выкладка идёт ОТДЕЛЬНОЙ службой, а не ребёнком этого демона.
#
# В конце выкладки планируется перезапуск этого демона — отложенный на 15
# секунд, чтобы он подхватил новый код. Но если сразу за первой выкладкой в
# очереди стоит вторая (владелец нажал «обновить» дважды, или ноды обновляются
# подряд), она успевает стартовать РАНЬШЕ, чем сработает отложенный перезапуск.
# А перезапуск службы убивает всё её дерево процессов — вместе с идущей
# выкладкой.
#
# Ровно так и вышло: вторая выкладка сделала git pull и была убита на шаге
# настройки, не дойдя до сборки. Репозиторий на новой версии, контейнеры на
# старой, ни отката, ни сообщения — тишина. Снаружи это выглядит как «обновился,
# а изменений нет».
#
# Своя служба разрывает эту связь: демон перезапускается, выкладка продолжается.
# --wait отдаёт её код возврата, а одно имя службы на всех делает две
# одновременные выкладки невозможными по построению.
run_deploy() {
    if ! command -v systemd-run >/dev/null 2>&1; then
        bash "$SCRIPT_DIR/deploy.sh"
        return $?
    fi
    if systemctl is-active --quiet vpn-deploy 2>/dev/null; then
        echo "[Updater] Выкладка уже идёт — вторую не запускаю."
        return 0
    fi
    systemd-run --unit=vpn-deploy --collect --wait --quiet         --property=KillMode=process         --property=TimeoutStartSec=infinity         /bin/bash "$SCRIPT_DIR/deploy.sh"
    rc=$?
    [ $rc -ne 0 ] && echo "[Updater] Выкладка вернула код $rc — журнал: journalctl -u vpn-deploy"
    return $rc
}

while true; do
    # 1. ОБНОВЛЕНИЕ СИСТЕМЫ
    if [ -f "$UPDATE_FLAG" ]; then
        echo "[Updater] Найдена метка обновления. Запуск deploy.sh..."
        rm -f "$UPDATE_FLAG"
        
        # Запускаем скрипт деплоя своей службой — см. run_deploy выше.
        run_deploy
        
        echo "[Updater] Цикл обновления завершен."
    fi

    # 2. ПЕРЕЗАГРУЗКА СЕРВЕРА
    if [ -f "$REBOOT_FLAG" ]; then
        echo "[Updater] Найдена метка перезагрузки! Сервер уходит в ребут..."
        rm -f "$REBOOT_FLAG"
        /usr/sbin/reboot
    fi

    # 3. АУДИТ ХОСТА
    if [ -f "$AUDIT_FLAG" ]; then
        echo "[Updater] Найдена метка аудита. Запуск host_audit.sh..."
        rm -f "$AUDIT_FLAG"
        bash "$SCRIPT_DIR/host_audit.sh"
        echo "[Updater] Аудит завершен."
    fi

    # 4. ЖЕСТКИЙ РЕСТАРТ WIREGUARD (SELF-HEALING)
    if [ -f "$RESTART_WG_FLAG" ]; then
        echo "[Updater] Найдена метка рестарта WG. Перезапуск контейнеров..."
        rm -f "$RESTART_WG_FLAG"
        # Ищем контейнер по имени или через docker compose
        cd "$NODE_DIR" && docker compose restart ru_wireguard || docker compose restart de_vpn_agent
    fi
    
    # 4.5 ЗАПИСЬ ПЕРЕМЕННОЙ В .env ПО ПРОСЬБЕ БОТА
    #     Бот живёт в контейнере и получает переменные, а не файл — сам .env он править
    #     не может. Поэтому кладёт сюда строки KEY=VALUE, а правим мы, на хосте.
    #     Так задаётся пароль архива бэкапа: он обязан лежать в .env, потому что в базе
    #     оказался бы внутри того самого архива, который защищает.
    # Просьб может прийти несколько подряд, и раньше они ложились в один файл
    # с перезаписью — доезжала только последняя.
    ENV_REQUESTS=$(ls -1 "$FLAGS_DIR"/set_env "$FLAGS_DIR"/set_env.* 2>/dev/null)
    if [ -n "$ENV_REQUESTS" ]; then
        echo "[Updater] Обновляю .env по запросу бота..."
        ENV_FILE="$NODE_DIR/.env"
        touch "$ENV_FILE"; chmod 600 "$ENV_FILE"
        for REQ in $ENV_REQUESTS; do
            [ -f "$REQ" ] || continue
            while IFS= read -r line; do
                case "$line" in
                    ''|'#'*) continue ;;
                esac
                KEY="${line%%=*}"
                if grep -q "^${KEY}=" "$ENV_FILE"; then
                    # заменяем существующую строку целиком, значение любое
                    grep -v "^${KEY}=" "$ENV_FILE" > "$ENV_FILE.tmp"
                    echo "$line" >> "$ENV_FILE.tmp"
                    mv "$ENV_FILE.tmp" "$ENV_FILE"
                else
                    echo "$line" >> "$ENV_FILE"
                fi
                echo "[Updater]   переменная ${KEY} записана"
            done < "$REQ"
            shred -u "$REQ" 2>/dev/null || rm -f "$REQ"
        done
        chmod 600 "$ENV_FILE"
        # Переменная доезжает до контейнеров только при пересоздании.
        cd "$NODE_DIR" && docker compose up -d >/dev/null 2>&1
        echo "[Updater] .env обновлён, контейнеры пересозданы."
    fi

    # 5. ОЧИСТКА МУСОРА
    if [ -f "$CLEANUP_FLAG" ]; then
        echo "[Updater] Очистка логов и кэша Docker..."
        rm -f "$CLEANUP_FLAG"
        # --volumes убран: он сносит неиспользуемые именованные тома.
        # Сейчас данные лежат в bind-mount и не страдают, но это мина
        # под ноги на будущее. Недельная уборка делает то же самое.
        docker system prune -af
        journalctl --vacuum-time=3d
    fi

    # Пауза перед следующей проверкой
    sleep 5
done