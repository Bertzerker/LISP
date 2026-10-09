#!/bin/sh
# Apply the additional LAN-only game slots explicitly requested by the operator.
set -eu
[ "$(id -u)" = 0 ] || { echo "Run as root." >&2; exit 1; }
lan=${1:-192.168.8.0/24}
case "$lan" in 192.168.8.0/24) ;; *) echo "Use the configured LAN subnet 192.168.8.0/24." >&2; exit 1 ;; esac
ufw allow from "$lan" to any port 27019:27050 proto udp comment 'LISP additional game slots'
ufw allow from "$lan" to any port 27019:27050 proto tcp comment 'LISP additional game RCON'
ufw allow from "$lan" to any port 28019:28050 proto tcp comment 'LISP additional admin consoles'
