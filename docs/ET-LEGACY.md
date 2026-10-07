# Wolfenstein: Enemy Territory — ET: Legacy

ET: Legacy 2.86.0 is installed and available at http://192.168.8.138/servers/. It uses the official native Linux x86_64 dedicated server and Legacy mod, with original ET packs from the official mirror. The linked etlegacy-snap project wraps this same upstream server; LISP installs it directly on CachyOS without Snap.

Select Objective, Stopwatch, Last Man Standing or Map Voting, choose a map and player limit, and optionally set join and admin passwords. The six original maps are battery, fueldump, goldrush, oasis, radar and railgun. The list also scans loose maps and PK3 archives in the template's etmain and legacy folders. Campaign sequences are not exposed by this map-based launcher.

## Players

Get **Wolfenstein Enemy Territory / ET Legacy 2.86.0 Windows x64 LAN.zip** from the downloads page. Extract the complete ZIP to a writable folder, run `Start ET Legacy.bat` and create your profile. This verified official Windows release includes the Legacy mod and original packs; no Internet download is needed for the packaged content. The client executable itself has not been launched as part of server verification.

Use the active match's Join button to copy its connect command. In ET: Legacy press `~` or `Shift+Esc` to open the console and paste `connect 192.168.8.138:PORT`. For protected matches, enter `password YOUR_JOIN_PASSWORD` first. Join provides console assistance because this client does not have a verified browser URL handler.

In-game administration: `rconpassword YOUR_ADMIN_PASSWORD`, then `rcon COMMAND`. The same optional admin password enables referee controls with `ref YOUR_ADMIN_PASSWORD`. Blank passwords disable the corresponding protection/access. No passwords are embedded in downloads, process arguments or API responses.

## Instances and network

Each match has an independent copy, home directory, configuration and game log. Join/RCON/referee credentials are stored only in mode-600 files inside its mode-700 instance folder, and removed when it stops. Dedicated LAN mode, disabled public advertisements/master servers and the existing UDP 27015–27018 allocation are used. ET needs one UDP port per match, so multiple ET matches fit the existing four slots. No firewall rules were changed. Connect directly using the displayed port; discovery on ET's default port is not required.

The bundled Legacy mod is selected explicitly. Bots and bundled Lua administration scripts are disabled; authenticated native RCON and referee access are available. The engine may transfer required PK3 content over its game connection. Standard maps and the bundled mod are already included in the prepared Windows client.

## Install elsewhere

Deploy the updated LISP source first, then run `sudo bash scripts/install-etlegacy.sh`. It requires Linux x86_64, curl, tar, Python 3, the existing lanserver account and enough storage. The pinned official release archive's published MD5 is checked; original PK3 archive integrity, required maps, game module and linked runtime dependencies are checked before enabling its marker. A failed staging directory is preserved for diagnosis; an existing template is never overwritten. Updates must be planned while its matches are stopped.

To rebuild the client ZIP, download the official 2.86.0 Win64 archive and run `python3 scripts/build-etlegacy-client.py ARCHIVE TEMPLATE OUTPUT.zip`. The builder checks the official archive MD5 and the installed pack SHA-256 manifest, keeps upstream licenses/credits, adds a local launch helper, and validates the resulting ZIP. Runtime binaries/data are excluded from the shareable source archive.

## Validation

Two simultaneous instances loaded oasis/Objective (8 players) and radar/Stopwatch (16 players) on distinct ports. Native UDP serverinfo confirmed maps, game types, capacities and password flags. Correct RCON worked, wrong credentials failed, and native join/referee password settings matched. Stopping the first preserved the second. Separate Last Man Standing and Map Voting tests reported their correct native game types and an unprotected match. API responses excluded the test secrets. All owned test matches were cleaned up.

Run `python3 tests/test_etlegacy_live.py` from a LAN machine with at least two free slots. `LISP_TEST_URL` overrides the target. Actual player joining and the in-game referee login still require a client test.

Sources: [requested Snap project](https://github.com/etlegacy/etlegacy-snap), [official 2.86.0 downloads](https://www.etlegacy.com/download), [upstream server configuration](https://github.com/etlegacy/etlegacy/blob/v2.86.0/misc/etmain/etl_server.cfg).

Browser verification also passed Start, Join copying and Stop. The download link appeared in the fold-out tree and passed HTTP size/resume checks (300575380 bytes). All owned preview/test matches were stopped; portal and SFTP services remained active.
