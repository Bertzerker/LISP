#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
[[ $(uname -m) == x86_64 ]] || { echo 'This installer requires Linux x86_64.'; exit 1; }
root=/srv/lan-party/servers
target="$root/templates/etlegacy"
[[ ! -e "$target" ]] || { echo 'ET: Legacy template already exists; do not overwrite active content.'; exit 1; }
stage=$(mktemp -d "$root/templates/.etlegacy-install.XXXXXX")
# Preserve failed staging for diagnosis and resumption, never expose partial content.
curl --fail --location --retry 2 https://www.etlegacy.com/download/file/757 -o "$stage/release.tar.gz"
printf '%s  %s\n' ef1f5e8f9d6d1a8cdc197fbb598bf543 "$stage/release.tar.gz" | md5sum --check
tar -xzf "$stage/release.tar.gz" -C "$stage"
game=$(find "$stage" -mindepth 1 -maxdepth 1 -type d -name 'etlegacy*' -print -quit)
[[ -n "$game" && -x "$game/etlded.x86_64" ]]
mkdir -p "$game/etmain"
for name in pak0 pak1 pak2; do
 curl --fail --location --retry 2 "https://mirror.etlegacy.com/etmain/$name.pk3" -o "$game/etmain/$name.pk3"
done
python3 - "$game" <<'PY'
import pathlib,sys,zipfile,json,hashlib
p=pathlib.Path(sys.argv[1]);maps=set()
for file in (p/'etmain').glob('pak*.pk3'):
 with zipfile.ZipFile(file) as z:
  assert z.testzip() is None,file
  maps.update(pathlib.Path(n).stem for n in z.namelist() if n.startswith('maps/') and n.endswith('.bsp'))
assert {'oasis','goldrush','radar','railgun','battery','fueldump'}<=maps,maps
assert list((p/'legacy').glob('qagame*.so')),'Missing Legacy game module'
hashes={f.relative_to(p).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/'etmain').glob('pak*.pk3')}
(p/'lisp-install.json').write_text(json.dumps({'version':'2.86.0','archiveURL':'https://www.etlegacy.com/download/file/757','archiveMD5':'ef1f5e8f9d6d1a8cdc197fbb598bf543','packSource':'https://mirror.etlegacy.com/etmain/','packSHA256':hashes,'maps':sorted(maps)},indent=2)+'\n')
print('PASS official packs, maps and Legacy module')
PY
ldd "$game/etlded.x86_64"
if ldd "$game/etlded.x86_64" | grep -q 'not found'; then exit 1; fi
mv -- "$game" "$target"
chown -R lanserver:lanserver "$target"
touch "$target/.lisp-installed"
chown lanserver:lanserver "$target/.lisp-installed"
echo "ET: Legacy 2.86.0 installed at $target; run tests/test_etlegacy_live.py with free slots."
