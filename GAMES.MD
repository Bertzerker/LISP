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

- Black Ops II multiplayer (Plutonium): enabled; two isolated servers, maps,
  modes, player limits, join protection, LAN RCON and independent stopping
  validated. Actual player joining remains untested.
- Modern Warfare 2 (IW4x): enabled after two-instance engine/LAN/RCON tests and
  authenticated portal start/stop. The real browser launcher also passed two
  concurrent protected matches, Join instructions and independent stopping.
- Modern Warfare 3: hidden; Steam refused anonymous access to required legacy
  depots. See docs/MW3-STEAM-FILES.md for licensed download instructions.
- Black Ops: enabled after fresh two-instance server, map/mode/player-limit,
  join-protection, local/LAN RCON, independent-stop and authenticated portal
  launch/ownership/readiness/stop checks. Player connection tests were explicitly
  skipped at the user’s request. Join/Stop controls are available.
- MW3’s installed current official server also reports local dedicated-server
  functionality temporarily disabled; its direct engine attempt exited without
  a ready server. The prepared Plutonium adapter needs legacy 32-bit assets.
  No client connection test is required for publication after server checks pass.
- World at War: enabled after two-instance Airfield/TDM and Asylum/FFA tests,
  LAN queries and RCON passwords, independent stopping and authenticated
  portal publication/start/ownership/stop.
- World at War: supplied DVD, patches 1.1–1.7, German 1.4.1 update and uncut
  patch were applied privately. Mixed-language assets failed the live font
  limit check; checksum-verified dedicated data repaired the private copy,
  and the new live tests passed. Original and patched data remain backed up.
- The user approved Plutonium query/RCON allowlisting for 192.168.8.0/24 while
  retaining admin passwords and the existing LAN-only firewall.
