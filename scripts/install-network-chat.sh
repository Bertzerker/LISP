#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
cd "$(dirname "$0")/.."
LAN_HOST=${LAN_HOST:-192.168.8.138}
LAN_CIDR=${LAN_CIDR:-192.168.8.0/24}
GATEWAY_CIDR=${GATEWAY_CIDR:-10.42.0.1/24}
GATEWAY_IP=$(python3 -c 'import ipaddress,sys; print(ipaddress.ip_interface(sys.argv[1]).ip)' "$GATEWAY_CIDR")
PARTY_CIDR=$(python3 -c 'import ipaddress,sys; print(ipaddress.ip_interface(sys.argv[1]).network)' "$GATEWAY_CIDR")
for tool in nginx python3 nmcli nft ufw busctl openssl dnsmasq; do command -v "$tool" >/dev/null || { echo "Required dependency missing: $tool"; exit 1; }; done
id lanserver >/dev/null
id lanadmin >/dev/null 2>&1 || useradd --system --home-dir /var/lib/lisp-admin --shell /usr/bin/nologin lanadmin
install -d -o lanserver -g lanserver -m 700 /srv/lan-party/chat
install -d -o lanadmin -g lanadmin -m 700 /var/lib/lisp-admin
install -d -o root -g root -m 700 /var/lib/lisp-network /etc/lisp/tls
install -d -m 755 /srv/lan-party/site/admin /srv/lan-party/site/style /opt/lan-portal
install -m 644 src/chat.py src/chat_server.py src/admin_auth.py src/admin_server.py src/network_control.py /opt/lan-portal/
install -m 644 src/accounts.py src/account_client.py src/account_server.py src/credits.py /opt/lan-portal/
install -d -m 755 /srv/lan-party/site/login
install -m 644 web/login.html /srv/lan-party/site/login/index.html
install -m 644 web/login.js web/account-controls.js web/forum-account.js /srv/lan-party/site/
install -m 644 web/admin.html /srv/lan-party/site/admin/index.html
printf 'window.LISP_GAME_HOST="%s";\n' "$LAN_HOST" > /srv/lan-party/site/server-info.js
install -m 644 web/shell.js web/personal-bar.js web/admin.js web/portal.css /srv/lan-party/site/
install -m 644 web/servers.html /srv/lan-party/site/servers/index.html
install -d -m 755 /srv/lan-party/site/my-servers
install -m 644 web/my-servers.html /srv/lan-party/site/my-servers/index.html
install -m 644 web/servers.js web/server-list.js web/my-servers.js /srv/lan-party/site/
install -m 644 style/* /srv/lan-party/site/style/
install -m 755 src/generate_index.py /usr/local/bin/lan-party-index
install -m 644 config/lisp-*.service /etc/systemd/system/
for service in lisp-chat lisp-admin lan-portal; do
  install -d "/etc/systemd/system/$service.service.d"
  printf '[Service]\nEnvironment=LISP_ALLOWED_HOSTS=%s,%s,127.0.0.1,localhost\n' "$LAN_HOST" "$GATEWAY_IP" > "/etc/systemd/system/$service.service.d/zz-lisp-hosts.conf"
done
printf 'Environment=LISP_IRC_NETWORKS=127.0.0.0/8,%s,%s\n' "$LAN_CIDR" "$PARTY_CIDR" >> /etc/systemd/system/lisp-chat.service.d/zz-lisp-hosts.conf
install -d /etc/systemd/system/lisp-network.service.d
printf '[Service]\nEnvironment=LISP_MANAGEMENT_IP=%s\nEnvironment=LISP_GATEWAY_CIDR=%s\n' "$LAN_HOST" "$GATEWAY_CIDR" > /etc/systemd/system/lisp-network.service.d/network.conf
if [[ ! -f /etc/lisp/tls/ca.crt ]]; then
  openssl req -x509 -newkey rsa:3072 -nodes -sha256 -days 3650 -keyout /etc/lisp/tls/ca.key -out /etc/lisp/tls/ca.crt -subj '/CN=LISP Local LAN Authority' -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign'
fi
if [[ ! -f /etc/lisp/tls/server.crt ]]; then
  openssl req -new -newkey rsa:3072 -nodes -keyout /etc/lisp/tls/server.key -out /etc/lisp/tls/server.csr -subj '/CN=LISP LAN Portal'
  printf 'subjectAltName=IP:%s,IP:%s,DNS:lisp.lan\nbasicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' "$LAN_HOST" "$GATEWAY_IP" > /etc/lisp/tls/server.ext
  openssl x509 -req -in /etc/lisp/tls/server.csr -CA /etc/lisp/tls/ca.crt -CAkey /etc/lisp/tls/ca.key -CAcreateserial -out /etc/lisp/tls/server.crt -days 825 -sha256 -extfile /etc/lisp/tls/server.ext
fi
chmod 600 /etc/lisp/tls/*.key
install -m 644 /etc/lisp/tls/ca.crt /srv/lan-party/site/style/lisp-lan-ca.crt
cp -a /etc/nginx/lan-party.conf /etc/nginx/lan-party.conf.before-network-chat
sed -e "s|192.168.8.0/24|$LAN_CIDR|g" -e "s|10.42.0.0/24|$PARTY_CIDR|g" config/nginx.conf > /etc/nginx/lan-party.conf
/usr/local/bin/lan-party-index
nginx -t -c /etc/nginx/lan-party.conf
systemctl daemon-reload
bootstrap_client=${SSH_CLIENT:-}
BOOTSTRAP_IP=${BOOTSTRAP_IP:-${bootstrap_client%% *}}
export BOOTSTRAP_IP
export LISP_ACCOUNT_NETWORKS="$LAN_CIDR,$PARTY_CIDR"
bash scripts/install-accounts.sh
systemctl enable --now lisp-network.service lisp-admin.service lisp-chat.service
systemctl restart lisp-admin.service lisp-chat.service
systemctl reload-or-restart lan-party-web.service
echo "Portal updated. Secure network admin: https://$LAN_HOST/admin/"
echo 'Log in at /login/ as admin using the existing network password or the initial password entered during bootstrap.'
echo 'LAN topology is unchanged. Firewall listeners are managed separately.'
