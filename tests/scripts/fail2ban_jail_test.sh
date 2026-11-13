#!/bin/bash
# fail2ban из обслуживания хоста: бан на настоящий порт SSH, журнал systemd.
#
#   docker run --rm -v "$PWD:/r:ro" ubuntu:24.04 bash /r/tests/scripts/fail2ban_jail_test.sh
#
# Пишет в /etc/fail2ban — гонять только в одноразовом контейнере.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FAIL=0
ok()  { echo "  ок   $*"; }
bad() { echo "  ПЛОХО $*"; FAIL=1; }

T=$(mktemp -d); mkdir -p "$T/bin"
PORT_FILE="$T/port"; echo 23232 > "$PORT_FILE"
CALLS="$T/calls"
printf '#!/bin/bash\n[ "$1" = -T ] && echo "port $(cat %s)"\n' "$PORT_FILE" > "$T/bin/sshd"
printf '#!/bin/bash\necho "systemctl $*" >> %s\nexit 0\n' "$CALLS" > "$T/bin/systemctl"
printf '#!/bin/bash\nexit 0\n' > "$T/bin/fail2ban-client"
printf '#!/bin/bash\nexit 0\n' > "$T/bin/python3"     # «python3-systemd есть»
chmod +x "$T/bin/"*
sed -n '/^# 4c\. fail2ban/,/^# 5\. Сторож узла/p' "$ROOT/scripts/ensure_host_maintenance.sh" > "$T/f2b.sh"
F=/etc/fail2ban/jail.d/zz-vpn-sshd.local

echo "=== порт SSH 23232"
PATH="$T/bin:$PATH" bash "$T/f2b.sh" >/dev/null
grep -qx "port = 23232" "$F" && ok "бан — на порт SSH" || bad "порт не тот: $(grep port "$F")"
grep -qx "backend = systemd" "$F" && ok "журнал — systemd, без auth.log" || bad "нет backend = systemd"
grep -q "restart fail2ban" "$CALLS" && ok "fail2ban перезапущен под новую настройку" || bad "не перезапущен"

echo "=== второй прогон, ничего не менялось"
: > "$CALLS"
PATH="$T/bin:$PATH" bash "$T/f2b.sh" >/dev/null
grep -q "restart fail2ban" "$CALLS" && bad "перезапускал без нужды" || ok "лишнего перезапуска нет"

echo "=== порт сменили руками"
echo 40022 > "$PORT_FILE"
PATH="$T/bin:$PATH" bash "$T/f2b.sh" >/dev/null
grep -qx "port = 40022" "$F" && ok "подхватил новый порт" || bad "остался старый: $(grep port "$F")"

[ "$FAIL" = 0 ] && echo "ВСЁ ПРОШЛО" || { echo "ЕСТЬ ПРОВАЛЫ"; exit 1; }
