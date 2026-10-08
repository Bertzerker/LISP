#!/bin/bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
cd "$(dirname "$0")/.."
host=${LAN_HOST:-192.168.8.138}
cidr=${LAN_CIDR:-192.168.8.0/24}
pacman -S --needed --noconfirm mumble-server npm
id lispvoice >/dev/null 2>&1 || useradd --system --user-group --no-create-home --shell /usr/bin/nologin lispvoice
install -d -m 750 -o root -g lispvoice /etc/lisp/mumble
install -d -m 755 /opt/lisp-mumble
python3 - "$host" <<'PY'
from pathlib import Path
import secrets,sys,grp,os
folder=Path('/etc/lisp/mumble');group=grp.getgrnam('_mumble-server').gr_gid;viewgroup=grp.getgrnam('lispvoice').gr_gid
for name in ('view-secret','write-secret','superuser-password'):
 p=folder/name
 if not p.exists():p.write_text(secrets.token_urlsafe(36)+'\n')
 p.chmod(0o640 if name=='view-secret' else 0o600);os.chown(p,0,viewgroup)
config=Path('/etc/mumble/mumble-server.ini')
if not (folder/'original-server.ini').exists():
 (folder/'original-server.ini').write_bytes(config.read_bytes());(folder/'original-server.ini').chmod(0o600)
config.write_text(f'''database=/var/lib/mumble-server/mumble-server.sqlite
host={sys.argv[1]}
port=64738
users=100
bandwidth=72000
welcometext=Welcome to LAN Zocken voice chat.
registerName=LAN Zocken Voice
serverpassword=
logfile=
ice="tcp -h 127.0.0.1 -p 6502"
icesecretread={(folder/'view-secret').read_text().strip()}
icesecretwrite={(folder/'write-secret').read_text().strip()}
''')
config.chmod(0o640);os.chown(config,0,group)
PY
# Native credentials remain private on the host, outside the source archive.
secret=$(cat /etc/lisp/mumble/superuser-password)
printf '%s\n' "$secret" | sudo -u _mumble-server mumble-server -ini /etc/mumble/mumble-server.ini -readsupw >/dev/null 2>&1
unset secret
install -m 644 config/mumble-package.json /opt/lisp-mumble/package.json
cd /opt/lisp-mumble
npm install --omit=dev --ignore-scripts --no-audit --no-fund
slice2js -I/usr/share/ice/slice --output-dir /opt/lisp-mumble /usr/share/mumble-server/MumbleServer.ice
cd - >/dev/null
install -m 644 src/mumble_view.js scripts/setup-mumble.js /opt/lisp-mumble/
install -m 644 config/lisp-mumble-view.service /etc/systemd/system/
install -m 644 config/mumble-locations.conf /etc/nginx/lisp-community/portal/mumble.conf
systemctl daemon-reload
systemctl enable --now mumble-server
node /opt/lisp-mumble/setup-mumble.js
systemctl enable --now lisp-mumble-view
ufw allow from "$cidr" to "$host" port 64738 proto tcp comment LISP-Mumble-LAN
ufw allow from "$cidr" to "$host" port 64738 proto udp comment LISP-Mumble-LAN
nginx -t -c /etc/nginx/lan-party.conf
systemctl reload lan-party-web
echo 'Mumble ready on LAN port 64738. SuperUser credential: /etc/lisp/mumble/superuser-password (root only).'
