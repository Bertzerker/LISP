#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
[[ ${1:-} == ut99 || ${1:-} == ut2004 ]] || { echo 'Usage: install-unreal.sh ut99|ut2004 --accept-epic-terms'; exit 1; }
[[ ${2:-} == --accept-epic-terms ]] || { echo 'Review https://legal.epicgames.com/en-US/epicgames/tos and explicitly pass --accept-epic-terms if you agree.'; exit 1; }
game=$1
root=/srv/lan-party/servers
target="$root/templates/$game"
[[ ! -e "$target/.lisp-installed" ]] || { echo 'Already installed. Update the template only when matches are stopped.'; exit 1; }
install -d -o lanserver -g lanserver "$target"
installer=$(mktemp /tmp/lisp-unreal-installer.XXXXXX)
log=$(mktemp /tmp/lisp-unreal-install.XXXXXX)
trap 'rm -f -- "$installer" "$log"' EXIT
curl --fail --location "https://raw.githubusercontent.com/OldUnreal/FullGameInstallers/master/Linux/install-$game.sh" -o "$installer"
chmod 644 "$installer"
sha256sum "$installer" > "$target/installer.sha256"
# Only the reviewed Epic terms prompt is answered; desktop and application entries are skipped.
printf 'y\n' | runuser -u lanserver -- env HOME="$root" bash "$installer" --destination "$target" --ui-mode none --application-entry skip --desktop-shortcut skip | tee "$log"
grep -Fq 'is now installed!' "$log"
if [[ $game == ut99 ]]; then
 [[ -x "$target/System/ucc-bin" ]]
 find "$target/Maps" -maxdepth 1 -name '*.unr' -print -quit | grep -q .
else
 [[ -x "$target/System/UCC" ]]
 find "$target/Maps" -maxdepth 1 -name '*.ut2' -print -quit | grep -q .
fi
touch "$target/.lisp-installed"
chown lanserver:lanserver "$target/.lisp-installed"
