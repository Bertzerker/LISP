# Contagion and Brink dedicated servers

Both are available in the alphabetically sorted portal at
https://192.168.8.138/servers/. All 21 previously available games remain present.
Installed game files and Steam originals remain private on the Linux PC.

| Game | Installed maps | Modes | Ports per match |
| --- | --- | --- | --- |
| Contagion | 83 from VPK and loose map files | Escape, Extraction, Hunted, Horde Mode, Flatline, Panic | One game UDP / RCON TCP port |
| Brink | 10 from SDMD2 map indexes, including installed DLC | Objective, Stopwatch | Two UDP ports: game and game+1 query |

Cooperative Contagion player limits are 2/4/6/8; Hunted supports up to 16.
Brink supports 2/4/6/8/10/12/16. Maps are filtered by the Contagion mode prefix.
Join/admin passwords are optional, private and unique to each match. Only its
creator or a portal admin may stop a match. Two instances of either game passed
live tests; Brink uses 27015/16 and 27017/18 within the existing approved range.
No game firewall rules changed. Brink's separate authentication socket is
reserved locally; no incoming LAN exception was opened for it.

## Runtime and importing

The completed official Steam dedicated downloads are apps 293030 and 72780.
Stage them with `sudo bash scripts/import-steam-extras.sh /path/to/steamapps`.
The original Steam installations are never overwritten. Contagion's installed
Linux depot lacks its engine libraries; the script uses anonymous SteamCMD to
validate its official Windows server depot in the private template. It must
finish with `Success! App '293030' fully installed.`

Both private engines use stock Wine with native Steam DLL overrides and separate
instance prefixes/configuration. Proton's Steam bridge caused an assertion with
these dedicated builds. Brink's original 2011 Steam libraries stalled startup;
its private Steam.dll/steamclient.dll/tier0_s.dll/vstdlib_s.dll were refreshed
from the current official Contagion dedicated depot. The old copies remain at
`servers/install-media/brink-steam-sdk-original`. Full game assets are preserved.
Contagion starts with `-steam` and `sv_lan 0`; its native Steam server query
then works over the LAN without a logged-in desktop Steam process. Brink uses
`si_onlineMode 3`, explicit game/query ports and native game RCON. Run engines
only as lanserver. A classic Wine prefix and stock `/usr/bin/wine` are required.

The import script stages files; real paired tests must pass before a
`.lisp-installed` marker is created. Live test: `tests/test_steam_extras_live.py`.
Use only free approved ports and stop only test-owned instances.

## Join and administration

Use **Join** in the match card for the game console connection command.
Contagion also offers a Steam launch link (client app 238430). Brink's Steam
client is app 22350. With join protection set, enter `password YOUR_JOIN_PASSWORD`
in the game's console before connecting.

Contagion administration: `rcon_address IP:PORT`,
`rcon_password YOUR_ADMIN_PASSWORD`, then `rcon COMMAND`.
Brink administration: `net_clientRemoteConsoleAddress IP:PORT`,
`net_clientRemoteConsolePassword YOUR_ADMIN_PASSWORD`, then `rcon COMMAND`.
Never put passwords in shared documents or downloads.

## Results — 2026-10-09

Two Contagion servers (Escape/Barlowe and Extraction/Aurora Estates Christmas)
and two Brink servers (Objective/Aquarium and Stopwatch/Container City) passed
real readiness, selected maps, eight-player limits and advertised join protection.
Actual Windows LAN queries and wrong/correct RCON passwords passed. Correct
RCON read back the configured join passwords; Brink also reported its selected
rules. Independent stopping passed. Authenticated production portal tests passed
two instances, creator ownership, readiness, Join/admin guidance and independent
stop for each game. All owned test matches were stopped. Game client joining
and gameplay have not been tested.

Results: `outputs/Steam-contagion-validation.json`,
`outputs/Steam-brink-validation.json`, `outputs/Steam-extras-portal-validation.json`.
Brink's bundled Windows Dedicated Server 1.1 PDF describes its native settings.
Primary reference: [Splash Damage's dedicated-server announcement](https://forums.splashdamage.com/t/brink-dedicated-server-files-available/132097).
