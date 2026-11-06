#!/bin/bash

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
echo "🚀 Установка VPN Dashboard в: $APP_DIR"

echo "🛡️ Базовая настройка безопасности и обновление системы..."
apt-get update && apt-get upgrade -y
apt-get install -y fail2ban ufw curl git unattended-upgrades

systemctl enable fail2ban
systemctl start fail2ban

# Ночные авто-обновления системы (переносим apt на ночь, чтобы не спайкать нагрузку днём)
if [ -f "$APP_DIR/../scripts/ensure_host_maintenance.sh" ]; then
    bash "$APP_DIR/../scripts/ensure_host_maintenance.sh" || true
fi

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
sysctl --system >/dev/null 2>&1

echo "💾 Проверка swap (нужен на 1–2 ГБ RAM, чтобы Control Plane/бот не словили OOM)..."
# единый идемпотентный скрипт — он же вызывается при КАЖДОМ обновлении (deploy.sh),
# чтобы swap подтягивался сам и через обновление, а не только при первой установке.
bash "$(dirname "$APP_DIR")/scripts/ensure_swap.sh" || true
# Секреты Control Plane (SECRET_KEY, пароль админки) CP генерит сам в БД при старте —
# .env остаётся стоковым, руками ничего дописывать не нужно.

echo ""
echo "🔑 Проверка OpenSSH..."
# На «минимальных» образах хостеров sshd нет вовсе: сервер доступен только из
# консоли хостера, а смена порта ниже правила конфиг, который некому читать.
# Ставим, восстанавливаем, что нужно для старта, и проверяем, что он слушает.
SSH_FRESH=0
if [ ! -x /usr/sbin/sshd ]; then
    echo "--> sshd не найден, ставлю openssh-server..."
    apt-get install -y openssh-server || echo "❌ openssh-server не поставился."
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
read -p "Введите новый порт для SSH (рекомендуется от 10000 до 65000) или нажмите Enter, чтобы оставить 22: " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

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

# 80 — проверка Let's Encrypt при выпуске сертификата узла. UDP 51820 — сам VPN.
ufw allow 80/tcp   >/dev/null 2>&1 || true
ufw allow 51820/udp >/dev/null 2>&1 || true

echo "📦 Проверка и настройка Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi
apt-get update && apt-get install -y docker-compose-plugin git
systemctl enable docker
systemctl start docker

echo "🔧 Настройка прав..."
chmod +x "$APP_DIR/install.sh"
mkdir -p "$APP_DIR/scripts"
chmod +x "$APP_DIR/scripts/"*.sh
mkdir -p "$APP_DIR/volumes/flags"
mkdir -p "$APP_DIR/volumes/backups"
mkdir -p "$APP_DIR/volumes/configs"
mkdir -p "$APP_DIR/volumes/wireguard"
mkdir -p "$APP_DIR/volumes/database"
# Сертификат. Папку создаёт и скрипт сертификата, но зовётся он уже ПОСЛЕ подъёма
# контейнеров — а её монтирует узел, и докер успел бы создать её сам, своими
# правами. Пусть лучше она будет наша и заранее.
mkdir -p "$APP_DIR/volumes/certs"
# Секреты хоста: пара для доступа к зоне домена. В контейнеры не передаётся, в
# архив бэкапа не входит. Права сразу закрытые — не потому, что кто-то полезет,
# а потому что открытую папку потом никто не закроет.
mkdir -p "$APP_DIR/volumes/secrets"
chmod 700 "$APP_DIR/volumes/secrets"

# ИСПРАВЛЕНИЕ: Умный поиск Git-репозитория
cd "$APP_DIR"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git rev-parse HEAD | cut -c1-7 > "$APP_DIR/volumes/VERSION"
else
    echo "unknown" > "$APP_DIR/volumes/VERSION"
fi

# 🔗 Автоопределение СВОЕГО GitHub-репозитория: дистрибутивы клиента собираются в
# твоём Actions/Releases под твой Control Plane — у каждого деплоера свой «блок»,
# сборки не пересекаются. Если уже задано в .env — не трогаем.
if ! grep -q '^CP_GITHUB_REPO=' "$APP_DIR/.env" 2>/dev/null; then
    ORIGIN_URL="$(git config --get remote.origin.url 2>/dev/null || true)"
    DETECTED_REPO="$(echo "$ORIGIN_URL" | sed -E 's#(git@github.com:|https?://[^/]*/)##; s#\.git$##')"
    if [ -n "$DETECTED_REPO" ]; then
        echo "CP_GITHUB_REPO=$DETECTED_REPO" >> "$APP_DIR/.env"
        echo "🔗 Сборки клиента пойдут в ТВОЙ репозиторий: $DETECTED_REPO"
    fi
fi

echo "⚙️ Настройка демона автообновлений..."
cat <<EOF > /etc/systemd/system/vpn-updater.service
[Unit]
Description=VPN Dashboard Auto-Updater Daemon
After=network-online.target docker.service
Wants=network-online.target docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=/bin/bash $APP_DIR/scripts/host_updater.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vpn-updater
systemctl restart vpn-updater

if [ ! -f "$APP_DIR/.env" ]; then
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
# PUBLIC_DOMAIN здесь по той же причине: имя узла задаётся из бота, но пока
# строки нет вовсе, по файлу не понять, что такая настройка существует. А она
# меняет многое — от срока сертификата до зоны имён внутри туннеля.
# APP_VERSION — тег образов. Без него compose разворачивает `${APP_VERSION:-dev}`
# в несуществующий `:dev` и уходит собирать образ с нуля; на одном ядре это часы,
# и всё это время тот, кто позвал compose, стоит и ждёт. Выкладка перезапишет
# значение своим, здесь важно, чтобы строка просто была.
if ! grep -q "^APP_VERSION=" "$APP_DIR/.env" 2>/dev/null; then
    echo "APP_VERSION=$(tr -d '[:space:]' < "$(dirname "$APP_DIR")/VERSION" 2>/dev/null || echo dev)" >> "$APP_DIR/.env"
fi

for KEY in API_TOKEN BACKUP_PASSWORD PUBLIC_DOMAIN; do
    if ! grep -q "^${KEY}=" "$APP_DIR/.env" 2>/dev/null; then
        echo "${KEY}=" >> "$APP_DIR/.env"
    fi
done
chmod 600 "$APP_DIR/.env"

# --- Токен панелей узлов ---
# Здесь НЕ генерируем намеренно. Токен должен совпадать на обеих нодах, а установщик
# знает только про свою: сгенерировав его тут, мы оставили бы агента без токена
# навсегда. Выдаёт его бот — одной кнопкой и сразу на обе ноды. Он же напомнит
# при первом запуске, если токена нет.

# --- Пароль архива резервных копий ---
# Архив уносит приватный ключ сервера и конфигурации всех пользователей, поэтому
# он шифруется. Пароль живёт ТОЛЬКО здесь, в .env: положи его в базу — и он окажется
# внутри того самого архива, который защищает.
# Пропустить можно, но тогда бот при первом запуске не пустит дальше, пока не задашь.
if ! grep -q '^BACKUP_PASSWORD=.\+' "$APP_DIR/.env" 2>/dev/null; then
    BK_PASS=""
    # Спрашиваем, только если есть у кого. Установщик запускают и без терминала —
    # по трубе, из другого скрипта, при обновлении. Там `read` получает конец
    # ввода мгновенно, и молчаливое «пропустить» выглядело как ответ человека.
    if [ -t 0 ]; then
        echo ""
        echo "🔐 Пароль для шифрования резервных копий."
        echo "   Архив содержит ключ сервера и конфиги всех пользователей."
        echo "   СОХРАНИТЕ пароль отдельно: без него копию не открыть."
        read -r -s -p "   Введите пароль (Enter — пропустить и задать позже из бота): " BK_PASS
        echo ""
    else
        echo "🔐 Пароль архива не спрашиваю: запуск без терминала."
    fi
    if [ -n "$BK_PASS" ]; then
        grep -v '^BACKUP_PASSWORD=' "$APP_DIR/.env" > "$APP_DIR/.env.tmp" 2>/dev/null || true
        mv "$APP_DIR/.env.tmp" "$APP_DIR/.env" 2>/dev/null || true
        echo "BACKUP_PASSWORD=$BK_PASS" >> "$APP_DIR/.env"
        echo "   ✅ Пароль записан."
    else
        # Строку заводим пустой, а не пропускаем файл вовсе. Переменная, которой
        # в `.env` нет, не отличается от переменной со значением: и то и другое
        # выглядит как пустота, и понять, спрашивали её вообще или нет, нельзя.
        if ! grep -q '^BACKUP_PASSWORD=' "$APP_DIR/.env" 2>/dev/null; then
            echo "BACKUP_PASSWORD=" >> "$APP_DIR/.env"
        fi
        echo "   ⏭️  Пароль не задан. Бот потребует его при первом запуске."
    fi
    unset BK_PASS
fi
chmod 600 "$APP_DIR/.env"

echo "🚀 Запуск контейнеров..."
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

# --- BBR: УПРАВЛЕНИЕ ПЕРЕГРУЗКОЙ TCP --------------------------------------
# Кому помогает: соединениям, которые терминируются на самом узле (бот, свои
# сервисы). TCP людей на AmneziaWG идёт насквозь и заканчивается у них самих и
# у сайта — наше ядро им не указывает, прибавки там почти нет.
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

BUILDKIT_PROGRESS=plain docker compose up -d --build --remove-orphans

# --- КЛЮЧ ДЛЯ ГЕРМАНИИ (DE_AGENT) ------------------------------------------
# Ключ выпускает бот: просит панель узла (vpn_wireguard) завести пир и пишет
# его в базу. Бот живёт в сетевом пространстве vpn_wireguard, поэтому:
#   • пока узел не поднялся, ни панели, ни базы бот не видит;
#   • если узел на старте перезапустился, бот остаётся в старом, пустом
#     сетевом пространстве («Network is unreachable») — его надо перезапустить.
# Раньше здесь было слепое «sleep 15» и одна попытка: не успел узел —
# ошибка печаталась, установка шла дальше, а ключа не было.
echo "⏳ Жду, пока узел устойчиво поднимется..."
UP_STREAK=0
for i in $(seq 1 60); do                       # до 5 минут
    if [ "$(docker inspect -f '{{.State.Running}}' vpn_wireguard 2>/dev/null)" = "true" ] \
       && [ "$(docker inspect -f '{{.State.Restarting}}' vpn_wireguard 2>/dev/null)" = "false" ]; then
        UP_STREAK=$((UP_STREAK + 1))
        [ "$UP_STREAK" -ge 3 ] && break        # 15 секунд подряд без перезапуска
    else
        UP_STREAK=0
    fi
    sleep 5
done
# Узел мог перезапуститься уже после старта бота — переподключаем бота к сети.
docker restart vpn_bot >/dev/null
sleep 10

echo "🤖 Генерация ключа для Германии (DE_AGENT)..."
DE_OK=0
for i in $(seq 1 12); do                       # до 2 минут: база и панель стартуют не сразу
    if docker exec vpn_bot python init_de_agent.py; then
        DE_OK=1
        break
    fi
    echo "   узел ещё поднимается, повтор через 10 с ($i/12)..."
    sleep 10
done

if [ "$DE_OK" = 1 ] && [ -f "$APP_DIR/volumes/DE_AGENT_CONFIG.txt" ]; then
    mv "$APP_DIR/volumes/DE_AGENT_CONFIG.txt" "$APP_DIR/DE_AGENT_CONFIG.txt"
    echo "================================================================"
    echo "🎉 КЛЮЧ ДЛЯ СЕРВЕРА В ГЕРМАНИИ УСПЕШНО СГЕНЕРИРОВАН!"
    echo "👉 $APP_DIR/DE_AGENT_CONFIG.txt"
    echo "Скопируй его в Германию по пути: /volumes/wireguard/wg0.conf"
    echo ""
    echo "Токен панелей выдаст бот — он напомнит при первом запуске."
    echo "================================================================"
else
    echo "================================================================"
    echo "❌ КЛЮЧ ДЛЯ ГЕРМАНИИ НЕ СГЕНЕРИРОВАЛСЯ."
    echo "Остальное установлено. Повторить вручную:"
    echo "   cd $APP_DIR"
    echo "   docker restart vpn_bot && sleep 15"
    echo "   docker exec vpn_bot python init_de_agent.py"
    echo "   cp volumes/configs/DE_AGENT.conf DE_AGENT_CONFIG.txt"
    echo "Если не выходит — посмотри: docker ps -a; docker logs vpn_wireguard --tail 30"
    echo "================================================================"
fi

# Сертификат узла. Берётся сразу при установке: без него страница отказа
# работает на самоподписанном, и браузер ругается. Бесплатный, на IP-адрес,
# домен не нужен. Не вышло — ничего не сломается, повторить можно из бота.
if [ -f "$(dirname "$APP_DIR")/scripts/public_sub.sh" ]; then
    echo "🔑 Сертификат узла..."
    bash "$(dirname "$APP_DIR")/scripts/public_sub.sh" ensure "$APP_DIR" || true
fi

echo "✅ УСТАНОВКА И НАСТРОЙКА ЗАВЕРШЕНА!"
echo ""
echo "Дальше — в боте. Уже работает всё, ради чего ставился проект:"
echo "  • AmneziaWG, выдача ключей, роли и доступы, фильтры;"
echo "  • имена вместо адресов — в зоне .vpn."
echo ""
echo "Необязательное, по желанию и по порядку:"
echo "  1. Токен панелей узлов — кнопкой в боте, сразу на обе машины."
echo "  2. Пароль архива бэкапов, если пропустили выше."
echo "  3. Своё имя узла (домен, ~200 ₽/год): «Домен и сертификаты → Имя узла»."
echo "     Сертификат станет на 90 дней вместо 160 часов, а имена внутри"
echo "     туннеля переедут в этот домен сами."
echo "  4. Сертификат на внутренние имена — там же. Убирает"
echo "     предупреждение браузера на страницах отказа и выдачи ключей."
echo ""
echo "Подробно: docs/domain.md, docs/names.md"