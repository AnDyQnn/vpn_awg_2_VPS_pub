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
# Подписка наружу. В файле одно слово: on или off. Скрипту нужны права хоста —
# он берёт сертификат, правит iptables и ставит таймер, и ничего из этого бот
# из контейнера сделать не может.
PUBSUB_FLAG="$FLAGS_DIR/do_public_sub"

echo "[Updater] Демон запущен для ноды: $(basename "$NODE_DIR")"
echo "[Updater] Ожидание флагов в директории: $FLAGS_DIR"

# Убедимся, что папка для флагов существует
mkdir -p "$FLAGS_DIR"

while true; do
    # 1. ОБНОВЛЕНИЕ СИСТЕМЫ
    if [ -f "$UPDATE_FLAG" ]; then
        echo "[Updater] Найдена метка обновления. Запуск deploy.sh..."
        rm -f "$UPDATE_FLAG"
        
        # Запускаем скрипт деплоя с точным путем
        bash "$SCRIPT_DIR/deploy.sh"
        
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
    # Просьб может быть несколько сразу: бот сам выдаёт токен панелей при первом
    # запуске, владелец в те же минуты задаёт пароль архива. Раньше файл был один
    # на всех и перезаписывался — одна из просьб пропадала молча. Теперь у каждой
    # своё имя, и разбираем мы их все.
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
                    # заменяем существующую строку целиком, значение может быть любым
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

    # 4.6 ПОДПИСКА НАРУЖУ
    #     Открыть её значит выдать сертификат на IP-адрес, поставить охрану
    #     порта и завести таймер продления. Всё это — работа хоста: у бота нет
    #     ни iptables, ни systemd, ни доступа к letsencrypt.
    if [ -f "$PUBSUB_FLAG" ]; then
        MODE=$(head -1 "$PUBSUB_FLAG" | tr -d '[:space:]')
        rm -f "$PUBSUB_FLAG"
        case "$MODE" in
            on|off)
                echo "[Updater] Подписка наружу: $MODE"
                bash "$(dirname "$SCRIPT_DIR")/../scripts/public_sub.sh"                     "$MODE" "$NODE_DIR" > "$FLAGS_DIR/public_sub.log" 2>&1
                echo "[Updater] Готово, отчёт в public_sub.json"
                ;;
            *)
                echo "[Updater] Подписка наружу: непонятная команда '$MODE'"
                ;;
        esac
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