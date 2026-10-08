#!/bin/bash
# Stage owned Steam dedicated downloads; validation enables them separately.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
steamapps=${1:?Usage: import-steam-extras.sh /path/to/Steam/steamapps}
root=${LISP_SERVER_ROOT:-/srv/lan-party/servers}
for item in '72780:brink:BRINK Dedicated Server' '293030:contagion:Contagion Dedicated Server'; do
 IFS=: read -r app game folder <<< "$item"
 source="$steamapps/common/$folder"
 [[ -f "$steamapps/appmanifest_$app.acf" && -d "$source" ]] || { echo "Missing Steam download: $folder" >&2; exit 1; }
 grep -Eq '"StateFlags"[[:space:]]+"4"' "$steamapps/appmanifest_$app.acf" || { echo "Steam download incomplete: $folder" >&2; exit 1; }
 [[ ! -e "$root/templates/$game" ]] || { echo "Existing $game template: leave it intact; update privately after stopping its matches." >&2; exit 1; }
 mkdir -p "$root/templates/$game"
 cp -a --reflink=auto "$source/." "$root/templates/$game/"
 rm -f "$root/templates/$game/.lisp-installed"
 chown -R lanserver:lanserver "$root/templates/$game"
done
# The Linux Contagion depot lacks its engine. Fetch its official Windows depot
# into the private template, as the service user, without changing Steam originals.
sudo -u lanserver env HOME="$root" "$root/steamcmd/steamcmd.sh" \
 +@sSteamCmdForcePlatformType windows +force_install_dir "$root/templates/contagion" \
 +login anonymous +app_update 293030 validate +quit
# Refresh only Brink's private legacy Steam SDK with current official depot
# libraries. Keep an original backup and never alter the installed Steam games.
backup="$root/install-media/brink-steam-sdk-original"
install -d -o lanserver -g lanserver -m 700 "$backup"
for name in steamclient.dll tier0_s.dll vstdlib_s.dll Steam.dll; do
 [[ -f "$root/templates/brink/$name" ]] && cp -a "$root/templates/brink/$name" "$backup/$name"
 source="$root/templates/contagion/$name"
 [[ $name == Steam.dll ]] && source="$root/templates/contagion/engine/steam.dll"
 [[ -f "$source" ]] || { echo "Missing official Steam SDK file: $name" >&2; exit 1; }
 install -o lanserver -g lanserver -m 644 "$source" "$root/templates/brink/$name"
done
echo 'Staged Brink and Contagion. Run paired live validation before creating installed markers.'
