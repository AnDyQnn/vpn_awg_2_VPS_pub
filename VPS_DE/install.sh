#!/bin/bash

# Скрипт установки DE Agent (Сервер в Германии)
set -e

if [ "$EUID" -ne 0 ]; then
  echo "❌ Запустите с правами root: sudo bash install.sh"
  exit 1
fi

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Пока идёт установка, сторож узла не вмешивается. Без этой метки он лечил
# недостроенный узел: перезапускал docker посреди сборки, а мог и перезагрузить
# сервер. Метка снимается на выходе, даже если установка упала.
mkdir -p "$APP_DIR/volumes/flags"
touch "$APP_DIR/volumes/flags/installing"
trap 'rm -f "$APP_DIR/volumes/flags/installing"' EXIT

# --- apt без вопросов ---------------------------------------------------------
# Установку запускают по SSH, в терминале, и apt там спрашивает: needrestart
# выводит диалог «какие службы перезапустить», а обновление пакета с конфигом,
# который правил хостер (sshd_config), — «оставить свой или взять новый». Оба
# ждут ответа, и установка стоит. А в первые минуты жизни свежего VPS apt
# занят unattended-upgrades: без ожидания блокировки apt-get падал сразу с
# «Could not get lock», и установка шла дальше без пакетов.
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a
APT_OPTS=(-o DPkg::Lock::Timeout=600 -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold)
apt_get() { apt-get "${APT_OPTS[@]}" "$@"; }

# .env без перевода строки в конце (так лежал .env.example, так оставляют
# правки через echo и sed) склеивал нашу дозапись с последней строкой:
# «POSTGRES_DB=vpndbBACKUP_PASSWORD=…» — база с мусорным именем, без
# таблиц, и потерянный пароль архива. Дописываем недостающий перевод строки.
[ -s "$APP_DIR/.env" ] && [ "$(tail -c1 "$APP_DIR/.env" | wc -l)" -eq 0 ] && echo >> "$APP_DIR/.env"
echo "=========================================="
echo "🚀 Начинаем установку DE Agent в: $APP_DIR"
echo "=========================================="

echo "🛡️ Настройка безопасности и обновление системы..."
apt_get update && apt_get upgrade -y
apt_get install -y fail2ban ufw curl wget git jq iptables iproute2 procps unattended-upgrades

systemctl enable fail2ban
systemctl start fail2ban


echo "🛡️ Настройка защиты ядра от DDoS и флуда (sysctl)..."
cat <<EOF > /etc/sysctl.d/99-vpn-security.conf
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.tcp_rfc1337 = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
EOF
sysctl --system >/dev/null 2>&1 || true

echo ""
echo "🔑 Проверка OpenSSH..."
# На «минимальных» образах хостеров sshd нет вовсе: сервер доступен только из
# консоли хостера, а смена порта ниже правила конфиг, который некому читать.
# Ставим, восстанавливаем, что нужно для старта, и проверяем, что он слушает.
SSH_FRESH=0
if [ ! -x /usr/sbin/sshd ]; then
    echo "--> sshd не найден, ставлю openssh-server..."
    apt_get install -y openssh-server || echo "❌ openssh-server не поставился."
    SSH_FRESH=1
fi
if [ -x /usr/sbin/sshd ]; then
    # Пакет стоит, а основного конфига нет — без него sshd не стартует и не
    # читает sshd_config.d. Берём штатный из пакета.
    if [ ! -f /etc/ssh/sshd_config ] && [ -f /usr/share/openssh/sshd_config ]; then
        cp /usr/share/openssh/sshd_config /etc/ssh/sshd_config
        echo "--> Восстановлен /etc/ssh/sshd_config из пакета."
    fi
    if [ -f /etc/ssh/sshd_config ] && ! grep -qE '^Include /etc/ssh/sshd_config\.d/' /etc/ssh/sshd_config; then
        sed -i '1i Include /etc/ssh/sshd_config.d/*.conf' /etc/ssh/sshd_config
    fi
    mkdir -p /etc/ssh/sshd_config.d /run/sshd
    ssh-keygen -A >/dev/null 2>&1 || true            # ключи хоста, если их нет
    # Свежий openssh в Ubuntu пускает root только по ключу (prohibit-password),
    # а на новом сервере у root есть лишь пароль от хостера — после установки
    # войти было бы нечем. Только для свежей установки: чужие настройки не трогаем.
    if [ "$SSH_FRESH" = "1" ]; then
        printf 'PermitRootLogin yes\nPasswordAuthentication yes\n' > /etc/ssh/sshd_config.d/05-vpn-access.conf
    fi
    if sshd -t 2>/tmp/sshd_check.err; then
        # Сокет-активацию (Ubuntu 24.04) не трогаем: она и так слушает порт.
        # Блок смены порта ниже, если нужно, переведёт на обычный sshd.
        if ! systemctl is-active --quiet ssh.socket 2>/dev/null; then
            systemctl enable ssh 2>/dev/null || systemctl enable sshd 2>/dev/null || true
            systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null || true
        fi
        sleep 1
        SSH_CUR_PORT=$(sshd -T 2>/dev/null | awk '/^port /{print $2; exit}')
        SSH_CUR_PORT=${SSH_CUR_PORT:-22}
        if ss -ltnH "sport = :$SSH_CUR_PORT" 2>/dev/null | grep -q .; then
            echo "✅ OpenSSH работает, слушает порт $SSH_CUR_PORT."
        else
            echo "❌ sshd установлен, но порт $SSH_CUR_PORT никто не слушает:"
            systemctl status ssh --no-pager -n 5 2>/dev/null || systemctl status sshd --no-pager -n 5 2>/dev/null || true
        fi
    else
        echo "❌ Конфиг sshd с ошибкой, sshd не перезапускаю:"
        cat /tmp/sshd_check.err
    fi
    rm -f /tmp/sshd_check.err
    # fail2ban стартовал раньше sshd — перечитываем, чтобы защита SSH включилась.
    systemctl restart fail2ban 2>/dev/null || true
else
    echo "❌ sshd нет: зайти на сервер можно будет только из консоли хостера."
fi

echo ""
echo "🚨 ЗАЩИТА ОТ БРУТФОРСА (Смена порта SSH)"
# По умолчанию — порт, на котором SSH работает сейчас, а не 22. При повторной
# установке Enter означал «оставить 22»: установщик писал «порт оставлен
# стандартным» и открывал в ufw 22-й, хотя SSH давно жил на другом.
CUR_SSH_PORT=$(sshd -T 2>/dev/null | awk '/^port /{print $2; exit}')
CUR_SSH_PORT=${CUR_SSH_PORT:-22}
read -p "Введите новый порт для SSH (рекомендуется от 10000 до 65000) или нажмите Enter, чтобы оставить $CUR_SSH_PORT: " SSH_PORT || true   # под set -e: без терминала read кончается EOF, и установка обрывалась молча
SSH_PORT=${SSH_PORT:-$CUR_SSH_PORT}
# Только число в допустимых пределах: опечатка ушла бы в sshd_config, и sshd
# не поднялся бы вовсе.
case "$SSH_PORT" in
    ''|*[!0-9]*) echo "⚠️  «$SSH_PORT» — не номер порта, оставляю $CUR_SSH_PORT."; SSH_PORT=$CUR_SSH_PORT ;;
    *) if [ "$SSH_PORT" -lt 1 ] || [ "$SSH_PORT" -gt 65535 ]; then
           echo "⚠️  $SSH_PORT вне 1–65535, оставляю $CUR_SSH_PORT."; SSH_PORT=$CUR_SSH_PORT
       fi ;;
esac

if [ "$SSH_PORT" != "22" ]; then
    echo "🔧 Смена порта SSH на $SSH_PORT..."
    ufw allow $SSH_PORT/tcp
    # Порт задаём в sshd_config и работаем через ОБЫЧНЫЙ sshd (не сокет-активацию).
    # На Ubuntu 24.04 sshd часто запущен через ssh.socket — тогда порт берётся из сокета (22),
    # sshd_config игнорируется, а после апдейта/ребута порт «слетает» на 22 (и ufw его не
    # пускает → лок-аут). Поэтому глушим и МАСКИРУЕМ ssh.socket (чтобы апдейт не включил его
    # обратно) и отдаём порт обычному sshd.service из sshd_config — порт задаётся ОДИН раз и
    # держится всегда, без кастомных сокет-конфигов.
    # На новых Ubuntu основного /etc/ssh/sshd_config может не быть — тогда порт
    # кладём отдельным файлом в sshd_config.d. Если в основном файле нет строки
    # Port, sed молча ничего не менял, и порт оставался 22.
    if [ -f /etc/ssh/sshd_config ]; then
        if grep -qE '^#*Port ' /etc/ssh/sshd_config; then
            sed -i "s/^#*Port .*/Port $SSH_PORT/" /etc/ssh/sshd_config
        else
            echo "Port $SSH_PORT" >> /etc/ssh/sshd_config
        fi
    else
        mkdir -p /etc/ssh/sshd_config.d
        echo "Port $SSH_PORT" > /etc/ssh/sshd_config.d/10-vpn-port.conf
    fi
    rm -f /etc/systemd/system/ssh.socket.d/port.conf 2>/dev/null   # старый drop-in — источник конфликта
    systemctl disable --now ssh.socket 2>/dev/null || true
    systemctl mask ssh.socket 2>/dev/null || true
    systemctl daemon-reload 2>/dev/null || true
    systemctl enable ssh 2>/dev/null || systemctl enable sshd 2>/dev/null || true
    systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null || true
    # Проверяем, на каком порту sshd слушает НА САМОМ ДЕЛЕ. Не перешёл — оставляем
    # 22 открытым: иначе после включения файрвола доступ к серверу пропал бы.
    sleep 1
    NOW_PORT=$(sshd -T 2>/dev/null | awk '/^port /{print $2; exit}')
    # Порт в конфиге — ещё не порт в работе: смотрим, что его реально слушают.
    if [ "$NOW_PORT" = "$SSH_PORT" ] && ss -ltnH "sport = :$SSH_PORT" 2>/dev/null | grep -q .; then
        echo "✅ Порт SSH → $SSH_PORT (обычный sshd, из sshd_config — не слетит после апдейтов)."
    else
        echo "⚠️ sshd не перешёл на $SSH_PORT (сейчас: ${NOW_PORT:-неизвестно}). Оставляю 22 открытым,"
        echo "   чтобы не потерять доступ. Поменяйте порт вручную позже."
        ufw limit 22/tcp
    fi
else
    echo "⚠️ Порт SSH оставлен стандартным (22). Включаем защиту..."
    ufw limit 22/tcp
fi
echo "---------------------------------------------------------"

# Swap через ОБЩИЙ скрипт (как на RU): dd-based, лимит по размеру диска, переживает ребут.
# Тот же скрипт вызывается и при КАЖДОМ обновлении (deploy.sh) — настройка переприменяется сама.
echo "💾 Проверка swap..."
if [ -f "$APP_DIR/../scripts/ensure_swap.sh" ]; then
    bash "$APP_DIR/../scripts/ensure_swap.sh" || true
fi

if ! command -v docker &> /dev/null; then
    echo "--> Установка Docker..."
    # Для только что вышедшей Ubuntu у Docker может ещё не быть репозитория —
    # тогда get.docker.com падает, а Docker не ставился вовсе. Запасной путь —
    # Docker из репозитория самой Ubuntu.
    if ! { curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh; }; then
        echo "⚠️  get.docker.com не справился — ставлю Docker из репозитория Ubuntu."
    fi
    rm -f get-docker.sh
fi
if ! command -v docker &> /dev/null; then
    apt_get update && apt_get install -y docker.io || true
fi
# Compose: у Docker он зовётся docker-compose-plugin, у Ubuntu — docker-compose-v2.
if ! docker compose version >/dev/null 2>&1; then
    apt_get update
    apt_get install -y docker-compose-plugin 2>/dev/null || apt_get install -y docker-compose-v2 || true
fi
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    echo "❌ Docker или Docker Compose не установились — дальше узел не собрать."
    echo "   Проверьте вывод выше (сеть, apt) и запустите установку снова."
    exit 1
fi
systemctl enable docker
systemctl start docker

# Обслуживание хоста: ночные обновления, модули файрвола, уборка, сторож узла.
# После Docker, а не до: служба сторожа требует docker.service, и до его
# установки она не стартовала до первой перезагрузки. И с папкой узла: без
# неё служба сторожа прописывалась с корнем репозитория и не видела ни метки
# установки (лечила недостроенный узел), ни своих файлов — до первого деплоя.
if [ -f "$APP_DIR/../scripts/ensure_host_maintenance.sh" ]; then
    bash "$APP_DIR/../scripts/ensure_host_maintenance.sh" "$APP_DIR" || true
fi

echo "--> Создание директорий..."
chmod +x "$APP_DIR/install.sh"
mkdir -p "$APP_DIR/scripts"
chmod +x "$APP_DIR/scripts/"*.sh
mkdir -p "$APP_DIR/volumes/flags"
mkdir -p "$APP_DIR/volumes/wireguard"
chmod -R 777 "$APP_DIR/volumes/flags"

# ИСПРАВЛЕНИЕ: Умный поиск Git-репозитория
cd "$APP_DIR" || exit 1
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git rev-parse HEAD | cut -c1-7 > "$APP_DIR/volumes/VERSION"
else
    echo "unknown" > "$APP_DIR/volumes/VERSION"
fi

if [ ! -f "$APP_DIR/.env" ]; then
    echo "📝 Создаю пустой .env..."
    touch "$APP_DIR/.env"
fi
chmod 600 "$APP_DIR/.env"

# --- Переменные окружения описаны всегда ---
# Переменная, которой в файле нет вовсе, ничем не отличается от переменной с
# пустым значением: и то и другое выглядит как пустота. Разница в том, что
# первую никто никогда не спрашивал, и по файлу это не понять — а именно так
# и терялись API_TOKEN с паролем архива: их не было ни строкой, ни значением.
#
# Значения здесь не придумываем. Токен узлов обязан совпадать на обеих машинах,
# и выдаёт его бот сразу на обе; пароль архива должен знать человек. Заводим
# пустые строки: видно, чего не хватает, и демону есть что заменять.
if ! grep -q "^API_TOKEN=" "$APP_DIR/.env" 2>/dev/null; then
    echo "API_TOKEN=" >> "$APP_DIR/.env"
fi
chmod 600 "$APP_DIR/.env"

echo "--> Настройка системного демона DE Agent..."
SERVICE_PATH="/etc/systemd/system/de-agent-updater.service"

cat <<EOF > $SERVICE_PATH
[Unit]
Description=DE VPN Agent Host Daemon
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=/bin/bash $APP_DIR/scripts/host_updater.sh
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable de-agent-updater.service
systemctl restart de-agent-updater.service

echo "--> Сборка и запуск контейнера de_vpn_agent..."
# Тег образов — версия проекта, а не «dev». Установщик собирал образы без неё,
# и свежая нода целиком оставалась на `vpn-ru-bot:dev`: по `docker images` было
# не понять, что на ней стоит, а после первого же обновления рядом повисал
# осиротевший `:dev`. Источник версии тот же, что у деплоя, — корневой файл.
if [ -f "$APP_DIR/../VERSION" ]; then
    APP_VERSION="$(tr -d '[:space:]' < "$APP_DIR/../VERSION")"
elif [ -f "$APP_DIR/VERSION" ]; then
    APP_VERSION="$(tr -d '[:space:]' < "$APP_DIR/VERSION")"
else
    APP_VERSION="dev"
fi
export APP_VERSION
echo "🏷  Версия проекта: $APP_VERSION (тег образов)"

# Сборка пишет полосу прогресса псевдографикой и перерисовывает её
# десятки раз в секунду. В терминале это одна строка, а в журнале —
# отдельная запись на каждую перерисовку: на узле выхода за один деплой
# так набежало 2,5 миллиона строк и полгигабайта syslog при диске в 10 ГБ.
# Построчный вывод задаём переменной BUILDKIT_PROGRESS=plain, а не флагом:
# у `docker compose up` флага --progress на многих версиях нет, и установка
# падала с «unknown flag». Переменную старая версия просто не заметит.
# Сборка тянет пакеты из сети (зеркала Alpine, pip), и разовый сбой сети здесь
# обычное дело — второй заход обычно проходит. Не прошёл и он — останавливаемся:
# раньше установщик после упавшей сборки ждал узел пять минут, базу три,
# не выпускал ключ и в конце писал «установка завершена».
compose_up() { BUILDKIT_PROGRESS=plain docker compose up -d --build ; }
if ! compose_up; then
    echo "⚠️  Сборка не удалась — повторяю через 30 секунд (часто это разовый сбой сети)..."
    sleep 30
    if ! compose_up; then
        echo "================================================================"
        echo "❌ КОНТЕЙНЕРЫ НЕ СОБРАЛИСЬ — установка остановлена."
        echo "   Причина — в выводе сборки выше (строки ERROR / failed to solve)."
        echo "   Чаще всего это сеть: недоступно зеркало пакетов. Запустите"
        echo "   установку ещё раз: всё уже сделанное повторно не выполняется."
        echo "================================================================"
        exit 1
    fi
fi


# --- BBR: УПРАВЛЕНИЕ ПЕРЕГРУЗКОЙ TCP --------------------------------------
# Кому помогает: соединениям, которые терминируются на самом узле. TCP людей
# на AmneziaWG идёт насквозь — наше ядро им не указывает, прибавки там почти нет.
#
# Нефатально: нет модуля — узел работает на прежнем способе, как и работал.
echo "--> Управление перегрузкой TCP (BBR)..."
if modprobe tcp_bbr 2>/dev/null; then
    grep -qx tcp_bbr /etc/modules-load.d/bbr.conf 2>/dev/null \
        || echo tcp_bbr > /etc/modules-load.d/bbr.conf
    cat > /etc/sysctl.d/99-bbr.conf <<'BBREOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
BBREOF
    sysctl -q -p /etc/sysctl.d/99-bbr.conf 2>/dev/null || true
    echo "   Включён: $(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null)"
else
    echo "   Модуль недоступен — остаёмся на прежнем способе."
fi

echo "✅ УСТАНОВКА DE AGENT ЗАВЕРШЕНА!"