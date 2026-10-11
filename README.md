# LISP — LAN Party server

<p align="center">
  <img width="420" src="docs/LAN Party.png">
</p>

A local portal for game downloads, on-demand dedicated servers, player accounts, text/voice chat and a forum.

Project Zomboid and 7 Days to Die are available with owned persistent worlds.
My Servers now has **Stop** and **Restart**: worlds and settings remain, including
after a reboot. Stopped servers have a **Server port** selector and **Save port**
button, including automatic free-port selection when the old port is busy. The portal allows **six active servers** and **36 port choices
(27015–27050)**, with 32 additional LAN-only ports. See [survival setup](docs/SURVIVAL.md)
and [My Servers](docs/MY-SERVERS.md).

Contagion and Brink are available with two simultaneous instances, map/mode
selection, join/admin passwords and ownership-controlled stopping. The game
list is sorted by name. See [Steam additions](docs/STEAM-EXTRAS.md).

Local Mumble voice runs at **192.168.8.138:64738**, with General, Shooter and
Strategy channels. Click the highlighted **CHAT // MUMBLE** sidebar tabs to
switch views; **Join voice** opens the desktop app. The live channel box grows
with its occupants. Text chat messages expire after **two hours** in all rooms.
Mumble startup waits for its LAN address and retries if the network is delayed.
See [Mumble setup](docs/MUMBLE.md) and [chat](docs/CHAT.md).


Elite Force, Jedi Academy, Wolfenstein (2009) and Aliens vs Predator 2: Primal Hunt
are now available in the launcher. Each passed two-instance engine and
authenticated portal checks, with maps, modes, passwords and independent
stopping. Player joining remains untested. See
[setup and commands](docs/CLASSIC-GAMES.md).

Modern Warfare 2 (IW4x), World at War, Black Ops and Black Ops II multiplayer
(Plutonium) are available. Player connection tests for Black Ops and MW3 are
skipped at the user’s request; server startup and administration still need to work.
Two concurrent servers,
selected maps/modes/player limits, advertised join protection, LAN RCON authentication and
independent stopping passed live tests. Portal launch/ownership/stop passed;
an actual player joining has not yet been tested. The MW2 browser launcher also
passed two concurrent protected matches, Join instructions and independent
stopping. World at War also passed two-instance and authenticated portal tests
after a verified dedicated-asset repair. MW3 needs licensed legacy Steam files. See
[Call of Duty setup and results](docs/CALL-OF-DUTY.md).

This directory is the source project. `LISP.MD`, `GAMES.MD`, and `quake live.MD` are the original planning notes. Current implementation: download index, engine adapters for Quake Live, SoF2 Gold, Half-Life, Counter-Strike 1.6, Cross Product, Left 4 Dead 2, Jabroni Brawl, Team Fortress 2, Half-Life 2: Deathmatch, Unreal Tournament, UT2004, ET: Legacy and original Star Wars Battlefront II (2005), isolated instances, map discovery, player/mode/map/port selection, join/admin credentials, and a start/stop command. The portal now includes local browser/IRC chat, HTTPS administration, connected-device discovery, per-device/global Internet controls and bridge/separate interface setup with automatic rollback. All pages share left navigation, a central workspace and right chat panel with local pixel fonts and project icons.

Home has been removed. Logged-in players open Forum; guests use `/login/`.
Log out and Change password are at the bottom of the forum. IRC connection codes
are available in the chat sidebar.

The personal top bar shows each player's name, role, IP, MAC, forum avatar and own running servers,
unread forum topics/messages and next scheduled tournament match. Avatar changes
use the native forum uploader through the top-bar avatar and forum profile. See
[community features](docs/COMMUNITY.md).

## Layout
- `src/`: controller and download-page generator (Python standard library).
- `web/`: portal, download navigation, server UI.
- `scripts/`: Linux deployment and `lan-server` start/stop CLI.
- `config/`: nginx and systemd configuration.
- `tests/`: live engine, password and two-instance integration tests.
- `docs/`: operating instructions and Quake Live diagnosis.

## Deploy
Use a Linux host with systemd, nginx, Python 3, curl, tar and SteamCMD's 32-bit runtime libraries. On CachyOS/Arch these include `lib32-glibc` and `lib32-gcc-libs`. Copy this source directory to the host, then run:

```sh
sudo env BOOTSTRAP_IP=YOUR_ADMIN_PC_LAN_IP bash scripts/install.sh
sudo bash scripts/install-quakelive.sh
sudo bash scripts/import-steam-servers.sh /path/to/Steam/steamapps/common
```

The default address is 192.168.8.138 and LAN subnet is 192.168.8.0/24. Override with `sudo env LAN_HOST=192.168.1.10 LAN_CIDR=192.168.1.0/24 bash scripts/install.sh` on a different network. The installer requires an existing upload account, defaults to `robert`; override with `UPLOAD_USER=youruser`. Files remain in `/srv/lan-party/files`. Existing matches stop when the controller is restarted during deployment.

The Quake Live installer downloads official game binaries separately. They are not included here. No account passwords, SSH keys, game downloads, runtime instances, or local machine session history are included in this project. Share this source folder; recipients install their own game-server files. No source license has been chosen yet.

## Use
- `/`: main portal.
- `/downloads/`: games and patches.
- Upload files to `/srv/lan-party/files`; the download tree refreshes about once a minute. Reload an already-open download page to see new links. The refresh timer starts automatically after reboot.
- `/servers/`: launch and join matches; six concurrent slots, including multiple instances of the same game.
- `/my-servers/`: stop, restart, change a stopped server's port, or delete/restore its entry.
- `lan-server start --map campgrounds --mode ffa --players 8`
- `lan-server list`
- `lan-server stop INSTANCE_ID`
- `lan-server maps`

Players connect through the game console using the IP and port displayed by the portal. See `docs/QUAKE-LIVE.md` for the connection fix and limitations.

## Verify
`python3 tests/test_portal.py` runs against the configured LAN host. It creates two temporary instances, checks challenge responses on both game ports, tests validation and cross-origin rejection, stops one while checking the other, and cleans up its test instances. Run when at least two server slots are free. Set `LISP_TEST_URL` to test another host.

## Passwords and engine differences
L4D2 join passwords are disabled because its native password setting breaks connections; RCON administration remains available. See `docs/GAME-SERVERS.md` for password usage, firewall ports, supported modes and Quake Live admin Steam IDs. The engine adapters deliberately use different connection/authentication settings. The installed servers run without root privileges. Passwords are written only into mode-600 files in mode-700 instance directories; they are not returned by the API or put in command arguments. Stopping an instance removes its private copy and credentials. Failed instances remain private until dismissed.

## Importing installed servers
The import script takes the path to a Steam `steamapps/common` folder. It copies recognized dedicated-server installations into `/srv/lan-party/servers/templates`; it does not copy Steam login credentials. Each match gets independent files through filesystem reflinks where supported, with regular copies as fallback. Stop all instances before refreshing templates after a Steam update. The source archive contains no game binaries.

The main portal installer does not change firewall rules. The separate Mumble installer adds LAN-only TCP/UDP 64738. On the current PC, UDP/TCP 27015–27050 (games and native RCON), and TCP 28015–28050 (Quake Live / 7 Days admin consoles) are allowed only from 192.168.8.0/24. Set equivalent LAN-scoped rules on another deployment. The portal uses HTTPS; HTTP redirects to it. Accounts are required for every page beyond the login screen and for direct downloads, chat, forum and server actions. Use the trusted local CA certificate. The installer does not open listener firewall ports; allow TCP 443 and TCP 6667 only from your trusted LAN if using secure administration and external IRC clients. Browser chat uses the existing website port. Its right-sidebar selector offers General, Shooter and Strategy, with matching authenticated IRC channels; see [chat](docs/CHAT.md).

Current test results and remaining engine limitations are recorded in `docs/VALIDATION.md`.

## Network management and local chat

Additional requirements: NetworkManager (`nmcli`, `busctl`), nftables, UFW, OpenSSL and dnsmasq. Upgrade an existing installation without restarting game matches with `sudo bash scripts/install-network-chat.sh`. The full installer also installs these components. The network helper does not change the current topology on installation.

Log in at `/login/` as **admin** with the existing network-administration password; then use `/accounts/` and `/admin/`. Trust the public certificate at `/style/lisp-lan-ca.crt` after checking its fingerprint locally. Fresh installations bind the administrator using `BOOTSTRAP_IP` and prompt for an initial password when there is no earlier administrator to migrate. Passwords and private TLS keys must never be copied into this source folder or shared archive.

Use a spare wired port for the managed LAN, or select two spare wired ports to bridge them. The management and upstream interfaces are protected. Review the plan, apply it, and confirm within the displayed rollback deadline. Clients must use the mini PC's managed gateway to be controlled. Devices using the existing router directly are listed for information only. See `docs/NETWORK.md` and `docs/CHAT.md`.

The supplied Silkscreen font is covered by `style/Silkscreen-OFL.txt`. The images come from the project's supplied style folder. All assets are served locally.

## Soldier of Fortune II and Join buttons

SoF2 Gold (1.03) is now installed using the checksum-verified SoF2.org executable and Gold data updates, with isolated instances, maps and passwords. See docs/SOF2.md for runtime compatibility, installation and rollback. Running matches have Join controls: Steam launch links for supported Steam games, and console-command assistance for SoF2 and Cross Product.

## Additional game servers

TF2, Half-Life 2: Deathmatch, Unreal Tournament 469f and UT2004 3374 are installed and available. Each passed two simultaneous instance tests and independent stopping. Unreal includes mode-filtered maps and stock mutators; two Unreal matches fit the existing port pairs. TF2 uses its 64-bit runtime and requires `libcurl-gnutls.so.4`. See [docs/MORE-GAMES.md](docs/MORE-GAMES.md) for installation, test results and remaining client checks.

Battlefront II (2005) uses the original dedicated package through a private Proton Wine environment. See [docs/SWBF2.md](docs/SWBF2.md) for installation, LAN discovery, passwords, map filtering and client compatibility limits. UDP 3656 is allowed only from the local 192.168.8.0/24 network after approval.

## ET: Legacy

Wolfenstein: Enemy Territory is available through the official native ET: Legacy 2.86.0 server. The launcher includes four modes, six original maps, join passwords, RCON/referee administration and independent simultaneous matches. The downloads page includes a complete Windows x64 LAN client ZIP. See [docs/ET-LEGACY.md](docs/ET-LEGACY.md) for installation, connection and tests. No Snap installation or additional firewall ports are required.

## Bound player accounts and local forum

See [docs/ACCOUNTS-FORUM.md](docs/ACCOUNTS-FORUM.md). Players register with a name/password; the server observes and binds the actual LAN IP/MAC. Admins log in with name/password without an IP/MAC restriction, and manage accounts, temporary passwords, roles and changed player interface bindings. Sessions and unused IRC codes are revoked on changes. Only a game server's creator or an administrator can stop it; ownership is enforced by the backend. The forum contains General, Games, Servers, Tools and Emulators, with topics, replies and admin moderation. Chat uses the logged-in account name.

`lisp-accounts.service` keeps credentials, sessions and forum state private. Only the login screen and appearance/login assets remain public. Existing unauthenticated API scripts need an authenticated account session and CSRF token; this includes old test helpers. The root-only `lisp-account-recovery` tool can restore a changed player interface or reset a forgotten password without exposing secrets in command arguments. The source archive excludes all private databases, credentials and game files.

The `lan-server` CLI now signs in with a local account and respects server ownership. From a bound player PC use `--url https://192.168.8.138 --ca <LAN-CA-file>`; when run over SSH it uses the connecting player PC's address. Passwords are entered at the prompt. Portal logos use the supplied 1024-pixel artwork and smooth resizing; the retro fonts and borders remain.

Black Ops is enabled after a fresh two-instance server/LAN/RCON test and
authenticated portal launch/ownership/readiness/stop. It uses two port pairs,
supports selected maps/modes/player limits and join/admin passwords, and has
the same Join/Stop controls as the other CoD games. Player connection tests were
explicitly waived; a playable client session has not been verified.
MW3 still needs the licensed legacy Steam depots: its current 64-bit assets
fail in Plutonium, and the installed official Steam server reports that local
dedicated-server functionality is temporarily disabled. See
[MW3 file steps](docs/MW3-STEAM-FILES.md). A reversible keep-awake service prevents
automatic sleep; see [power management](docs/POWER-MANAGEMENT.md).

## Integrated tournaments and Simple Machines Forum

`/tournaments/` offers game voting, automatic Bracket creation, account-based signups and organizer controls. Votes and confirmed results update a Tournaments forum thread automatically. Administrators confirm the final podium; trophies then appear in the **Trophy Room** (`/trophies/`) and native forum profiles. The Trophy Room lists every enabled player with their forum avatar and gold/silver/bronze totals; clicking a player shows each medal's game and tournament. The top-bar avatar opens the native forum profile. Simple Machines Forum 2.1.7 uses the same bound LAN login and dark white/cyan portal palette. See [community setup and operation](docs/COMMUNITY.md) for installation, source licenses, backups, validation and competition limits.

Admins can delete unfinished tournaments when attendance is insufficient, including zero- and one-player events. They disappear from the active list, their forum thread is marked cancelled, and no trophies are awarded. Show deleted tournaments offers restoration with the original roster and bracket.

## Your game servers

Use **My Servers** from the left menu or top-bar activity to manage servers you
started. Stop and Restart controls are there; stopped entries and saved worlds remain.
Delete entry hides a stopped entry without deleting its world; Restore recovers
its settings. **Game Servers**
keeps the launcher, active list and Join controls. Administrators can manage
other players’ servers in a separate section. See [My Servers](docs/MY-SERVERS.md).

## Game server load and Credit Tokens — 2026-10-09

Server cards show per-engine CPU/current and average LAN traffic. Player server
usage charges local Credit Tokens; admin-owned servers are free. Accounts has
manual audited top-ups and, at the bottom, CPU/network token-worth settings and
the maximum negative balance. Reaching that shared floor saves/stops the owner's
servers without deleting worlds or entries. Thirty Linux tests, UI fixtures,
real separate CPU/LAN counters, player charging/admin exemption, browser top-up
and automatic credit-floor stop passed. Existing accounts and baseline entries
remain; no firewall permissions changed. No real payment service is connected.
See docs/CREDITS-AND-LOAD.md and outputs/Credit-load-live.json.
