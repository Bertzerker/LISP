# Additional LAN game servers

All four additions are installed, enabled and validated on 192.168.8.138. Open http://192.168.8.138/servers/ to select a game, players, mode, map and optional join/admin passwords.

| Game | Installed server | Maps | Modes | Stock mutators |
| --- | --- | ---: | ---: | ---: |
| Team Fortress 2 | SteamCMD 232250, native 64-bit | 238 | Map-defined | — |
| Half-Life 2: Deathmatch | SteamCMD 232370, native Linux | 8 | 2 | — |
| Unreal Tournament | OldUnreal 469f, native 64-bit | 96 | 5 | 3 |
| Unreal Tournament 2004 | OldUnreal 3374, native 64-bit | 131 | 8 | 3 |

Steam logs contained the exact successful app-install messages for both app IDs. Both OldUnreal logs reported “is now installed!”; native executables, maps and installed Unreal package/class names were checked before exposing the games. Installation markers hide incomplete templates.

## Verified behavior

Each game passed a live two-instance test with different maps, isolated ports and credentials. Stopping one left the other running. Only owned test matches were stopped, and all were removed afterward. HL2DM standard/team deathmatch settings were checked through native RCON. TF2 and HL2DM accepted the correct admin password and rejected an incorrect one; their native join-password values matched the requested settings.

Unreal's native queries reported password protection. UT2004's native rules also reported active Instagib. The installed mode and mutator classes were verified against the actual packages. UT99 selections include Instagib, low gravity and no powerups; UT2004 includes Instagib, low gravity and no adrenaline. Instance directories are private (700), and Unreal password configuration is private (600). The browser showed all four additions, mode-filtered maps, mutators, active-server Join/Stop controls and a working copy-connect-command control.

Actual player joins for these four additions and Unreal in-game `adminlogin` authentication still need a client test. The native query checks do not substitute for those client actions. Steam/Unreal Join buttons depend on the corresponding client URL handler; the copied console command remains available.

## Runtime fixes

TF2 uses `srcds_run_64`, a per-instance Steam SDK64 link and a per-instance link to its 64-bit replay module. The original template is preserved. Its replay module requires `libcurl-gnutls.so.4`; the official CachyOS `libcurl-gnutls` package was installed. Replay and automatic bots are disabled for these matches.

UT2004 reads its query port from `[URL] QueryPort`. The adapter now writes both game and query ports explicitly, avoiding the default 7778 listener when multiple matches run. Unreal instances reserve pairs within the existing LAN rules: 27015/27016 and 27017/27018. Up to two Unreal servers can run concurrently; other combinations remain subject to the portal's four slots. The legacy game+10 port is reserved against conflicts, but no additional firewall rule was added. WebAdmin, Internet uplinks and UT2004 LAN broadcast are disabled. Use the displayed address to join directly.

Unreal console connection: `open IP:PORT`, adding `?password=YOUR_PASSWORD` for protected matches. Administration: `adminlogin YOUR_ADMIN_PASSWORD`. Passwords are stored in private instance configuration, excluded from API responses and command arguments, and removed when a match is stopped.

## Reinstallation and sharing

Run the installers only when no matches are active. On CachyOS, install `libcurl-gnutls` before the Steam installer; other distributions need the equivalent GnuTLS libcurl ABI plus the documented Steam runtime libraries.

```sh
sudo bash scripts/install-more-steam.sh
sudo bash scripts/install-unreal.sh ut99 --accept-epic-terms
sudo bash scripts/install-unreal.sh ut2004 --accept-epic-terms
```

The user approved Epic's terms for both installations on this PC. A recipient must review and accept those terms themselves before using the flag. Installers require the successful completion message plus executable/content checks before creating their installation marker.

Sources: [OldUnreal Linux installers](https://github.com/OldUnreal/FullGameInstallers/tree/master/Linux) and [LinuxGSM TF2 configuration](https://github.com/GameServerManagers/LinuxGSM/blob/master/lgsm/config-default/config-lgsm/tf2server/_default.cfg).

Run `python3 tests/test_more_games_live.py GAME` from a LAN machine, choosing `tf2`, `hl2dm`, `ut99` or `ut2004`. It uses the current PC's address and creates temporary matches; allow two free Source slots or two free Unreal port pairs. It cleans up only its own matches. The protocol helper is included beside it.

The shareable source excludes Game Files, game binaries, runtime instances and credentials. Existing games, downloads, chat and network settings are preserved. The roadmap's unspecified “with mods” entries do not identify additional packages: HL2DM supplies the base game, and existing Cross Product remains available. Further third-party mods require their own server files and integration.
