# Elite Force, Jedi Academy, Wolfenstein 2009 and Primal Hunt

These four games are installed on the CachyOS LAN PC and available to signed-in
players at `/servers/`. Each match has its own game files, configuration,
passwords and, for Windows engines, its own Wine prefix. Two matches of the same
game work concurrently. Only the creator or an administrator can stop a match.

| Game | Server engine | Available modes |
| --- | --- | --- |
| Star Trek: Voyager – Elite Force | Native Linux cMod 1.30 | Free for All, Team Deathmatch, Capture the Flag |
| Star Wars Jedi Knight: Jedi Academy | Native Linux OpenJK, build `latest-2-g260c59c2` | Free for All, Duel, Power Duel, Team Deathmatch, Siege, Capture the Flag |
| Wolfenstein (2009) | Original patched Windows Lite Server through Wine; engine reports `WolfMP 1.3.344285` | Objective, Stopwatch, Team Deathmatch |
| Aliens vs Predator 2: Primal Hunt | Original Windows dedicated server through Wine, supplied Master Server Patch 1.1 | Deathmatch, Team Deathmatch, Hunt, Survivor, Overrun, Evacuation |

The map menus are built from the installed game files, including loose maps.
Elite Force uses multiplayer BSPs in `baseEF/*.pk3`; Jedi Academy retains the
`mp/` map directory in its BSP names. Wolfenstein uses `mapinfo/mp_*.md` in PK4s.
Primal Hunt uses `worlds/multi/**/*.dat` in REZ archives. Mode-specific menus
filter unsuitable map folders. Drop supported custom maps into the private
template and reload the launcher catalog. Do not modify a template during a
running match or copy an untested engine over a working installation.

## Joining and administration

Use the address and port shown on each running match. Elite Force clients need
Holomatch 1.2 or cMod; Jedi Academy clients need multiplayer 1.01 or OpenJK.
Wolfenstein clients need compatible multiplayer patches. Primal Hunt clients
need the expansion and its Master Server Patch 1.1; a base AVP2 client cannot
join an expansion match.

| Game | Join | In-game administration |
| --- | --- | --- |
| Elite Force / Jedi Academy | Console: `connect IP:PORT`; set `password YOUR_JOIN_PASSWORD` first for protected matches | `rconpassword YOUR_ADMIN_PASSWORD`, then `rcon COMMAND` |
| Wolfenstein 2009 | Console: `connect IP:PORT`; set `password YOUR_JOIN_PASSWORD` first | `net_clientRemoteConsolePassword YOUR_ADMIN_PASSWORD`, then `rcon COMMAND`; for remote administration without joining, also set `net_clientRemoteConsoleAddress IP:PORT` |
| Primal Hunt | Multiplayer LAN, select the LISP server, or use the game's direct-IP dialog; enter the join password when prompted | In game chat: `<serv> control "YOUR_ADMIN_PASSWORD"`, then `<serv> nextlevel`, `<serv> restart`, or `<serv> kick PLAYER_NAME` |

Primal Hunt uses its native server-controller password (`SCPassword`), rather
than Quake RCON. If the admin-password field is empty, the private configuration
receives an undisclosed random controller token and the portal shows
administration disabled. The portal never returns passwords or this token.

All four games use one of the existing UDP ports 27015–27018. No firewall rules
were added. Direct connection is the supported fallback when a game's LAN
browser scans its original default port rather than these custom ports.
Wolfenstein also opens its built-in backend UDP socket; no extra backend port
was exposed through the firewall.

## Installation and originals

The supplied ZIPs/DVD images and patch installers remain untouched under
`/srv/lan-party/files/Games/`. Extraction and patching took place under
`/srv/lan-party/servers/install-media/classic-games`, with runnable private copies
in `templates/eliteforce`, `templates/jka`, `templates/wolf2009` and
`templates/avp2ph`. Bundled cracks and No-CD replacement archives were not used.
Primal Hunt's base-game resource packs stay in a separate `base-resources`
directory; its 32-bit per-instance registry points to that directory.

`scripts/stage-classic-games.py` reproduces staging on a fresh host from the
same supplied media layout. Run it as `lanserver`, with 7z, innoextract,
msiextract, Xvfb and a working Wine runtime installed. Set
`LISP_CLASSIC_WINE_RUNTIME` when the runtime differs from the current CachyOS
Proton path. The script refuses enabled templates and occupied approved game
ports. It creates no installation markers and does not restart the portal.
The Windows dependency prefix is either copied from the private Battlefront
prefix or initialized separately; a fresh runtime still needs live validation.

Native engines and the InstallShield extractor are downloaded from their
upstream releases and checked against pinned SHA-256 hashes:

| Asset | SHA-256 |
| --- | --- |
| OpenJK Linux x86_64 | `8116857544cc8ca90713edae43db0b13108cb044af7ea7312c739a677464c297` |
| ioEF cMod 1.30 Linux x86_64 | `19426ca04167f13e6927117dade0435625dda3dc8143214894cc80679ef47245` |
| ISx 0.3.11 extractor | `145c254a8e656a2f1df9a384759700a2e686ca5e760fea1103224e3a2b818417` |

OpenJK's `latest` release is mutable. The installer rejects a changed digest;
review and validate a new upstream build before updating its pin. Engine
binaries, DVD images, REZ/PK3/PK4 data and Wine prefixes are not in this source
repository or its shareable ZIP. Native engine licensing belongs to the
upstream projects; their use does not grant redistribution rights to game data.

## Validation and limits

Real paired engine tests passed for all four: selected maps/modes, eight-player
limits, advertised join protection, external Windows LAN queries, and stopping
one match while the other remains running. Elite Force, Jedi Academy and
Wolfenstein also rejected incorrect RCON passwords and accepted correct ones
from Windows on the LAN. Their configured join passwords were verified through
authenticated engine queries. Primal Hunt's native join/controller credentials
were checked privately in its configuration; all six advertised modes and their
selected maps passed external queries.

Authenticated portal tests passed two concurrent matches for every game,
creator ownership, readiness, join/admin guidance and independent stopping.
An additional Primal Hunt match with empty password fields confirmed open
joining and the private random admin token. All owned matches were stopped.
Four malformed-response/archive tests and launcher JavaScript syntax checks
passed. Validation reports are in `outputs/Classic-*-validation.json`.

Actual players joining and playing have not been tested. Primal Hunt's in-game
controller password acceptance/rejection has not been exercised by a joined
player; the documented native command and private configuration are in place.
This source does not claim that a server query proves successful player joining.

Run the tests as `lanserver` with `PYTHONPATH=/opt/lan-portal`, only when at least
two approved slots are free: `tests/test_classic_live.py GAME` and
`tests/test_primal_live.py`. The optional `--external-lan` mode is for a paired
LAN harness and waits for private acknowledgment files; do not use it alone.

Upstream references: [OpenJK](https://github.com/JACoders/OpenJK),
[Elite Force cMod server instructions](https://github.com/Chomenor/ioef-cmod/blob/master/docs/server.md),
[Primal Hunt Master Server Patch](https://www.avpunknown.com/avp2master/),
[ISx](https://github.com/lifenjoiner/ISx), and
[LithTech REZ layout reference](https://github.com/no-lith/RezExtract).
Wolfenstein launch settings and Primal Hunt controller commands were also
verified against the supplied original launchers and packaged readme files.
