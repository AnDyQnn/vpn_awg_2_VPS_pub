#!/bin/bash
# Хостовое обслуживание нод (идемпотентно; вызывается из deploy.sh и install.sh):
#   1) авто-обновления системы НОЧЬЮ (а не в случайное дневное время),
#   2) потолок размера логов journald,
#   3) еженедельная авто-очистка мусора (docker + журналы).
#
# ЗАЧЕМ: apt/unattended-upgrades по умолчанию стартуют в случайное ДНЕВНОЕ время (на проде
# видели apt-daily в 16:45, upgrade в 06:17). На VPS с 1 vCPU это даёт внезапные спайки
# нагрузки среди дня. Плюс журналы и docker-мусор со временем забивают небольшой диск
# (у DE всего 10 ГБ). Всё это чиним на уровне systemd — работает независимо от бота, на
# обеих нодах, применяется на очередном деплое. Сервер вручную трогать не нужно.
#
# Времена задаются в ЛОКАЛЬНОМ времени сервера (RU=Europe/Moscow, DE=Europe/Berlin).
# Ребут для применения обновлений делает бот раз в неделю (RU вс 04:00 MSK, DE — отдельно),
# поэтому авто-ребут в unattended-upgrades намеренно НЕ включаем (чтобы не было двойных).

set -u

# 1. unattended-upgrades установлен и включён (авто-установка обновлений).
if ! dpkg -s unattended-upgrades >/dev/null 2>&1; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y unattended-upgrades >/dev/null 2>&1 || true
fi
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
# Авто-обновления ставят ВСЕ пакеты, а не только security.
#
# Раньше здесь были одни security-патчи, а «крупные апгрейды вручную» не делал никто:
# apt upgrade выполнялся ровно один раз, при первичной установке. Через год разница
# между сервером и репозиторием становится заметной.
#
# Авто-ребут по-прежнему выключен: перезагрузку делает бот раз в неделю, и установка
# теперь подогнана прямо под неё (см. таймеры ниже) — обновления применяются через час
# после установки, а не лежат применёнными наполовину неделю.
cat > /etc/apt/apt.conf.d/52vpn-unattended <<'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-updates";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF

# 2. Переносим таймеры apt на ночь (пустой OnCalendar= сбрасывает вендорный дефолт).
#    apt-daily — обновление списков + скачивание (~02:30); apt-daily-upgrade — установка (~03:00).
mkdir -p /etc/systemd/system/apt-daily.timer.d
cat > /etc/systemd/system/apt-daily.timer.d/override.conf <<'EOF'
[Timer]
OnCalendar=
OnCalendar=*-*-* 02:30
RandomizedDelaySec=20m
Persistent=true
EOF

# Установка обновлений — РАЗ В НЕДЕЛЮ, в ночь перед плановой перезагрузкой.
# Бот перезагружает ноду в воскресенье в 04:00, поэтому ставим в 03:00 того же дня:
# обновления применяются через час, а не ждут применения неделю. Заодно перезапуск
# демона docker при апгрейде (а он рвёт контейнеры) приходится на три часа ночи и
# гасится ближайшей перезагрузкой.
mkdir -p /etc/systemd/system/apt-daily-upgrade.timer.d
cat > /etc/systemd/system/apt-daily-upgrade.timer.d/override.conf <<'EOF'
[Timer]
OnCalendar=
OnCalendar=Sun *-*-* 03:00
RandomizedDelaySec=15m
Persistent=true
EOF

# 2.5 ЗАПЛАТКИ БЕЗОПАСНОСТИ — КАЖДЫЙ ДЕНЬ, А НЕ РАЗ В НЕДЕЛЮ.
#
# Общая установка стоит по воскресеньям намеренно: она задевает всё подряд, а
# рядом плановая перезагрузка, которая доводит дело до конца. Но заплатка
# безопасности не должна ждать до семи суток только потому, что рядом с ней в
# очереди лежит косметика.
#
# Поэтому отдельный ежедневный проход, и он берёт РОВНО то, что пришло из
# ветки безопасности, — по одному пакету поимённо, а не «обнови всё». Список
# пуст — ничего и не делается.
#
# Docker этим проходом не задевается никогда: он приезжает из своего источника,
# а не из веток Ubuntu. Значит контейнеры не перезапускаются, и туннель не
# рвётся.
cat > /usr/local/sbin/vpn-security-upgrade <<'SEC'
#!/bin/bash
# Ставит только то, что пришло из ветки безопасности. Ничего не удаляет.
set -u
export DEBIAN_FRONTEND=noninteractive
APT="apt-get -o DPkg::Lock::Timeout=300 -o Dpkg::Options::=--force-confold"
$APT update -qq >/dev/null 2>&1
SEC_PKGS=$(apt-get -s upgrade 2>/dev/null | awk '/^Inst/ && /security/ {print $2}')
if [ -z "$SEC_PKGS" ]; then
    echo "[security] заплаток нет"
    exit 0
fi
echo "[security] ставлю: $SEC_PKGS"
# --only-upgrade: новые пакеты не появляются, а значит и удалять ничего не
# придётся. Именно этого мы и хотим от прохода, который идёт без присмотра.
$APT -y --only-upgrade install $SEC_PKGS
SEC
chmod +x /usr/local/sbin/vpn-security-upgrade

cat > /etc/systemd/system/vpn-security-upgrade.service <<'UNIT'
[Unit]
Description=Заплатки безопасности ОС (ежедневно)
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/vpn-security-upgrade
UNIT

cat > /etc/systemd/system/vpn-security-upgrade.timer <<'UNIT'
[Unit]
Description=Заплатки безопасности ОС — каждый день

[Timer]
OnCalendar=*-*-* 03:40
RandomizedDelaySec=20m
Persistent=true

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload 2>/dev/null || true
systemctl enable --now vpn-security-upgrade.timer 2>/dev/null || true
echo "[maintenance] Заплатки безопасности ставятся ежедневно в 03:40."

# 3. Потолок логов journald.
#
# Он тут был и раньше — 200 МБ. Но на узле выхода диск всего десять гигабайт, и
# журнал честно упирался в этот потолок: 194 МБ при двух с половиной свободных.
# Поломкой это не было, просто цифра оказалась щедрой не по размеру диска.
#
# Теперь считаем от диска: на тесном узле 64 МБ, на просторном 256 МБ.
DISK_GB=$(df -BG --output=size / 2>/dev/null | tail -1 | tr -dc '0-9')
if [ "${DISK_GB:-0}" -gt 0 ] && [ "${DISK_GB:-0}" -lt 20 ]; then
    JOURNAL_CAP=64M
else
    JOURNAL_CAP=256M
fi
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/size.conf <<EOF
[Journal]
SystemMaxUse=${JOURNAL_CAP}
SystemKeepFree=500M
RuntimeMaxUse=32M
EOF
systemctl restart systemd-journald 2>/dev/null || true
echo "Потолок журнала: ${JOURNAL_CAP} (диск ${DISK_GB:-?} ГБ)"

# 4. Еженедельная авто-очистка мусора (docker + журналы) через systemd-таймер.
#    Раньше это делал только бот на RU (ежедневно, флаг do_cleanup) — DE оставалась без
#    очистки и копила мусор. Теперь чистятся ОБЕ ноды, независимо от бота, раз в неделю ночью.
#    prune без --volumes: именованные тома не трогаем (данные проекта — в bind-mount ./volumes).
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Каталог ноды передаёт вызывающий скрипт; если не передан — вычисляем.
NODE_DIR_FOR_WATCHDOG="${1:-$(dirname "$SELF_DIR")}"
cat > /etc/systemd/system/vpn-cleanup.service <<EOF
[Unit]
Description=VPN node weekly cleanup (docker, journald, apt)

[Service]
Type=oneshot
Environment=GC_FLAGS_DIR=${NODE_DIR_FOR_WATCHDOG}/volumes/flags
# Сборщик мусора: докер, журналы, кэш пакетов, старые ядра, хвосты удалённых
# пакетов, прошивки несуществующего железа. Каждое удаление он сначала
# проигрывает всухую и отказывается от шага, если под нож идёт что-то нужное —
# ядро, докер, systemd, туннель. Что освободил — пишет в volumes/flags для бота.
ExecStart=/bin/bash ${SELF_DIR}/gc.sh
# Ротация текстовых журналов: журнал systemd чистит сборщик, а вот /var/log
# с файлами служб раньше никто не трогал.
ExecStart=/usr/sbin/logrotate -f /etc/logrotate.conf
# Проверка самого хоста: место, inode, журналы, зависшие процессы, нужна ли
# перезагрузка после обновлений. Отчёт кладётся в volumes/flags для бота.
ExecStart=/bin/bash ${SELF_DIR}/host_health.sh ${NODE_DIR_FOR_WATCHDOG}
# Сверка базы с тем, что реально стоит на узле: все ли пиры на месте и нет ли
# лишних, разложены ли имена, стоят ли правила ролей, считается ли трафик, не
# отстала ли вторая нода. Ту же сверку показывает аудит по кнопке, но кнопку
# нажимают редко, а расходится состояние само. Расхождения уходят в журнал —
# видно через "journalctl -u vpn-cleanup". Ничего не меняет, только читает.
#
# ВНИМАНИЕ: этот блок пишется НЕзакавыченным heredoc — иначе не подставятся
# пути. Значит оболочка выполняет здесь и обратные кавычки, и $(...). Раньше в
# этой самой строке стояли обратные кавычки вокруг journalctl — и весь его
# вывод вписывался прямо в файл службы. Дальше петля кормила сама себя: systemd
# ругался на мусорные строки, ругань попадала в журнал, журнал вписывался
# снова. На боевых узлах файл дорос до 41 МБ и двухсот тысяч строк, а журнал
# systemd — до 194 МБ на диске в десять гигабайт.
#
# Никаких обратных кавычек и $(...) в этом блоке.
ExecStart=/bin/bash ${SELF_DIR}/contract_check.sh ${NODE_DIR_FOR_WATCHDOG}
EOF
# Проверка сразу после записи: файл службы — это десяток строк. Если он вышел
# больше, значит в heredoc снова что-то выполнилось и натекло. Такое лучше
# поймать здесь, чем спустя месяц по раздутому журналу.
UNIT_SIZE=$(wc -c < /etc/systemd/system/vpn-cleanup.service 2>/dev/null || echo 0)
if [ "$UNIT_SIZE" -gt 8192 ]; then
    echo "⚠️  Файл службы уборки вышел ${UNIT_SIZE} байт вместо пары тысяч." >&2
    echo "    В него натекло лишнее — чиню и продолжаю." >&2
    cat > /etc/systemd/system/vpn-cleanup.service <<EOF2
[Unit]
Description=VPN node weekly cleanup (docker, journald, apt)

[Service]
Type=oneshot
Environment=GC_FLAGS_DIR=${NODE_DIR_FOR_WATCHDOG}/volumes/flags
ExecStart=/bin/bash ${SELF_DIR}/gc.sh
ExecStart=/usr/sbin/logrotate -f /etc/logrotate.conf
ExecStart=/bin/bash ${SELF_DIR}/host_health.sh ${NODE_DIR_FOR_WATCHDOG}
ExecStart=/bin/bash ${SELF_DIR}/contract_check.sh ${NODE_DIR_FOR_WATCHDOG}
EOF2
fi

cat > /etc/systemd/system/vpn-cleanup.timer <<'EOF'
[Unit]
Description=Weekly VPN node cleanup

[Timer]
OnCalendar=Sun *-*-* 05:00
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 4b. Следы прежних входов в файрволе хоста.
#
# Свой Xray убран целиком: запасные входы 2053 и 2083, подписка наружу на
# 2096. Правила на них остались бы открытыми дверями, за которыми никто не
# слушает. Снимаем — но только если порт действительно пуст: пока старый
# контейнер ещё работает, он его держит, и правило снимется при следующем
# проходе. 443 не трогаем: там теперь подписка для клиентов на mihomo.
#
# ufw есть не на всех нодах — отсутствие не считаем бедой.
if command -v ufw >/dev/null 2>&1; then
    for XPORT in 2053 2083 2096; do
        ufw status 2>/dev/null | grep -qE "^$XPORT(/tcp)? " || continue
        if ss -lnt 2>/dev/null | awk '{print $4}' | grep -qE "(^|[.:])$XPORT\$"; then
            echo "[maintenance] Правило на $XPORT/tcp пока оставлено: порт ещё слушается."
            continue
        fi
        ufw delete allow "$XPORT/tcp" >/dev/null 2>&1 || true
        ufw delete allow "$XPORT" >/dev/null 2>&1 || true
        echo "[maintenance] Сняты правила ufw на $XPORT: там больше никто не слушает."
    done

    # Второй интерфейс AmneziaWG (переезд на новый ключ, 51821/udp) убран. Правило
    # снимаем, только если порт действительно никто не слушает.
    if ufw status 2>/dev/null | grep -qE "^51821/udp"; then
        if ss -lnu 2>/dev/null | awk '{print $4}' | grep -qE "(^|[.:])51821\$"; then
            echo "[maintenance] Правило на 51821/udp пока оставлено: порт ещё слушается."
        else
            ufw delete allow 51821/udp >/dev/null 2>&1 || true
            echo "[maintenance] Снято правило ufw на 51821/udp: второго интерфейса больше нет."
        fi
    fi

    # Открытый порт, которого никто не слушает, — это не дыра, но и не порядок:
    # он остаётся в списке и каждый следующий человек тратит время, выясняя,
    # что там. SSH давно переехал с 22-го, а правило осталось с установки.
    #
    # Снимаем ТОЛЬКО если 22-й действительно никем не занят: если кто-то вернул
    # его сознательно, закрывать вход под собой нельзя.
    SSH_EFF_PORT=$(sshd -T 2>/dev/null | awk '/^port /{print $2}' | head -1)
    if [ -n "$SSH_EFF_PORT" ] && [ "$SSH_EFF_PORT" != "22" ]; then
        if ! ss -lnt 2>/dev/null | awk '{print $4}' | grep -qE '(^|[.:])22$'; then
            if ufw status 2>/dev/null | grep -qE '^22/tcp'; then
                ufw delete allow 22/tcp >/dev/null 2>&1 || true
                echo "[maintenance] Снято лишнее правило ufw на 22/tcp: SSH живёт на $SSH_EFF_PORT."
            fi
        fi
    fi

    # Правила из образа хостера. Наш узел ставится поверх готового образа, и в
    # файрволе остаются двери от панели управления, которой тут нет и не будет.
    # Сегодня за ними никто не слушает — но правило переживёт и нас, и того, кто
    # однажды поставит на этот порт что-нибудь своё, не заметив, что он открыт.
    #
    # Снимаем только когда порт действительно пуст: вдруг кто-то занял его
    # осознанно.
    for STALE in ispmanager vesta cpanel plesk; do
        ufw status 2>/dev/null | grep -q "^$STALE" || continue
        BUSY=""
        for SP in $(ufw app info "$STALE" 2>/dev/null |
                    sed -n 's|^ *\([0-9,]*\)/tcp$|\1|p' | tr ',' ' '); do
            ss -lnt 2>/dev/null | awk '{print $4}' |
                grep -qE "(^|[.:])$SP\$" && BUSY="$BUSY $SP"
        done
        if [ -n "$BUSY" ]; then
            echo "[maintenance] Правило «$STALE» оставлено: порты заняты —$BUSY"
            continue
        fi
        ufw delete allow "$STALE" >/dev/null 2>&1 || true
        echo "[maintenance] Снято чужое правило ufw «$STALE»: панели тут нет."
    done
fi

# 5. Сторож узла — отдельной службой, а не внутри бота.
#    Раньше за здоровьем следил сам бот: падал бот — лечить было некому. Служба
#    поднимается сама после перезагрузки и переживает падение любого контейнера.
cat > /etc/systemd/system/vpn-watchdog.service <<EOF
[Unit]
Description=VPN node watchdog (tunnel health + staged self-healing)
After=docker.service
Requires=docker.service

[Service]
Type=simple
Environment=WATCHDOG_NODE_DIR=${NODE_DIR_FOR_WATCHDOG}
ExecStart=/bin/bash ${SELF_DIR}/vpn_watchdog.sh
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload 2>/dev/null || true
systemctl enable --now vpn-watchdog.service 2>/dev/null || true

# Сторож — долгоживущий bash: код он читает один раз при старте и дальше крутит
# цикл из памяти. `enable --now` уже запущенную службу не трогает, и новый код
# сторожа до узла не доезжал вовсе: обе ноды с 20.09 жили на старом, и
# российский раз в полминуты «возвращал охрану порта подписки», которой в
# проекте уже не было. Перезапускаем, когда скрипт на диске сменился.
# Перезапуск безопасен: сторож только смотрит и лечит, связь он не держит.
WD_SHA_FILE=/var/lib/vpn-watchdog.sha256
WD_SHA=$(sha256sum "${SELF_DIR}/vpn_watchdog.sh" 2>/dev/null | cut -d' ' -f1)
if [ -n "$WD_SHA" ] && [ "$WD_SHA" != "$(cat "$WD_SHA_FILE" 2>/dev/null)" ]; then
    if systemctl restart vpn-watchdog.service 2>/dev/null; then
        echo "$WD_SHA" > "$WD_SHA_FILE"
        echo "[maintenance] Сторож перезапущен — подхватил новый код."
    else
        echo "[maintenance] ⚠️  Сторож не перезапустился: systemctl restart vpn-watchdog"
    fi
fi

# 4.5 ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ОПИСАНЫ В .env
# Переменная, которой в файле нет вовсе, ничем не отличается от переменной с
# пустым значением: и то и другое выглядит как пустота. Разница в том, что
# первую никто никогда не спрашивал — и понять это по файлу невозможно.
#
# Значений здесь не придумываем: пароль архива должен знать человек, а не
# скрипт. Заводим пустые строки, чтобы было видно, чего не хватает, и чтобы
# демону было что заменять.
# Файл берём только существующий: в репозитории лежат папки обоих узлов, а
# стоит на хосте один. Создавать `.env` соседу значит оставить на диске файл,
# который ничего не настраивает и путает при разборе.
for ENV_DIR in "$(dirname "$SELF_DIR")"/VPS_RU "$(dirname "$SELF_DIR")"/VPS_DE; do
    ENV_FILE="$ENV_DIR/.env"
    [ -f "$ENV_FILE" ] || continue
    chmod 600 "$ENV_FILE" 2>/dev/null || true
    # API_TOKEN общий для обоих узлов, пароль архива — только у мастера. Лишняя
    # пустая строка ничему не мешает, а недостающая прячет проблему.
    for KEY in API_TOKEN BACKUP_PASSWORD; do
        if ! grep -q "^${KEY}=" "$ENV_FILE" 2>/dev/null; then
            echo "${KEY}=" >> "$ENV_FILE"
            echo "[maintenance] в $(basename "$ENV_DIR")/.env добавлена строка ${KEY}="
        fi
    done
done

# 5. Применяем всё. (SSH-порт закрепляется в install.sh обычным sshd — здесь не трогаем.)
systemctl daemon-reload 2>/dev/null || true
systemctl restart apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true
systemctl restart systemd-journald 2>/dev/null || true
systemctl enable --now vpn-cleanup.timer 2>/dev/null || true

echo "[maintenance] Настроено: обновления вс ~03:00 перед плановым ребутом, потолок journald 200M, недельная уборка (докер, журналы, кэш пакетов, старые ядра) с проверкой хоста (вс ~05:00), сторож узла запущен."
