# Verification — 2026-10-04

CoD results, 2026-10-06: MW2/IW4x passed two instances on Afghan/TDM and
Alpha/FFA with eight-player limits, advertised join protection, actual Windows
LAN queries, wrong/correct LAN and local RCON, and independent stopping.
Its authenticated portal launch and cleanup passed. The real browser also
started protected Afghan/FFA and Alpha/TDM matches, displayed Join/Stop,
copied Join instructions and stopped them independently. Screenshot:
task workspace `outputs/CoD-MW2-two-servers.png`.

The supplied WaW patches/uncut payload applied successfully, but the resulting
mixed-language assets failed the first live startup on duplicate fonts.
The original and patched directories were retained; the checksum-verified
LinuxGSM 1.7 dedicated `main`/`zone` data repaired only the private template.
Two T4 instances then passed Airfield/TDM and Asylum/FFA, eight-player limits,
join protection, actual LAN queries, wrong/correct local and LAN RCON and
independent stopping. Authenticated portal publication, creator ownership,
readiness and stop passed before enabling World at War.
Its real browser check passed map/mode/player menus, a protected Airfield/TDM
match, Join's Plutonium LAN-mode instructions and copied command, and creator
stopping. The owned match was cleaned up. Task screenshot:
`outputs/CoD-World-at-War-server.png`.
Actual player joining remains untested for both games.

An account lookup regression discarded the wired neighbor when the same player
was observed on Wi-Fi first. Keeping distinct server-interface observations
fixed route selection without changing IP/MAC/password checks or account roles.
Eight account tests passed, including a dual-interface regression and continued
rejection of routed clients; production registration and the existing player's
browser session succeeded afterwards.

Earlier IW4x tests timed out during automatic asset conversion. The separate
conversion job completed 106 files, and the later pair/portal/browser tests
above passed. MW3's anonymous legacy-depot attempt was refused for lack of a
license; no legacy overlay was applied. A single 2026-10-06 continuation check
found none of the three licensed legacy depot folders. Completed jobs are not
being restarted or polled.

Black Ops' older Session-ID FAQ conflicts with the newer official r4811
changelog, which adds offline LAN/direct connections. The user has waived further player
connection tests for Black Ops and MW3. Server-only checks remain required;
passing server queries is not proof of a playable client session.

## Call of Duty — 2026-10-06

Black Ops II (Plutonium r5354) passed two simultaneous instances on ports
27015/27016, Carrier/Team Deathmatch and Cargo/Free for All, eight-player limits,
advertised join protection, correct-versus-wrong RCON passwords over loopback
and the Windows LAN, remote LAN getinfo queries and independent stopping.
An authenticated portal launch, owner-only stop capability, running status and
stop also passed. Existing catalog games stayed available. No owned test
servers were left running. Actual player joining/playing was not tested.

The user explicitly approved LAN 192.168.8.0/24 entries in the Plutonium
query/RCON allowlist. Wrong admin passwords still failed over the LAN. No
firewall rules were broadened. Black Ops is enabled after fresh server-only and portal checks; MW3 remains
hidden because its engine lacks compatible assets.

- Reproduced the old configuration's `Server is for LAN clients only.` response from the Windows LAN PC.
- Applied `sv_serverType 2`, `sv_lan 0`, and kept `sv_master 0`.
- Detected 149 installed maps from the game content.
- Started independent FFA (8 slots) and Duel (2 slots) instances on UDP 27015 and 27016.
- Both ports responded at the Steam-authentication stage over the LAN.
- Stopping the first instance left the second running; test instances were cleaned up.
- Invalid map/player settings, missing request headers, and foreign origins were rejected.
- Full Steam client authentication and player entry into the match require an in-game test.

- User confirmed a successful in-game connection to the fixed server.

## Expanded portal — 2026-10-05

- Detected six games: Quake Live (149 maps), Half-Life (125), Counter-Strike 1.6 (25), Cross Product (31), Left 4 Dead 2 (79), and Jabroni Brawl (149).
- All five newly imported game adapters passed startup, native readiness, authenticated RCON, public API secret-exclusion, and instance cleanup checks.
- Two instances of EACH game ran concurrently with distinct ports. Stopping one preserved the other. Source/GoldSrc tests checked different credentials and private configuration permissions.
- Two Quake Live instances accepted RCON commands from the Windows LAN PC; wrong RCON passwords received no response. Their join-password flags and stop isolation passed. Actual player joining was previously confirmed by the user.
- L4D2 with a join password did not answer queries. Clearing it immediately restored responses; the UI disables that capability and the API rejects nonempty join passwords. Both L4D2 instances passed with join passwords empty and distinct admin passwords.
- Browser verification confirmed all six game options, populated maps, active-server cards, stop controls, and the disabled L4D2 join field with its explanation.
- These checks validate game protocols and administration, not a human playthrough of every game, mode, or map. Player entry was explicitly confirmed only for Quake Live.

Reproduce on the server with `python3 tests/test_installed_engines.py` and `python3 tests/test_pairs.py` as the service owner or root, with at least two free slots. `tests/test_quake_passwords.py` runs from a LAN PC and additionally needs `pyzmq`; it uses throwaway credentials and removes its instances. None of these tests should run during a match you cannot interrupt indirectly through resource use.

For a different deployment, set `LISP_TEST_URL` to its portal/controller URL and `LISP_BIND_IP` to its LAN address when running the engine tests.


## Network, chat and portal — 2026-10-05

- Six tests passed on Linux: forced administrator password rotation/session revocation, persisted chat and nickname/rate/input validation, shared IRC/browser history, protected-interface/plan validation, rollback restoration and forwarding-only rule generation.
- Actual Linux nftables forwarding was tested in disposable virtual networks: both clients allowed, one MAC blocked while the other retained Internet, global blocking, and local gateway access preserved in each case. No host topology or listener firewall rules were changed by these tests.
- Physical bridge activation and DHCP with the player switch have not been tested: the PC currently has only one spare wired interface. The live gateway remains unconfigured.

- After explicit approval, TCP 443 and TCP 6667 were allowed only from 192.168.8.0/24. Windows LAN checks verified the HTTPS certificate against the exported local CA, administration page access, unauthenticated network API rejection and an IRC CAP protocol response without joining or posting to a channel.

- SoF2 v1.01: two simultaneous independent instances passed readiness, distinct map/mode/port checks, correct and incorrect RCON authentication, and stopping one while preserving the other. Test matches were cleaned up. Actual player-client joins and local Steam application launches were not tested.

- SoF2 Gold update: checksum matched SoF2.org; Gold data updates loaded. Fixed confirmed modern NSS stack-alignment crash with a SoF2-only shim. Two instances reported protocol 2004 and g_needpass=1; correct/wrong RCON and independent stopping passed. No test matches remain. The user subsequently confirmed a successful Gold client join.

## Battlefront II (2005)

- Original ModDB v1.1 dedicated installer matched MD5 7dff4d332505269810fd7313c44a944d and extracted without a GUI. Proton CachyOS Wine successfully loaded installed missions with the existing controller sandbox enabled.
- Two simultaneous matches passed native TCP RCON status with distinct game ports, maps, player limits and passwords. Correct admin credentials succeeded and wrong credentials failed. Stopping one preserved the second. Invalid mode/map combinations were rejected.
- Testing identified the native 15-character admin-password truncation; the UI and API now reject longer Battlefront passwords, and private status credentials fit that limit.
- Both matches bound shared UDP 3656. After explicit approval, that discovery port was allowed only from 192.168.8.0/24. Actual LAN-browser discovery and a player join still require a game-client test. The package RCON version string is 1.00 despite the installer v1.1 label.
- SoF2 Gold: the user confirmed a successful player connection after the preceding automated server tests.

## Additional games — 2026-10-05

- Steam's exact app-install success messages confirmed 232250 (TF2) and 232370 (HL2DM). Both OldUnreal installers reported “is now installed!”. Native executables and map content passed inspection before installation markers were enabled.
- TF2: 238 maps; two native 64-bit instances on 27015/27016 loaded koth_abbey and arena_afterlife. Correct admin RCON succeeded, wrong credentials failed, and the native join-password setting matched each request. Fixed the private 64-bit replay/Steam runtime links and installed official CachyOS libcurl-gnutls.
- HL2DM: 8 maps and two modes; two instances loaded dm_lockdown and dm_overwatch. Native mp_teamplay settings, correct/wrong RCON and join-password settings passed.
- UT99 469f: 96 maps, five modes and three installed stock mutators. Native query/password checks passed for DM-Agony and CTF-Command on game ports 27015/27017, with separate following query ports. Instagib was configured for the second instance.
- UT2004 3374: 131 maps, eight modes and three installed stock mutators. DM-1on1-Albatross and CTF-AbsoluteZero passed native queries on distinct port pairs. Native rules confirmed GamePassword=True and active Instagib. Explicit URL QueryPort fixed the default 7778 collision.
- Every game passed stopping the first instance while the second remained running. Tests and the browser preview were cleaned up; no player matches were stopped. No firewall changes were made.
- Actual installed Unreal mode and mutator package/class names passed checks. Unreal instance directories and private configuration had permissions 700/600.
- Browser checks confirmed all four game options, filtered maps, mutator selection, active-server Join/Stop controls and copied connect commands. Screenshot captured in outputs/LISP-additional-game-servers.png.
- Actual player joins for these four games, Unreal in-game adminlogin authentication and local game URL-handler launches remain untested. Source RCON authentication and native Unreal password flags were tested directly.

Reproduce with tests/test_more_games_live.py GAME and its adjacent more_games_protocols.py helper. Use free slots; Unreal needs two complete port pairs. Per-game live results are recorded in the task outputs folder.

## ET: Legacy — 2026-10-05

- Official Linux and Windows 2.86.0 archives matched their published MD5 checksums. Original game packs passed full ZIP integrity checks; the template manifest records pack SHA-256 values. Required six maps, native executable, Legacy module and linked runtime dependencies were checked.
- Two simultaneous ET matches passed native UDP queries: oasis/Objective/8 slots and radar/Stopwatch/16 slots, distinct ports, join-password flags, correct RCON authentication, wrong-password rejection, matching native join/referee settings and API secret exclusion. Stopping one preserved the other. Last Man Standing and Map Voting returned their correct native game types with public passwords disabled.
- The complete Windows x64 LAN ZIP was built from the verified upstream client plus installed ET packs; resulting archive integrity passed. Upstream licenses/credits were retained. The helper uses a local profile folder and contains no credentials.
- Live tests stop only their own matches. Existing games, portal functions and firewall rules were preserved. No actual ET player join or in-game referee login has been performed; the Windows client executable has not been launched.

Reproduce with tests/test_etlegacy_live.py from the LAN with two free slots.

- ET browser check: selected ET: Legacy, inspected all four modes and six maps, started an oasis match from the form, copied its address with Join and stopped the same preview from its card. Screenshot saved as outputs/LISP-ET-Legacy.png. Instance/config permissions were verified as 700/600. The live catalog contains 13 games; controller, website and SSH/SFTP services were active.
- ET download check: the Windows LAN ZIP appeared in the fold-out download tree. HTTP HEAD reported 300575380 bytes and a 100-byte resumable range returned 206. Browser preview and all owned test matches were stopped.

## Accounts, ownership and forum — 2026-10-06

- Six security tests passed: changed IP/MAC and stolen-session binding checks, CSRF, reset and mandatory password rotation, role/disable protections, logout/expiry, hashed credential/session storage, one-use IRC codes, forum persistence and admin moderation.
- Live HTTPS tests from the Windows LAN client verified registration with its server-observed IP/MAC; guest denial for pages, raw downloads and APIs; admin-only account/network access; missing-CSRF denial; all five forum sections, posts, replies and locking; account-based browser chat and IRC; password reset, interface rebind and disabled-session revocation; logout; authenticated HEAD/size and resumable range downloads.
- Two real concurrent SoF2 matches had independent owners and ports. A different player could not stop either owner's match; its creator and the test administrator could stop it. One match remained queryable after the other stopped. Spoofed owner data was ignored. Only owned tests were stopped and test accounts/posts/messages removed.
- Browser layout preview revealed and fixed removal of the forum navigation by the shared shell. The preview displayed all sections in the existing pixel layout. The in-app browser rejected the existing LAN CA, so production behavior was checked through HTTPS using that CA explicitly; the visual screenshot is a localhost layout preview.
- Account service and private state permissions were verified. Existing network settings, downloads, chat history, upload/SFTP account and installed game templates were retained. Robertkopp remains a player at the user's request; admin remains the host administrator.

## Higher-resolution icons and DVD backup — 2026-10-06

- Portal logos use the supplied 1024×1024 artwork at 128/144-pixel desktop display sizes with smooth resizing; header/browser icons use the 192×192 asset. Updated styles and shell URLs force a new browser fetch. All six pages and regenerated download index were checked on the server. Live HTTPS verified exact logo bytes, updated styles and continued guest API denial. The localhost Home preview was checked visually and saved.
- World at War DVD ISO completed at exactly 7,325,483,008 bytes. Complete saved-file checksum passed; the recovered final 64 KiB and six prefix positions matched the DVD. ISO9660/Joliet file extents fit within the image, and MSI, setup and autorun files matched the DVD. Earlier copied sectors were retained rather than all reread. See docs/DVD-BACKUP.md. DVD monitoring is paused.

## Chatrooms — 2026-10-06

13 Linux unit/integration tests passed for migration, isolated histories and
presence, per-room retention, shared rate limits, authenticated APIs and real
IRC sockets, plus the existing network/chat regressions. Production preserved
every prior message and ID in General. Real LAN HTTPS/IRC checks passed
General/Shooter/Strategy isolation, browser-to-IRC sharing, PART presence and
unauthenticated rejection. Owned test data was removed. Real browser room
switching and the retained General message passed; screenshot is task
outputs/Chatrooms.png. Only lisp-chat restarted; game controller, existing
account roles, network controls and downloads were preserved.

## Black Ops server-only publication — 2026-10-06

The user explicitly requested skipping player connection tests for Black Ops
and MW3. A fresh T5 pair passed Array/TDM/8 slots on 27015 and Havana/FFA/8 slots
on 27017, join protection, wrong/correct local and actual Windows LAN RCON,
LAN queries and independent stopping. The game marker was published only after
this result. Authenticated portal launch, creator ownership, running readiness
and stopping passed. The browser confirmed the Black Ops dropdown, 14 maps,
eight modes, player limits, password fields and Start. Evidence:
outputs/CoD-t5-live-validation.json, CoD-t5-portal-validation.json and
CoD-Black-Ops-launcher.png in the task workspace. No player client was launched
in this run, and sustained player joining remains unverified. The T5 loading
timeout, inactivity limit and Plutonium RCON instructions are now deployed.

The current official x64 MW3 dedicated launcher displayed its explicit local
hosting-disabled error and opened no game port. Direct dedicated engine startup
exited with code 53 without readiness. All diagnostic engines ran as lanserver
and only their own Wine prefix was stopped. Steam originals were unchanged.
Plutonium still needs licensed older assets; no additional anonymous download
was attempted and none of the three legacy depot folders was found in this
run's one check. MW3 remains hidden for a startup failure, not a client-test gate.
The continuation remains paused and its instructions now omit client tests.

## Community integration — 2026-10-08

- 21 account/community unit tests passed on Linux. PHP integration files passed syntax checks; the pinned native Bracket frontend built successfully.
- Separate loopback validation databases passed real Bracket event creation, two signup/account mappings, native SMF identity, automatic voting/result threads, a scored single-elimination match, administrator-confirmed gold/silver trophies in portal and native forum profiles, idempotent result publication, private-profile exclusion, player restrictions and CSRF rejection.
- Zero- and one-player tournament deletion passed, including restoration, cancellation publication, no trophies, active-list removal, blocked native edits and rejected player/forged requests. The administrator subsequently cancelled the real UT tournament through the new control; its forum thread and retained roster show cancellation.
- Native SMF and tournament browser checks passed with the existing admin login. The forum's stock white gradients, rows and breadcrumb backgrounds were replaced by portal colors, white text and cyan links; SCEditor's separate document uses the same palette.
- Validation services were stopped after tests. Existing controller, chat, accounts, SFTP, website and community services remain active. No game-controller restart, human role change or firewall change occurred.
- See docs/COMMUNITY.md and outputs/Community-live-validation.json for scope and workflow. Podium confirmation is an admin action; game scores are not collected automatically. Screenshots: outputs/Forum-dark-theme.png, outputs/Tournaments-admin-controls.png and outputs/Bracket-home.png.

## Automatic download refresh repair — 2026-10-08

- The installed generator had CRLF line endings. Its shebang therefore named a nonexistent interpreter, causing systemd `203/EXEC` failures even though the timer was enabled and running after reboot.
- The generator was redeployed with LF line endings. Both the systemd service and initial installer refresh now invoke `/usr/bin/python3` explicitly, so copied Windows line endings cannot prevent the scheduled refresh from starting.
- A temporary owned upload created after the manual refresh appeared during the timer's next normal run. The timer is active and enabled; the refresh service exited successfully. The temporary file was removed and the index refreshed again.
- All 84 generated download links exactly match the visible completed files in `/srv/lan-party/files`, including the newly uploaded emulator archive, Generals installer and Carmageddon files. Reload an already-open page after uploading; indexing runs about once a minute.
- No website/game-controller restart, account change or firewall change was needed. Browser verification in the in-app browser was unavailable because it did not trust the LAN HTTPS certificate; the timer and generated file/link checks passed on the host.

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

- 2026-10-08 branding: supplied transparent coat of arms replaces the portal logo and favicon; the Neon Retro Arcade image replaces the sidebar LISP wordmark. Home, native forum and generated downloads loaded both images in the live browser; deployed files matched source hashes, HTTPS assets and forum PHP syntax passed. Screenshot: `outputs/Portal-branding.png`.

- 2026-10-08 forum repair: CSS/JS minification disabled to match the read-only theme folders; attachment path normalized to the selected JSON directory; PostgreSQL empty-row session/last-visit assignments guarded. Actual installed PHP regression checks, idempotent reapplication and a fresh admin login plus five authenticated forum pages passed. Error count/last ID stayed at 180 with no new errors; topics, messages and member counts were unchanged. No roles, board permissions or service restrictions changed. Screenshot: `outputs/Forum-repaired.png`.

- HTTP check before the ET: Legacy addition: 47 downloads passed HEAD/size and resumable-range checks. The 40 original entries are present under their original names except `AOE.iso`, now `Age of Empires Collection.iso`; its SHA-256 still matches the original transfer manifest. The source drive was unavailable for a new complete local checksum comparison.
- Final service check: controller, nginx website, index timer and SFTP/SSH were active. No test matches remained running.
