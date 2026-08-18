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
# Авто-обновления — ТОЛЬКО security-патчи и БЕЗ авто-ребута (чтобы обновления не ломали
# VPN-стек и нода сама не уходила в перезагрузку). Крупные апгрейды всех пакетов делаются
# только вручную (apt upgrade), автоматика их не трогает.
cat > /etc/apt/apt.conf.d/52vpn-unattended <<'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::Automatic-Reboot "false";
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

mkdir -p /etc/systemd/system/apt-daily-upgrade.timer.d
cat > /etc/systemd/system/apt-daily-upgrade.timer.d/override.conf <<'EOF'
[Timer]
OnCalendar=
OnCalendar=*-*-* 03:00
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
cat > /etc/systemd/system/vpn-cleanup.service <<'EOF'
[Unit]
Description=VPN node weekly cleanup (docker + journald)

[Service]
Type=oneshot
ExecStart=/usr/bin/docker system prune -af
ExecStart=/usr/bin/journalctl --vacuum-time=7d
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

# 5. Применяем всё. (SSH-порт закрепляется в install.sh обычным sshd — здесь не трогаем.)
systemctl daemon-reload 2>/dev/null || true
systemctl restart apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true
systemctl restart systemd-journald 2>/dev/null || true
systemctl enable --now vpn-cleanup.timer 2>/dev/null || true

echo "[maintenance] Настроено: ночные апдейты (~02:30/03:00), потолок journald 200M, еженедельная очистка (вс ~05:00, локальное время)."
