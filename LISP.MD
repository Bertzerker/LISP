Local Internet Service Provider and Game Server for LAN Partys
Based on a Intel n110 Mini PC with 12GB RAM and 2x2.5Gbit Network Interfaces plus a 1Gbit USB Network Interface to the Internet

and 2x2.5Gbit Ethernet Switches



Web based locally hosted Downloads to minimize Internet access



Web based Game Server management
Create or Stop Servers.

&#x09;Create API to normalize the interface with each individual game.

&#x09;	All games are going to have a mixture of these server settings, game "executable", mod "folder name", mode "name", map "name", players x, time x, rounds x
Each game session will need a separate port, add a dropdown menu with a few defaults

&#x09;Create Plugin System for the API, so users can make a Adapter for each game.

&#x09;	Interfacing with the server differs between game engines, Adapters minimize keep the code clean



Local IRC chat



Web based internet access controls for admins

&#x09;Make this interface only available via a secure https connection.

&#x09;Secure the access with a default password which has to be changed on the first login.

&#x09;Make a list of all connected users and buttons to Block or grant access to the Web for all (toggle routing) or individual users (block routing)

&#x09;I want to be able to pair and switch the network interfaces to bridge or separate from the web interface.



## Implementation update — 2026-10-05

Implemented Network \& Internet Management (HTTPS admin, mandatory initial password change, device discovery, global/per-device Internet controls, bridge/separate plans and automatic rollback), shared browser/IRC local chat, and the retro pixel portal with left navigation, centre workspace and right chat. See README.md, docs/NETWORK.md and docs/CHAT.md for setup and current wiring limitations. Existing management/upstream connections were preserved. LAN-only TCP listener rules for HTTPS 443 and IRC 6667 were explicitly approved and enabled on 2026-10-05; both services passed connection checks from the Windows LAN client.


## Implementation update — 2026-10-06

Local accounts now bind name/password login to the server-observed LAN IP and MAC. Administrators manage accounts, interface replacements and temporary passwords. Home is public; downloads, chat, forum, servers and network controls require login. Server owners and admins alone can stop matches. The persistent forum has General, Games, Servers, Tools and Emulators. See docs/ACCOUNTS-FORUM.md for operation, recovery and the limits of MAC identification.

Modern Warfare 2 (IW4x), World at War, Black Ops and Black Ops II multiplayer are
enabled after two-instance and authenticated portal tests. MW3 is staged but
requires compatible legacy Steam assets before its server can start.
The World at War retail and uncut patches are applied only to private copies;
all Game Files and binaries remain excluded from the shareable source archive.

Black Ops is published with the existing map/mode/player/password and Join/Stop
controls. The user explicitly requested skipping player connection tests for
Black Ops and MW3; engine readiness, query, RCON and ownership checks remain.
Black Ops reserves paired ports 27015/16 and 27017/18, so two matches fit the
approved game slots. MW3 still needs licensed legacy Steam depots; its current
official server explicitly reports local dedicated hosting temporarily disabled.
A reversible keep-awake service blocks idle/sleep. See docs/POWER-MANAGEMENT.md,
docs/CALL-OF-DUTY.md and docs/MW3-STEAM-FILES.md.


## Chatrooms — 2026-10-06

General, Shooter and Strategy are available in the right chat sidebar and
authenticated IRC. Histories and room presence are separate; the original
history is retained in General and #lan remains a compatible IRC alias.
Room-isolation, migration, login requirements, real LAN API/IRC and browser
switching checks passed. Game matches and account roles were not changed.

## Community integration — 2026-10-08

Official Bracket and Simple Machines Forum 2.1.7 are deployed behind the existing bound LAN login. Game voting creates a tournament and maintains its forum thread. Portal signups map accounts to native players/teams; administrator-confirmed results publish automatically and grant profile trophies. General, Shooter and Strategy chat remain alongside the pages. The forum and post editor now use dark portal backgrounds, white text and cyan links. Separate-database integration tests passed a scored two-player elimination event, both trophy views and access/CSRF checks. See docs/COMMUNITY.md for operation and source/license details.

Admin tournament deletion/restoration is implemented and validated for zero/one players. Cancellation publishes to the Tournament thread, blocks votes/signups/bracket edits, and gives no trophies. Finished awards remain protected.

## Classic dedicated-server additions — 2026-10-08

Elite Force (native cMod 1.30), Jedi Academy (native OpenJK), Wolfenstein 2009
(patched Lite Server/Wine) and Primal Hunt (dedicated server/Wine plus supplied
Master Server Patch 1.1) are enabled. All passed two-instance engine and
authenticated portal launch/ownership/readiness/independent-stop checks.
Windows LAN queries passed; incorrect/correct RCON passwords passed for Elite
Force, Jedi Academy and Wolfenstein. Primal Hunt's native controller/join
credentials were checked privately, and all six modes passed actual LAN queries.
Its in-game controller authentication and actual player joining are untested.
No firewall change; originals and all 17 previously available games preserved.
See docs/CLASSIC-GAMES.md and outputs/Classic-games-status.md.

## Voice/chat and Steam additions — 2026-10-09

Local Mumble installed with General/Shooter/Strategy, LAN-only TCP/UDP 64738,
authenticated live channel viewer and native Join. CHAT // MUMBLE tabs switch
and highlight the current view. Seven actual test clients alongside admin
proved the box expands without clipping and shrinks on departure; existing
admin voice connection preserved. Text messages expire after two hours in all
rooms, including idle cleanup and already-open pages. Contagion and Brink
are published with two-instance/password/ownership tests and alphabetical list.
See docs/MUMBLE.md, docs/CHAT.md and docs/STEAM-EXTRAS.md.

## Trophy Room — 2026-10-09

Replaced 06 / My Profile with Trophy Room. All enabled players have forum avatars
and gold/silver/bronze totals; player details show each medal's game, tournament
and date. Top-bar identity opens the native forum profile. Existing profile links
redirect for compatibility. Final-only awards, no new production awards, existing
authentication retained. 15 Linux tests and live HTTPS/browser checks passed.
See docs/TROPHY-ROOM.md and outputs/Trophy-room-validation.json.
