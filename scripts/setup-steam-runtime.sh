#!/usr/bin/env bash
set -euo pipefail
# Steam server processes use this service account's SDK runtime, not a desktop login.
for bits in 32 64; do
    sdk=/srv/lan-party/servers/.steam/sdk$bits
    install -d -o lanserver -g lanserver "$sdk"
    for candidate in /srv/lan-party/servers/steamcmd/linux$bits/steamclient.so /srv/lan-party/servers/quakelive/linux$bits/steamclient.so; do
        if [[ -f "$candidate" ]]; then ln -sfn "$candidate" "$sdk/steamclient.so"; break; fi
    done
done
