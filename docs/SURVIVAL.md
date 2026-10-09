# Persistent survival servers

Project Zomboid and 7 Days to Die use completed Steam dedicated installations
on the CachyOS LAN PC. Steam originals remain untouched. Private templates and
isolated per-instance copies use reflinks, with saved worlds stored separately.
Choose a new world or resume one belonging to your account. Admins may resume
other players' worlds without changing ownership. Only worlds matching the
installed build are selectable; legacy Zomboid worlds are retained, not upgraded.

| Game | Steam app / installed build | Maps / regions | Ports |
|---|---|---|---|
| Project Zomboid | 380870 / 25485538, version 42.21.0 | 11 installed Kentucky spawn regions | UDP base and base+1; TCP base RCON |
| 7 Days to Die | 294420 / 25661908, V3.3.0 b18 | Navezgane and four pregenerated worlds | UDP base and base+2; TCP base; TCP base+1000 console |

Both offer Co-op and PvP with 2/4/6/8 players. Zomboid region selection controls
spawn locations in the shared Kentucky world. 7 Days uses installed maps;
empty/playtesting folders are excluded. Public visibility and supported UPnP/
crossplay settings are disabled. The added firewall rules admit only the LAN.
7 Days with private visibility does not answer the Steam A2S browser query;
portal readiness comes from the actual native console. Use Connect to IP.

Stop saves and closes the native engine. Restart keeps the same world ID and
settings. A world cannot run twice simultaneously. Zomboid uses save/quit;
7 Days uses shutdown. Active saves are not force-killed by these controls. Delete entry is available
only after stopping; it keeps the world and has a Restore option.

Join passwords protect game entry. Zomboid's admin password bootstraps the native
`admin` account and authenticates RCON. Players choose their own character-account
credentials separately. 7 Days uses SteamID64 permissions for in-game F1 admin:
enter your SteamID64 at launch. Its admin password protects the Telnet console,
not an in-game password login. This distinction appears in the portal. Telnet
is LAN-only and unencrypted; use it on the trusted local network.

The portal offers 36 game ports (27015–27050), six active servers and collision
checks. Matching client builds are required. Actual player joining/gameplay is
not tested. Six heavy survival worlds are not load-tested; they share the mini
PC's 12 GB RAM and the game service memory budget.

Run `sudo python3 scripts/stage-survival-steam.py --steamapps /path/to/steamapps`
with the verified ECJ 3.40.0 compiler already at `servers/ecj-3.40.0.jar`.
The staging script verifies completed Steam manifests and compiles the Zomboid
bootstrap against installed Java classes. Installed markers are published only
after live validation. Apply the authorized additional LAN rules with
`sudo sh scripts/allow-additional-game-ports.sh`. The main installer still leaves
firewall configuration to the operator.
