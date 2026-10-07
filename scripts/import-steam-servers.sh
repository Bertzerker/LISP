#!/bin/bash
set -euo pipefail
src=${1:?Usage: import-steam-servers.sh /path/to/steamapps/common}
dst=/srv/lan-party/servers/templates
install -d -o lanserver -g lanserver "$dst"
names=('Half-Life' 'CPDS' 'Left 4 Dead 2 Dedicated Server' 'Jabroni Brawl Episode 3 Dedicated Server')
ids=(halflife crossproduct l4d2 jabroni)
for i in "${!names[@]}"; do
  [[ -d "$src/${names[$i]}" ]] || continue
  install -d -o lanserver -g lanserver "$dst/${ids[$i]}"
  cp -a --reflink=auto "$src/${names[$i]}/." "$dst/${ids[$i]}/"
  chown -R lanserver:lanserver "$dst/${ids[$i]}"
done
echo 'Dedicated-server templates imported.'

bash "$(dirname "$0")/setup-steam-runtime.sh"
