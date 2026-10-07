#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
[[ $# == 2 ]] || { echo 'Usage: install-sof2.sh sof2dedlinux101.zip retail-game.rar'; exit 1; }
binary_archive=$(realpath "$1")
retail_archive=$(realpath "$2")
id lanserver >/dev/null
command -v 7z >/dev/null
target=/srv/lan-party/servers/templates/sof2
[[ ! -e "$target" ]] || { echo 'SoF2 template already exists; stop matches and back it up before replacing it.'; exit 1; }
stage=$(mktemp -d /srv/lan-party/servers/sof2-install.XXXXXX)
trap 'rm -rf -- "$stage"' EXIT
mkdir -p "$stage/media" "$stage/template/base"
7z x -y "$retail_archive" -o"$stage/media" >/dev/null
while IFS= read -r -d '' disc; do
  7z e -y "$disc" 'Setup/base/*.pk3' -o"$stage/template/base" >/dev/null
done < <(find "$stage/media" -type f -iname '*.iso' -print0)
python3 - "$binary_archive" "$stage/template" <<'PY'
import pathlib,sys,zipfile
r=pathlib.Path(sys.argv[2])
with zipfile.ZipFile(sys.argv[1]) as z:
    for member,dest in [('sof2ded','sof2ded'),('readme.txt','readme.txt'),('update101.pk3','base/update101.pk3')]:
        (r/dest).write_bytes(z.read(member))
# The supplied server uses protocol 2003; do not mix Gold game code into it.
for name in ('update102.pk3','update103.pk3'):(r/'base'/name).unlink(missing_ok=True)
for name in ('mp.pk3','maps.pk3','models.pk3','update101.pk3'):
    assert (r/'base'/name).is_file(), 'Required retail data missing: '+name
PY
chmod 755 "$stage/template/sof2ded"
chown -R lanserver:lanserver "$stage/template"
mv "$stage/template" "$target"
echo 'SoF2 v1.01 installed. Requires matching v1.01 clients; Gold v1.03 needs its own compatible binary.'
echo 'Deploy adapters.py and restart lan-portal only when no matches are running.'
