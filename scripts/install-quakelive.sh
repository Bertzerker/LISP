#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo after install.sh.'; exit 1; }
id lanserver >/dev/null
root=/srv/lan-party/servers
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
curl --fail --location https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz -o "$tmp"
chmod 644 "$tmp"
runuser -u lanserver -- tar -xzf "$tmp" -C "$root/steamcmd"
runuser -u lanserver -- env HOME="$root" "$root/steamcmd/steamcmd.sh" +@sSteamCmdForcePlatformType linux +force_install_dir "$root/quakelive" +login anonymous +app_info_update 1 +app_update 349090 validate +quit

bash "$(dirname "$0")/setup-steam-runtime.sh"
