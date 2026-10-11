# Game server guide

This guide collects the game-specific setup, runtime differences and operating
details moved out of the [project README](../README.md). For the portal's other
modules and their integration, start with that overview.

The portal lists the installed allowlisted adapters. Each offers maps read from the game folders and PAK/PK3/VPK archives. It never accepts an executable path from a browser request. Maximum six simultaneous matches on game ports 27015–27050 (36 choices); multiple instances of any one supported game are permitted.

## Game catalog and detailed guides

The catalog is sorted by name and depends on completed local installations.
Incomplete or unvalidated templates stay hidden; possessing the source adapter
alone does not make a game available. These are the documented installations and
remaining blockers, not a promise that every game is installed on a fresh host.

| Games | Runtime notes and current limits | Detailed guide |
| --- | --- | --- |
| Quake Live | Native dedicated runtime. Its Steam authentication settings and in-game admin Steam IDs differ from Source/GoldSrc. | [Quake Live](QUAKE-LIVE.md) |
| Half-Life, Counter-Strike 1.6, Half-Life: Cross Product, Left 4 Dead 2, Jabroni Brawl: Episode 3 | Native GoldSrc/Source templates. Mode discovery, Steam libraries, terminal handling and L4D2's password exception are described below. | [Modes and credentials](#modes-and-credentials), [runtime fixes](#runtime-fixes) |
| Soldier of Fortune II Gold 1.03 | Checksum-verified SoF2.org executable and Gold data updates; isolated instances, maps and passwords. | [SoF2 installation, compatibility and rollback](SOF2.md) |
| Team Fortress 2, Half-Life 2: Deathmatch, Unreal Tournament, UT2004 | Native Steam/OldUnreal installations; UT 469f and UT2004 3374 support mode-filtered maps and stock mutators. TF2 uses a 64-bit runtime and needs `libcurl-gnutls.so.4`. | [Additional servers](MORE-GAMES.md) |
| Wolfenstein: Enemy Territory | Native ET: Legacy 2.86.0, four modes, six original maps, join/RCON/referee options and a local Windows client download. No Snap runtime is required. | [ET: Legacy](ET-LEGACY.md) |
| Star Wars Battlefront II (2005) | Original dedicated package in private Proton Wine instances, with mission discovery, mode filtering and LAN discovery. | [Battlefront II](SWBF2.md) |
| Modern Warfare 2, World at War, Black Ops, Black Ops II | IW4x/Plutonium adapters with private per-instance configuration and Wine storage. MW3 remains blocked on compatible licensed legacy assets. | [Call of Duty](CALL-OF-DUTY.md), [MW3 asset steps](MW3-STEAM-FILES.md) |
| Star Trek: Elite Force, Star Wars Jedi Academy, Wolfenstein (2009), Aliens vs Predator 2: Primal Hunt | Native cMod/OpenJK for the first two; patched dedicated Windows runtimes through Wine for the latter two. | [Classic games](CLASSIC-GAMES.md) |
| Contagion, Brink | Imported Steam dedicated servers, with mode/map filtering, join/admin passwords and two-instance validation. | [Steam additions](STEAM-EXTRAS.md) |
| Project Zomboid, 7 Days to Die | Owned persistent worlds, compatible-build selection and save/stop/restart support. In-game accounts and admin controls differ by engine. | [Survival servers](SURVIVAL.md) |

## Install and import game files

First deploy the base portal as described in the README. Game runtime utilities
need curl, tar and the relevant SteamCMD/Wine/native dependencies. On CachyOS/Arch,
SteamCMD's 32-bit runtime includes `lib32-glibc` and `lib32-gcc-libs`.

```sh
sudo bash scripts/install-quakelive.sh
sudo bash scripts/import-steam-servers.sh /path/to/Steam/steamapps/common
```

The Quake Live installer downloads its official dedicated binaries separately.
The Steam import script copies recognized dedicated installations into
`/srv/lan-party/servers/templates` without copying Steam login credentials. It is
not a universal installer for every game in the table; use the linked guide for
each game's staging and dependencies. Recipients supply their own game files.

Each match receives independent runtime files using reflinks where supported,
with regular copies as fallback. Steam originals are retained. Stop all instances
of a game before refreshing its template after an update. Installers and tests
must not overwrite another player's active instance or world.

## Launch, join and manage

Use `/servers/` to choose a game, players, mode, compatible map and port, plus
supported passwords or admin IDs. Active matches have Join controls: native
launch links where supported, otherwise connection instructions. Use the IP and
port displayed for that specific instance; discovery is not guaranteed.

Stop, Restart, port changes, Delete entry and Restore are on `/my-servers/`, not
the shared Game Servers list. Only the creator or an administrator may manage
an entry. Stopped entries release their ports; another match may take one. Save
a new free port before restarting when needed. Multi-port games reserve query
or admin sockets too, so some base-port choices are unavailable. See
[My Servers](MY-SERVERS.md) for lifecycle and collision checks.

Six is the controller's concurrency limit, not a guarantee that six heavy worlds
will perform well on the mini PC. Cards show CPU and LAN traffic; player-owned
usage consumes local Credit Tokens and may trigger a save-and-stop at the debt
limit. See [load and credits](CREDITS-AND-LOAD.md).

### Command-line launcher

`lan-server` signs in with a portal account, uses the same ownership rules and
prompts for passwords. From a player PC, provide the HTTPS URL and trusted CA;
when run over SSH, it uses the connecting player's address.

```sh
lan-server start --map campgrounds --mode ffa --players 8
lan-server list
lan-server stop INSTANCE_ID
lan-server maps
```

These examples run on the Linux host. From a player PC, include connection
options before the action on every command, for example:

```sh
lan-server --url https://192.168.8.138 --ca /path/to/lisp-lan-ca.crt list
```

The start example uses Quake Live. Use `--ask-passwords` for hidden join/admin
credential prompts, `--admin-steam-ids` where supported and `--port` to request a
free game port. Keep credentials out of command arguments.

## Modes and credentials

| Game | Modes | Join password | Administration |
| --- | --- | --- | --- |
| Quake Live | FFA, Duel, TDM, CA, CTF, Freeze Tag, Domination, Race | g_password | In-game: SteamID64 admin list. External client: ZeroMQ RCON password, game port +1000. |
| Half-Life | Deathmatch, team deathmatch | sv_password | rcon_password from game console |
| Counter-Strike 1.6 | Standard map rules | sv_password | rcon_password from game console |
| Half-Life: Cross Product | Installed gamemode CFG files | sv_password | rcon_password from game console |
| Left 4 Dead 2 | Campaign, Realism, Versus, Survival, Scavenge | Unavailable in this engine build | rcon_password from game console |
| Jabroni Brawl: Episode 3 | Default map/rotation rules | sv_password | rcon_password from game console |

L4D2 enforces its native 4-player or 8-player mode size. Quake Live Duel uses two slots. Other adapters expose standard 2–32 slot choices. A map must support the selected mode; installed does not mean every map supports every mode.

## Join
For Quake Live and Source/GoldSrc clients, set `password YOUR_JOIN_PASSWORD` in
the client console, then use the displayed `connect IP:PORT` command. Quake Live
commands may be prefixed with `/`. Other engines use their own client menus or
console syntax; follow the portal's Join instructions and the linked game guide.

## Admin
For Source and GoldSrc games, set `rcon_password YOUR_ADMIN_PASSWORD` in the client console, then use `rcon status`, `rcon changelevel MAP`, and other engine commands. Blank admin passwords leave password-based administration disabled.

Quake Live does not implement the same in-game password-based RCON system. Enter one or more 17-digit SteamID64 values in the portal for in-game admin rights. Its optional admin password secures an external ZeroMQ RCON connection, not an in-game login command. The UI explains this distinction.

The command-line launcher supports `--ask-passwords`, which reads hidden prompts so credentials are not exposed in shell command arguments. Use `--admin-steam-ids` for Quake Live and 7 Days to Die and `--port` to request an explicit free port.

Engines run as the unprivileged service account, never root. Per-instance
passwords are written only into mode-600 files inside mode-700 private folders;
they are not returned by the API or put in command arguments. Clean stops remove
disposable runtime copies, while private restart presets retain settings and
credentials. Persistent worlds are stored separately. Failed runtime logs remain
private until handled, and deleting an entry preserves its world for restoration.
Private presets, databases, game binaries, ISOs and worlds do not belong in the
shared source or Git repository.

## LAN ports

On the current host, UDP/TCP **27015–27050** admit game/native-RCON traffic only
from **192.168.8.0/24**. TCP **28015–28050** serves the Quake Live and 7 Days admin
consoles. Battlefront II discovery additionally uses LAN-only UDP **3656**.
The base portal installer does not open these firewall ports; use equivalent
LAN-scoped rules on another deployment. Do not add router forwarding to make a
local match reachable. Portal HTTPS and voice/IRC ports are documented in their
own module guides.

## Connection policy
The shared principle is to keep Steam authentication operational while limiting inbound access to the LAN with the firewall. Quake Live uses sv_serverType 2, sv_lan 0 and sv_master 0. Source/GoldSrc use their own sv_lan and master-server controls; Quake-specific variables are not copied to them. No router forwarding is configured. LAN discovery is not guaranteed: use the displayed direct-connect command.

## Adding an adapter
`src/adapters.py` contains the registry and base adapters; dedicated adapter
modules hold engine-specific map discovery, isolated configuration, launch and
readiness behavior. Extend that allowlist and the relevant adapter module; never
turn browser inputs into arbitrary commands. Retest password enforcement, RCON,
slot allocation and two-instance isolation before exposing another game.

## Left 4 Dead 2 exception
Setting a nonempty native `sv_password` reproduced a connection/query failure on this installed build. Clearing it restored A2S queries immediately. The portal disables the join-password field and the API rejects attempts to set one, rather than claiming an open server is protected. Its RCON admin password works. See [Valve issue 3416](https://github.com/ValveSoftware/Source-1-Games/issues/3416). Join access remains restricted by the LAN firewall.

## Runtime fixes
GoldSrc uses the service account's Steam SDK library and distinct Steam ports per instance. Cross Product launchers are normalized to Linux line endings in each private copy. Source games bind to the configured LAN address and use their own engine settings. L4D2 instances receive app ID 550 and their bundled Steam library. Jabroni's Linux console requires a pseudo-terminal with valid dimensions; the controller supplies it and captures its output privately. Quake Live uses its authenticated server mode and disabled master listing. These are per-engine fixes, not a single set of Quake variables applied to every game.

## Star Wars Battlefront II (2005)

The original dedicated server now supports multiple private Proton Wine instances, installed mission discovery, mode filtering, join/admin passwords (maximum 15 characters), LAN join instructions and independent stops. See [SWBF2.md](SWBF2.md). UDP 3656 discovery is allowed only from 192.168.8.0/24 after approval. Real client compatibility remains to be tested.

## Persistent worlds and lifecycle

Project Zomboid and 7 Days to Die support owned, build-compatible saved worlds.
Stop saves and retains the entry. Restart reuses the same world, settings and owner,
including after a controller restart. Manage these actions on My Servers. See
[SURVIVAL.md](SURVIVAL.md) and [MY-SERVERS.md](MY-SERVERS.md).

## Validation and known limits

The game guides and [validation log](VALIDATION.md) record engine startup,
map/mode/player settings, password flags, actual LAN queries/RCON, isolated
instances and authenticated portal ownership checks. These checks do not prove
that a player has joined and completed gameplay. Many additions still need that
client check. Black Ops player-connection testing was explicitly waived; its
server pair and authenticated publication passed. MW3 is not represented as a
working server while its legacy-data blocker remains.

The MW2 browser launcher passed two concurrent protected matches with Join
instructions and independent stopping. World at War passed after a verified
dedicated-asset repair. The linked game guides preserve their precise runtime,
version and repair details. Other additions likewise record their own tests:
SoF2 Gold, the Steam/Unreal additions, ET: Legacy, Battlefront II, classic games,
Contagion/Brink and the persistent survival servers.

Run live engine tests only with free slots, authenticated sessions and trusted
LAN TLS, and stop only their owned test instances. `tests/test_portal.py` is a
legacy Quake Live two-instance/query/input-validation check that predates the
current login and stopped-entry lifecycle; its unauthenticated HTTP calls need
updating before use. Prefer the game-specific live tests and module unit tests
listed in the guides. No new engine or player gameplay tests were run for this
documentation reorganization.
