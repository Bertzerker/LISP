#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.'; exit 1; }
[[ $# == 2 ]] || { echo 'Usage: update-sof2-gold.sh sof2dedGOLD.zip sof2gold-1.03.tar.xz'; exit 1; }
archive=$(realpath "$1")
runtime=$(realpath "$2")
echo '8bd4721b6ffe0840040b0250e2216a7b3cc333a84945c6664c18d5d0559fe3d5  '"$archive" | sha256sum -c -
echo '201e23bab04207d00ce813d001c483d9  '"$runtime" | md5sum -c -
python3 -c 'import urllib.request,json; assert not json.load(urllib.request.urlopen("http://127.0.0.1:8787/api/servers"))["servers"],"Stop matches before updating"'
root=/srv/lan-party/servers
target="$root/templates/sof2"
stage=$(mktemp -d "$root/sof2-gold.XXXXXX")
trap 'rm -rf -- "$stage"' EXIT
cp -a --reflink=auto "$target/." "$stage/"
python3 - "$archive" "$stage" <<'PY'
import pathlib,sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    pathlib.Path(sys.argv[2],'sof2ded').write_bytes(z.read('sof2ded'))
PY
lib=$(tar -tJf "$runtime" | awk '/(^|\/)libcxa\.so\.1$/ {print}')
[[ -n "$lib" ]] || { echo 'Runtime library not found'; exit 1; }
tar -xOJf "$runtime" "$lib" > "$stage/libcxa.so.1"
for update in update102.pk3 update103.pk3; do
 if [[ ! -f "$stage/base/$update" ]]; then
  cp -p "$stage/unused-gold-updates/$update" "$stage/base/$update"
 fi
done
gcc -m32 -shared -fPIC -O2 -o "$stage/lisp-dns-compat.so" "$(dirname "$0")/../src/sof2-dns-compat.c" -ldl
chmod 755 "$stage/sof2ded"
chmod 644 "$stage/libcxa.so.1"
chown -R lanserver:lanserver "$stage"
LD_LIBRARY_PATH="$stage" ldd "$stage/sof2ded" | tee "$stage/gold-runtime-check.txt"
! grep -q 'not found' "$stage/gold-runtime-check.txt"
backup="$root/sof2-backup-$(date +%Y%m%d-%H%M%S)"
mv "$target" "$backup"
mv "$stage" "$target"
trap - EXIT
echo "Gold template installed; previous template saved to $backup"
echo 'Deploy current adapters.py, then restart lan-portal only with no active matches.'
