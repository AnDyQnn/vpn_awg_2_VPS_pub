#!/bin/bash
# Продление сертификата узла: провал certbot не выдаётся за успех.
#
#   docker run --rm -v "$PWD:/r:ro" ubuntu:24.04 bash /r/tests/scripts/cert_renew_test.sh
#
# Подменяет certbot и пишет в /etc/letsencrypt — только в одноразовом контейнере.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FAIL=0
ok()  { echo "  ок   $*"; }
bad() { echo "  ПЛОХО $*"; FAIL=1; }

command -v openssl >/dev/null || { apt-get update -qq >/dev/null && apt-get install -y -qq openssl >/dev/null 2>&1; }

NODE=$(mktemp -d)/VPS_RU; mkdir -p "$NODE/volumes/certs" "$NODE/volumes/flags"
LIVE=/etc/letsencrypt/live/vpn-node-ip; mkdir -p "$LIVE"
openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=203.0.113.7" \
    -keyout "$LIVE/privkey.pem" -out "$LIVE/fullchain.pem" >/dev/null 2>&1
cp "$LIVE/fullchain.pem" "$NODE/volumes/certs/fullchain.pem"

mkdir -p /opt/certbot-ip/bin
fake_certbot() {   # $1 = код выхода renew
    cat > /opt/certbot-ip/bin/certbot <<EOF
#!/bin/bash
[ "\$1" = "--version" ] && { echo "certbot 5.8.0"; exit 0; }
if [ "$1" = 0 ]; then echo "Certificate not yet due for renewal"; exit 0; fi
echo "Failed to renew certificate vpn-node-ip with error: Connection refused on port 80"
exit $1
EOF
    chmod +x /opt/certbot-ip/bin/certbot
}
st() { python3 -c "import json;print(json.load(open('$NODE/volumes/flags/public_sub.json'))['$1'])" 2>/dev/null \
       || sed -n "s/.*\"$1\":\"\([^\"]*\)\".*/\1/p" "$NODE/volumes/flags/public_sub.json"; }

echo "=== certbot: продлевать рано (код 0)"
fake_certbot 0
bash "$ROOT/scripts/public_sub.sh" renew "$NODE" >/dev/null 2>&1
[ "$(st state)" = "on" ] && ok "состояние on" || bad "состояние $(st state)"

echo "=== certbot: продление упало (код 1)"
fake_certbot 1
bash "$ROOT/scripts/public_sub.sh" renew "$NODE" >/dev/null 2>&1
[ "$(st state)" = "warning" ] && ok "состояние warning, а не on" || bad "состояние $(st state)"
st msg | grep -q "Connection refused" && ok "в сообщении причина из лога certbot" || bad "причины нет: $(st msg)"
[ -s "$NODE/volumes/certs/fullchain.pem" ] && ok "действующий сертификат на месте" || bad "сертификат пропал"
grep -q '"until":[1-9]' "$NODE/volumes/flags/public_sub.json" && ok "срок для бота посчитан" || bad "нет срока"

[ "$FAIL" = 0 ] && echo "ВСЁ ПРОШЛО" || { echo "ЕСТЬ ПРОВАЛЫ"; exit 1; }
