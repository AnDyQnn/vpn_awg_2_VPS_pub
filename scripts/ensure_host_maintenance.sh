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

# 3. Потолок логов journald (по умолчанию лимит = 10% диска; на DE диск всего 10 ГБ).
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/size.conf <<'EOF'
[Journal]
SystemMaxUse=200M
SystemKeepFree=500M
EOF

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
ExecStart=/bin/bash ${SELF_DIR}/host_health.sh
# Сверка базы с тем, что реально стоит на узле: все ли пиры на месте и нет ли
# лишних, разложены ли имена, стоят ли правила ролей, считается ли трафик, не
# отстала ли вторая нода. Ту же сверку показывает аудит по кнопке, но кнопку
# нажимают редко, а расходится состояние само. Расхождения уходят в журнал —
# видно через `journalctl -u vpn-cleanup`. Ничего не меняет, только читает.
ExecStart=/bin/bash ${SELF_DIR}/contract_check.sh ${NODE_DIR_FOR_WATCHDOG}
EOF
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

# 4b. Входы Xray в файрволе хоста.
#
# Порт 443 однажды уже оказался закрыт — правилом, поставленным когда-то для
# страницы отказа, — и Xray выглядел сломанным: изнутри всё работало, снаружи
# тишина. Запасные входы повторили бы эту историю, если бы до них не
# достучаться. Поэтому открываем явно и здесь же, рядом с остальной настройкой
# хоста: правило переживает перезагрузку и не требует помнить о нём.
#
# ufw есть не на всех нодах — отсутствие не считаем бедой.
if command -v ufw >/dev/null 2>&1; then
    for XPORT in 443 2053 2083; do
        ufw allow "$XPORT/tcp" >/dev/null 2>&1 || true
    done
    echo "[maintenance] Входы Xray разрешены в файрволе: 443, 2053, 2083."
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

# 5. Применяем всё. (SSH-порт закрепляется в install.sh обычным sshd — здесь не трогаем.)
systemctl daemon-reload 2>/dev/null || true
systemctl restart apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true
systemctl restart systemd-journald 2>/dev/null || true
systemctl enable --now vpn-cleanup.timer 2>/dev/null || true

echo "[maintenance] Настроено: обновления вс ~03:00 перед плановым ребутом, потолок journald 200M, недельная уборка (докер, журналы, кэш пакетов, старые ядра) с проверкой хоста (вс ~05:00), сторож узла запущен."
