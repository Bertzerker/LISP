Quake Live

Half Life Cross Product

Jabroni Brawl: Episode 3

Half Life (with mods)

Half Life 2 (with mods)

Left for Dead 2 (with mods)
Unreal Tournament 2004 (with mutators) https://linuxgsm.com/servers/ut2k4server/

Unreal Tournament (with mutators)

Team Fortress 2 https://wiki.teamfortress.com/wiki/Linux\_dedicated\_server

Soldier of Fortune 2 Gold https://www.sof2.org/download.php?id=3597\&current=1

Star Wars Battlefront 2



Wolfenstein: Enemy Territory — ET: Legacy https://github.com/etlegacy/etlegacy-snap

Call of Duty implementation update — 2026-10-06:

* Black Ops II multiplayer (Plutonium): enabled; two isolated servers, maps,
modes, player limits, join protection, LAN RCON and independent stopping
validated. Actual player joining remains untested.
* Modern Warfare 2 (IW4x): enabled after two-instance engine/LAN/RCON tests and
authenticated portal start/stop. The real browser launcher also passed two
concurrent protected matches, Join instructions and independent stopping.
* Modern Warfare 3: hidden; Steam refused anonymous access to required legacy
depots. See docs/MW3-STEAM-FILES.md for licensed download instructions.
* Black Ops: enabled after fresh two-instance server, map/mode/player-limit,
join-protection, local/LAN RCON, independent-stop and authenticated portal
launch/ownership/readiness/stop checks. Player connection tests were explicitly
skipped at the user’s request. Join/Stop controls are available.
* MW3’s installed current official server also reports local dedicated-server
functionality temporarily disabled; its direct engine attempt exited without
a ready server. The prepared Plutonium adapter needs legacy 32-bit assets.
No client connection test is required for publication after server checks pass.
* World at War: enabled after two-instance Airfield/TDM and Asylum/FFA tests,
LAN queries and RCON passwords, independent stopping and authenticated
portal publication/start/ownership/stop.
* World at War: supplied DVD, patches 1.1–1.7, German 1.4.1 update and uncut
patch were applied privately. Mixed-language assets failed the live font
limit check; checksum-verified dedicated data repaired the private copy,
and the new live tests passed. Original and patched data remain backed up.
* The user approved Plutonium query/RCON allowlisting for 192.168.8.0/24 while
retaining admin passwords and the existing LAN-only firewall.



Wolfenstein 2009

Star Trek Elite Force

Star Wars Jedi Academy

Alien vs Predator 2 Primal Hunt

## Classic dedicated-server additions — 2026-10-08

Elite Force (native cMod 1.30), Jedi Academy (native OpenJK), Wolfenstein 2009
(patched Lite Server/Wine) and Primal Hunt (dedicated server/Wine plus supplied
Master Server Patch 1.1) are enabled. All passed two-instance engine and
authenticated portal launch/ownership/readiness/independent-stop checks.
Windows LAN queries passed; incorrect/correct RCON passwords passed for Elite
Force, Jedi Academy and Wolfenstein. Primal Hunt's native controller/join
credentials were checked privately, and all six modes passed actual LAN queries.
Its in-game controller authentication and actual player joining are untested.
No firewall change; originals and all 17 previously available games preserved.
See docs/CLASSIC-GAMES.md and outputs/Classic-games-status.md.

## Contagion and Brink — 2026-10-09

Both completed Steam dedicated downloads are integrated and enabled. Contagion
has 83 installed maps across six modes; Brink has 10 maps and two modes. Each
passed two isolated instances, actual Windows LAN queries, join protection,
wrong/correct admin passwords and independent stop. Two-instance production
portal ownership/readiness/stop passed. Game list is alphabetical. All 21 prior
games remain present. No additional game firewall rule. Player joining is untested.
See docs/STEAM-EXTRAS.md and outputs/Steam-extras-portal-validation.json.

## Persistent survival games and server lifecycle — 2026-10-09

Project Zomboid (Steam app 380870, build 25485538) and 7 Days to Die
(app 294420, build 25661908) use independent private copies of the completed
Steam installations. Saved worlds belong to their creator, preserve progress
and are selectable only with the matching build. Old Zomboid worlds remain intact.
My Servers has owner/admin Stop and Restart with durable entries and settings;
Game Servers retains launch and Join without management/delete controls.
Six active servers are allowed; 32 new game ports make 36 choices, 27015–27050.
Additional UDP/TCP game and TCP admin ranges are allowed only from the LAN.
7 Days uses SteamID64 permissions for in-game administration, with its admin
password protecting the native Telnet console. Actual player gameplay is untested.
See docs/SURVIVAL.md, docs/MY-SERVERS.md and outputs/Survival-status.md.

Stopped entries also have owner/admin Delete entry and recoverable Restore on
My Servers; deletion keeps saved worlds and never deletes Steam/game files.
