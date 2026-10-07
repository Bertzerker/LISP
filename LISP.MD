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
