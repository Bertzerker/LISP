#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
root=/srv/lan-party/servers
python3 - <<'PY'
import ctypes,json,urllib.request
ctypes.CDLL('libcurl-gnutls.so.4') # TF2's 64-bit replay module needs the GnuTLS ABI.
with urllib.request.urlopen('http://127.0.0.1:8787/api/servers',timeout=3) as r:
    assert not json.load(r)['servers'],'Stop running matches before updating templates.'
PY
log=$(mktemp /tmp/lisp-steam-install.XXXXXX)
trap 'rm -f -- "$log"' EXIT
for spec in tf2:232250 hl2dm:232370; do
 game=${spec%:*}; app=${spec#*:}
 mkdir -p "$root/templates/$game"
 chown lanserver:lanserver "$root/templates/$game"
 rm -f -- "$root/templates/$game/.lisp-installed"
 runuser -u lanserver -- env HOME="$root" "$root/steamcmd/steamcmd.sh" +@sSteamCmdForcePlatformType linux +force_install_dir "$root/templates/$game" +login anonymous +app_update "$app" validate +quit | tee "$log"
 grep -Fq "Success! App '$app' fully installed." "$log"
 if [[ $game == tf2 ]]; then
  [[ -x "$root/templates/$game/srcds_run_64" && -f "$root/templates/$game/bin/linux64/replay_srv.so" ]]
 else
  [[ -x "$root/templates/$game/srcds_run" && -f "$root/templates/$game/hl2mp/gameinfo.txt" ]]
 fi
 touch "$root/templates/$game/.lisp-installed"
 chown lanserver:lanserver "$root/templates/$game/.lisp-installed"
done
