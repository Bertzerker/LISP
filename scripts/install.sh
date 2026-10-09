#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run this installer with sudo.'; exit 1; }
cd "$(dirname "$0")/.."
LAN_HOST=${LAN_HOST:-192.168.8.138}
LAN_CIDR=${LAN_CIDR:-192.168.8.0/24}
UPLOAD_USER=${UPLOAD_USER:-robert}
python3 - "$LAN_HOST" "$LAN_CIDR" <<'PY'
import ipaddress,sys
ipaddress.IPv4Address(sys.argv[1]); ipaddress.IPv4Network(sys.argv[2])
PY
id "$UPLOAD_USER" >/dev/null
for tool in nginx python3 systemctl; do command -v "$tool" >/dev/null; done
id lanserver >/dev/null 2>&1 || useradd --system --create-home --home-dir /srv/lan-party/servers --shell /usr/bin/nologin lanserver
install -d -m 755 /srv/lan-party /srv/lan-party/site /srv/lan-party/site/downloads /srv/lan-party/site/servers /opt/lan-portal
install -d -o "$UPLOAD_USER" -m 755 /srv/lan-party/files
install -d -o lanserver -g lanserver /srv/lan-party/servers/instances /srv/lan-party/servers/quakelive /srv/lan-party/servers/steamcmd
bash scripts/setup-steam-runtime.sh
install -m 644 src/adapters.py src/unreal_adapter.py src/etlegacy_adapter.py src/zomboid_adapter.py src/sevendays_adapter.py src/swbf2_adapter.py src/run_swbf2.py src/cod_adapter.py src/run_cod.py src/classic_adapter.py src/classic_windows_adapter.py src/steam_extras_adapter.py src/rez_index.py src/run_classic_wine.py /opt/lan-portal/
install -m 644 src/portal.py src/credits.py src/server_metrics.py src/engine_exec.py src/network_meter.py /opt/lan-portal/
install -d /etc/systemd/system/lisp-network-meter.service.d
printf '[Service]\nEnvironment=LISP_METER_NETWORKS=%s\n' "$LAN_CIDR" > /etc/systemd/system/lisp-network-meter.service.d/network.conf
install -m 755 src/generate_index.py /usr/local/bin/lan-party-index
install -m 755 scripts/lan-server /usr/local/bin/lan-server
install -d -m 755 /srv/lan-party/site/login
install -m 644 web/login.html /srv/lan-party/site/login/index.html
install -m 644 web/login.js web/account-controls.js web/forum-account.js /srv/lan-party/site/
install -m 644 web/servers.html /srv/lan-party/site/servers/index.html
install -d -m 755 /srv/lan-party/site/my-servers
install -m 644 web/my-servers.html /srv/lan-party/site/my-servers/index.html
install -m 644 web/server-list.js web/my-servers.js /srv/lan-party/site/
install -m 644 web/portal.css web/servers.js /srv/lan-party/site/
if [[ -f /etc/nginx/lan-party.conf ]]; then cp -a /etc/nginx/lan-party.conf /etc/nginx/lan-party.conf.previous; fi
sed "s|192.168.8.0/24|$LAN_CIDR|g" config/nginx.conf > /etc/nginx/lan-party.conf
install -m 644 config/*.service config/*.timer /etc/systemd/system/
install -d /etc/systemd/system/lan-portal.service.d
printf '[Service]\nEnvironment=LISP_ALLOWED_HOSTS=%s,127.0.0.1,localhost\nEnvironment=LISP_BIND_IP=%s\n' "$LAN_HOST" "$LAN_HOST" > /etc/systemd/system/lan-portal.service.d/network.conf
bash scripts/install-network-chat.sh
/usr/bin/python3 /usr/local/bin/lan-party-index
nginx -t -c /etc/nginx/lan-party.conf
systemctl daemon-reload
systemctl enable lan-portal.service lan-party-web.service lan-party-index.timer lisp-keep-awake.service
systemctl restart lan-portal.service
systemctl start lan-party-web.service lan-party-index.timer lisp-keep-awake.service
systemctl reload lan-party-web.service
# Firewall rules are managed separately; this installer never changes them.
echo "Portal ready at http://$LAN_HOST/"
