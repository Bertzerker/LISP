# Call of Duty servers

Modern Warfare 2 (IW4x), World at War, Black Ops and Black Ops II multiplayer
(Plutonium r5354) are enabled in the launcher. Each passed two isolated engines,
selected maps, Team Deathmatch/Free for All, eight-player limits, advertised
join protection, wrong/correct local and Windows LAN RCON passwords, LAN queries
and independent stopping. Authenticated portal launch, creator ownership,
readiness and stop also passed. Actual players joining and playing remain
unverified. The user explicitly requested skipping further player connection
tests for Black Ops and MW3 on 2026-10-06.

## Black Ops

A fresh server-only pair passed Array/Team Deathmatch on 27015 and Havana/Free
for All on 27017. It reserves game/QoS pairs 27015/16 and 27017/18, allowing two
concurrent matches within the existing firewall rules. The authenticated
publication check started a protected match, confirmed running status and
creator Stop permission, then stopped it. The browser dropdown displays 14
installed maps, eight modes, player limits, join/admin password fields and Start.
Task evidence: outputs/CoD-t5-live-validation.json,
outputs/CoD-t5-portal-validation.json and outputs/CoD-Black-Ops-launcher.png.

The newer [official r4811 changelog](https://plutonium.pw/docs/changelog/)
adds offline LAN/direct connect to T5; installed r5354 includes it. Players
launch the matching Plutonium game in LAN mode, set their join password if
needed, then use `connect 192.168.8.138:PORT`. Admin commands are
`rcon login YOUR_ADMIN_PASSWORD`, `rcon COMMAND` and `rcon logout`.
The server allows 180 seconds for connection loading and uses the official
190-second inactivity limit. Older experimental client tests reached map
loading but did not prove sustained play; those historical results are retained
in the task outputs. They no longer gate publication and are not being retried.

## Modern Warfare 3

The complete portal adapter is prepared with installed map discovery, modes,
player limits, isolated game/config/Wine storage, join/admin passwords and
start/stop support. It is not enabled because its engine cannot yet start with
the current Steam assets. Supplying private legacy audio/video DLL imports
resolved missing imports, but Plutonium then failed loading
`codescripts/$default` while reading `configure_mp.csv`. No client connection
test is needed: this is a server startup failure.

An isolated test of the matching current official x64 `iw5mp_server.exe` displayed
“The Local Dedicated Server function for MW3 is temporarily disabled.” It opened
no game/query port. The direct `iw5mp.exe -dedicated` attempt exited with code 53
without server readiness. Only the owned test Wine prefix was stopped; Steam
originals and player matches were preserved. Task evidence:
outputs/CoD-MW3-stock-startup.png and outputs/CoD-iw5-server-only-status.json.

Anonymous SteamCMD access to older depots was refused with a missing-license
error. It was not repeated. [Licensed Steam download steps](MW3-STEAM-FILES.md)
provide the three console commands and expected output folders. The latest
once-only file check found none of those directories. After licensed files are
available, copy only verified contents into the private template and require
the same paired engine/LAN/RCON/independent-stop and authenticated portal checks.
Do not run another player connection test or ask for Steam credentials.

## MW2 and World at War

IW4x uses its official launcher/runtime and a separate dependency prefix. Its
official [asset converter](https://github.com/iw4x/iw4x-client/blob/main/src/Components/Modules/ZoneConvert.cpp)
converted 106 private Steam fastfiles to the expected x86 layout. Paired tests
passed Afghan/TDM and Alpha/FFA; two real browser matches passed Join controls
and independent stopping. Evidence: outputs/CoD-MW2-two-servers.png.
IW4x admin commands use `rcon_password YOUR_ADMIN_PASSWORD`, then `rcon COMMAND`.

The World at War DVD ISO is preserved read-only under
`/srv/lan-party/servers/install-media/waw`. Supplied patches 1.1–1.7, German
1.4.1 and uncut conversion were applied only to private copies. Mixed-language
data initially failed on duplicate fonts. Checksum-verified LinuxGSM dedicated
1.7 assets repaired only the private `main` and `zone` data; archive MD5 is
`2c6be1bb66ea631b9b2e7ae6216c6680`. Original DVD, backup and patched/uncut folders
are retained under `install-media/waw-retail-patches`. Paired Airfield/TDM and
Asylum/FFA and authenticated portal/browser checks passed. T4 uses `tdm` and
`ui_maxclients`, without overriding `party_maxplayers`. Evidence:
outputs/CoD-World-at-War-server.png. Retail keys are excluded from source/logs.

## Isolation, accounts and LAN access

All engines run as `lanserver`, never root, with separate prefixes, game copies,
profiles and configs. Only approved UDP 27015–27018 slots are used. No firewall
rules or public forwarding were added. The user approved Plutonium query/RCON
allowlisting for `192.168.8.0/24`; wrong RCON passwords still fail. Wine binds
game traffic to all local interfaces within the existing LAN firewall, while
the controller queries loopback. Only a match's creator or an administrator
can stop it. Current account roles, forum, General/Shooter/Strategy chatrooms,
network settings and downloads were retained. No owned test matches remain.

All Game Files, binaries, ISOs, game archives, databases, keys and credentials
are excluded from the shareable source ZIP. Project Zomboid remains cancelled.
The half-hour continuation is paused; it must not resume player connection tests.

References: [Plutonium hosting](https://plutonium.pw/docs/server/t6/setting-up-a-server/),
[IW4x hosting](https://docs.iw4x.io/hosting/server-hosting/),
[LinuxGSM asset checksum](https://github.com/GameServerManagers/LinuxGSM/blob/master/lgsm/modules/install_server_files.sh).
