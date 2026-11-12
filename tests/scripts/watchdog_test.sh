#!/bin/bash
# Сторож узла на подставных docker/systemctl/reboot: что он делает при какой беде.
#
#   bash tests/scripts/watchdog_test.sh
#
# Ничего настоящего не трогает: команды подменены заглушками, которые только
# записывают, что их позвали.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FAIL=0
ok()  { echo "  ок   $*"; }
bad() { echo "  ПЛОХО $*"; FAIL=1; }

run_case() {   # $1 = имя, $2 = что сломано: handshake | api
    local T; T=$(mktemp -d)
    mkdir -p "$T/bin" "$T/node/volumes/flags"
    echo "services: { ru_wireguard: {} }" > "$T/node/docker-compose.yml"
    touch "$T/node/volumes/flags/watchdog.armed"       # узел уже бывал здоров
    local CALLS="$T/calls"
    cat > "$T/bin/docker" <<EOF
#!/bin/bash
echo "docker \$*" >> "$CALLS"
case "\$*" in
  "inspect -f {{.State.Running}} vpn_wireguard") echo true ;;
  *"curl -sf --max-time 5 http://127.0.0.1:8000/api/health"*) [ "$2" = api ] && exit 7; exit 0 ;;
  *"wg show wg0 dump"*)
     printf 'priv\tpub\t51820\toff\n'
     printf 'k\t(none)\t1.2.3.4:51820\t10.13.13.254/32\t%s\t0\t0\t25\n' "\$(( \$(date +%s) - 3600 ))" ;;
  *"ipset list ru_nets"*) echo 500 ;;
esac
exit 0
EOF
    printf '#!/bin/bash\necho "systemctl $*" >> "%s"\n[ "$1" = is-active ] && exit 3\nexit 0\n' "$CALLS" > "$T/bin/systemctl"
    printf '#!/bin/bash\necho "reboot" >> "%s"\n' "$CALLS" > "$T/bin/reboot"
    printf '#!/bin/bash\nexit 1\n' > "$T/bin/pgrep"
    chmod +x "$T/bin/"*
    # reboot в сторже вызывается по полному пути — подменяем и его.
    sed "s#/usr/sbin/reboot#$T/bin/reboot#" "$ROOT/scripts/vpn_watchdog.sh" > "$T/wd.sh"
    PATH="$T/bin:$PATH" WATCHDOG_NODE_DIR="$T/node" WATCHDOG_INTERVAL=0 \
        timeout 8 bash "$T/wd.sh" >/dev/null 2>&1
    echo "$T"
}

echo "=== сосед не отвечает (рукопожатие старое), своё в порядке"
T=$(run_case neighbour handshake)
grep -q "compose restart ru_wireguard" "$T/calls" && ok "свой контейнер перезапущен (L2)" || bad "L2 не было"
grep -q "systemctl restart docker" "$T/calls" && bad "перезапускал docker из-за соседа" || ok "docker не трогал"
grep -q "^reboot" "$T/calls" && bad "перезагружал сервер из-за соседа" || ok "сервер не перезагружал"
grep -q "жду соседа" "$T/node/volumes/flags/watchdog.log" && ok "в журнале — ждёт соседа" || bad "в журнале нет причины"

echo "=== своя беда (панель не отвечает)"
T=$(run_case own api)
grep -q "systemctl restart docker" "$T/calls" && ok "лестница дошла до перезапуска docker (L3)" || bad "L3 не было"

[ "$FAIL" = 0 ] && echo "ВСЁ ПРОШЛО" || { echo "ЕСТЬ ПРОВАЛЫ"; exit 1; }
