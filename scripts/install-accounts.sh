#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
cd "$(dirname "$0")/.."
[[ -n ${BOOTSTRAP_IP:-} ]] || { echo 'Set BOOTSTRAP_IP to the admin PC LAN address, then connect from that PC first.'; exit 1; }
id lanadmin >/dev/null
id lanserver >/dev/null
install -d -o lanadmin -g lanserver -m 700 /var/lib/lisp-accounts
install -m 644 src/accounts.py src/account_client.py src/account_server.py /opt/lan-portal/
install -m 755 scripts/account-recovery.py /usr/local/bin/lisp-account-recovery
/usr/local/bin/lisp-account-recovery bootstrap --ip "$BOOTSTRAP_IP"
install -m 644 config/lisp-accounts.service /etc/systemd/system/
install -d /etc/systemd/system/lisp-accounts.service.d
cp /etc/systemd/system/lisp-admin.service.d/zz-lisp-hosts.conf /etc/systemd/system/lisp-accounts.service.d/zz-lisp-hosts.conf
printf 'Environment=LISP_ACCOUNT_NETWORKS=%s\n' "${LISP_ACCOUNT_NETWORKS:-192.168.8.0/24,10.42.0.0/24}" >> /etc/systemd/system/lisp-accounts.service.d/zz-lisp-hosts.conf
install -d /srv/lan-party/site/accounts /srv/lan-party/site/forum
install -m 644 web/auth.js web/home.js web/accounts.js web/forum.js /srv/lan-party/site/
install -m 644 web/accounts.html /srv/lan-party/site/accounts/index.html
install -m 644 web/forum.html /srv/lan-party/site/forum/index.html
systemctl daemon-reload
systemctl enable --now lisp-accounts.service
echo 'Local accounts ready. Initial administrator name: admin.'
