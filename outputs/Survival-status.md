# Survival games and persistent server controls — 2026-10-09

Enabled at https://192.168.8.138/servers/: Project Zomboid 42.21.0 (Steam build
25485538) and 7 Days to Die V3.3.0 b18 (build 25661908). All 23 previous games
remain, for 25 total in alphabetical order. Steam originals and the two legacy
Zomboid worlds are retained unchanged. Tests used only owned private worlds.

My Servers retains stopped entries and has owner/admin Stop, Restart and
Delete entry after stopping. Delete keeps the world; Restore recovers the same
entry/settings without starting it. Private presets survive a controller restart.
Game Servers has launch and Join without management buttons. No roles changed.

Capacity: six active servers; 36 choices, 27015–27050, including 32 added ports.
New UDP/TCP game and TCP 28019–28050 admin rules are LAN-only. Automatic
allocation skips occupied ports, including the existing Steam client on 27036.

Passed: two simultaneous native instances of each survival game; selected
Co-op/PvP maps/regions and 2/4 player limits; native local and Windows LAN
admin-password rejection/acceptance; 7 Days SteamID64 admin permission; Zomboid
native admin-account password hashes; independent stop and saved-world resume.
Live authenticated portal Stop/Restart preserved world ID, server ID, owner,
password protection and port. Six actual Quake Live engines ran together on new
ports and answered Windows LAN queries; a seventh was refused. Stopped records
survived service restart, then restarted. Nine Linux unit tests and browser
fixtures cover lifecycle ownership, durable secrets, stale-instance safeguards,
world compatibility, Delete/Restore and UI placement.

7 Days private visibility does not answer the Steam A2S browser query. Its native
console validates readiness and LAN administration; use Connect to IP. Actual
player joining/gameplay is untested. Six heavy survival worlds are not load-tested
and share this mini PC's 12 GB RAM and service memory budget. Native Telnet admin
is unencrypted on the LAN; in-game 7 Days admin uses SteamID64, not a password.

See docs/SURVIVAL.md and docs/MY-SERVERS.md. Sanitized engine/LAN/portal artifacts
are in outputs/Survival-*.json. Game data, ISO files, account passwords, databases,
private restart presets and saved worlds are excluded from the shared source.

Browser Delete/Restore/Restart passed on the same 7 Days world. Delete kept it
selectable; Restore returned the stopped entry; Restart reached running. Screenshots
show the controls. Owned test data is retained privately outside normal player lists.
Controller, website, accounts, community/forum, chat, Mumble, index timer and SFTP
remained active. Actual player gameplay was not tested.
