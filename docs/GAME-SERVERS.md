# Game servers

The portal lists the installed allowlisted adapters. Each offers maps read from the game folders and PAK/PK3/VPK archives. It never accepts an executable path from a browser request. Maximum four simultaneous matches on game ports 27015–27018; multiple instances of any one supported game are permitted.

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
Set `password YOUR_JOIN_PASSWORD` in the client console, then use the displayed `connect IP:PORT` command. Quake Live console commands may be prefixed with `/`.

## Admin
For Source and GoldSrc games, set `rcon_password YOUR_ADMIN_PASSWORD` in the client console, then use `rcon status`, `rcon changelevel MAP`, and other engine commands. Blank admin passwords leave password-based administration disabled.

Quake Live does not implement the same in-game password-based RCON system. Enter one or more 17-digit SteamID64 values in the portal for in-game admin rights. Its optional admin password secures an external ZeroMQ RCON connection, not an in-game login command. The UI explains this distinction.

The command-line launcher supports `--ask-passwords`, which reads hidden prompts so credentials are not exposed in shell command arguments. Use `--admin-steam-ids` for Quake Live and `--port` to request an explicit free port.

## Connection policy
The shared principle is to keep Steam authentication operational while limiting inbound access to the LAN with the firewall. Quake Live uses sv_serverType 2, sv_lan 0 and sv_master 0. Source/GoldSrc use their own sv_lan and master-server controls; Quake-specific variables are not copied to them. No router forwarding is configured. LAN discovery is not guaranteed: use the displayed direct-connect command.

## Adding an adapter
`src/adapters.py` contains the adapter registry and the engine-specific map discovery, isolated configuration, launch and readiness operations. Extend the allowlist and implement any engine-specific behavior there; never turn browser inputs into arbitrary commands. Retest password enforcement, RCON, slot allocation and two-instance isolation before exposing another game.

## Left 4 Dead 2 exception
Setting a nonempty native `sv_password` reproduced a connection/query failure on this installed build. Clearing it restored A2S queries immediately. The portal disables the join-password field and the API rejects attempts to set one, rather than claiming an open server is protected. Its RCON admin password works. See [Valve issue 3416](https://github.com/ValveSoftware/Source-1-Games/issues/3416). Join access remains restricted by the LAN firewall.

## Runtime fixes
GoldSrc uses the service account's Steam SDK library and distinct Steam ports per instance. Cross Product launchers are normalized to Linux line endings in each private copy. Source games bind to the configured LAN address and use their own engine settings. L4D2 instances receive app ID 550 and their bundled Steam library. Jabroni's Linux console requires a pseudo-terminal with valid dimensions; the controller supplies it and captures its output privately. Quake Live uses its authenticated server mode and disabled master listing. These are per-engine fixes, not a single set of Quake variables applied to every game.

## Star Wars Battlefront II (2005)

The original dedicated server now supports multiple private Proton Wine instances, installed mission discovery, mode filtering, join/admin passwords (maximum 15 characters), LAN join instructions and independent stops. See [SWBF2.md](SWBF2.md). UDP 3656 discovery is allowed only from 192.168.8.0/24 after approval. Real client compatibility remains to be tested.
