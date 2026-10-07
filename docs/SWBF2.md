# Star Wars Battlefront II (2005)

The original Windows dedicated server is installed on the Linux LAN PC and available at [Game servers](http://192.168.8.138/servers/) as **Star Wars Battlefront II (2005)**. It runs without rendering or sound through the PC's system-wide Proton CachyOS Wine runtime and a private virtual display. It does not need an interactive Steam session.

## Start, join and stop

Choose the game, player limit, mode and map, optionally set join/admin passwords, and select Start server. The map choices come from the installed `data/_LVL_PC/mission.lvl`, filtered for the selected mode. Location and era are included in map labels. Conquest, two-flag CTF, one-flag CTF, Space Assault, Hunt and Hero Assault are available where installed missions support them. The current launcher offers 2–32 player slots, 30 server ticks per second and four AI units per team in supported modes.

Wait for running status, then open the original 2005 game, Multiplayer → LAN, and select **LISP Battlefront II - PORT**. Allow up to 30 seconds for the game browser to populate. Enter the join password if prompted. The portal's Join button displays these instructions and copies the address; it cannot launch and connect this old game automatically. See the [original game manual](https://cdn.akamai.steamstatic.com/steam/apps/6060/manuals/BF2_Manual-English.pdf).

For in-game administration, open global chat with Ctrl+T and enter `/admin /login YOUR_ADMIN_PASSWORD`. Then use `/admin /players`, `/admin /maps` or `/admin /nextmap`. See the [2005 remote administration reference](https://swbf2stats.net/downloads/SWBF2_RemoteAdminRef_Nov2005.pdf). Both password fields are limited to 15 characters to avoid the original engine's observed truncation. Readiness uses native TCP RCON; returned password values are discarded. When the admin field is blank, the controller generates a private random status credential that is not exposed to players or returned by the API.

Use Stop server in the portal to end a match. Each match has its own game copy, settings, log, Wine prefix and virtual display. Multiple matches of the same game use distinct game ports within 27015–27018. Stopping one kills only its private Wine services and removes its instance directory. Total portal capacity remains four matches across all games. The existing `lan-server` command supports `--game swbf2`, the selected mission as `--map`, and `--ask-passwords`; use its help for start/stop syntax.

## Network and compatibility

Game traffic uses UDP 27015–27018 and native RCON uses TCP on the same selected port; these already have LAN-scoped rules. LAN discovery uses shared UDP 3656. Both simultaneous instances successfully bound that listener. After user approval, UDP 3656 is allowed only from 192.168.8.0/24 for LAN discovery. No router forwarding is needed.

The package is the original v1.1 dedicated installer from [ModDB](https://www.moddb.com/games/star-wars-battlefront-ii/downloads/star-wars-battlefront-ii-v11-dedicated-server), supplied in the project's Game Files folder. Its MD5 is `7dff4d332505269810fd7313c44a944d` and size is 161,902,200 bytes. The executable's RCON status reports version **1.00**, despite the package's v1.1 label. A real player connection has not yet been tested. In particular, current Steam/GOG releases may differ from this original server: verify your actual client through LAN before relying on it for a party.

## Reinstall on another Linux PC

Install the normal LISP portal first. On CachyOS/Arch, prerequisites are system-wide Proton CachyOS, `xorg-server-xvfb` (including `xauth`) and `unshield`. The installed runtime is `/usr/share/steam/compatibilitytools.d/proton-cachyos-slr/files`; a compatible alternate runtime can be configured with `LISP_SWBF2_RUNTIME` for both installer and controller service. Its `bin/wine`, `bin/wineserver` and `share/default_pfx` must exist. Generic system Wine 11.19 failed to load this old executable in testing; this installation uses the tested Proton runtime.

With no matches running, copy the installer onto that host and run:

```sh
sudo python3 scripts/install-swbf2.py /path/swbattlefrontiipcserver_v1_1.exe
```

The installer checks the package checksum, extracts its embedded InstallShield cabinets without running a GUI and creates `templates/swbf2` plus `templates/swbf2-wine-prefix` under the configured server root. Proton's default prefix contains relative DLL symlinks; these must be dereferenced before relocating the seed. Later per-match copies preserve their DOS-drive symlinks. Deploy `adapters.py`, `swbf2_adapter.py`, `run_swbf2.py` and `portal.py` via the normal installer. Never restart the controller during player matches. The installer does not change firewall rules. Source packages exclude game files, Wine binaries, prefixes and live credentials.

## Verification

Two portal-launched instances loaded `tat2g_con` and `cor1c_ctf` concurrently with different player limits and join/admin passwords. Native RCON accepted each correct password and rejected an incorrect one. Mode/map mismatch was rejected by the API. Stopping the first preserved the second, and owned test matches were cleaned up. The controller's systemd restrictions remained enabled. Initial Wine setup can take around a minute on this mini PC; a process being present alone does not count as running until native status reports a loaded installed mission. `tests/test_swbf2.py` repeats the live two-instance checks when two slots are free.
