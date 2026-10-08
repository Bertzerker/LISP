# Tournaments, forum and player trophies

Open https://192.168.8.138/tournaments/ with your existing LAN account. The same IP/MAC-bound login protects Bracket, Simple Machines Forum, voting and profiles; no second account or password is needed. Navigation and the three chatrooms remain beside these pages.

## Organize a tournament

1. An administrator opens **Open a tournament game vote**, gives it a name, selects at least two installed games, and chooses voting and tournament dates.
2. Each player can cast one vote and change it until the deadline. The Tournaments forum board gets a thread automatically; its first post shows current votes and links.
3. Voting closes automatically. A unique winner creates the Bracket tournament and opens signups. A tie or no votes waits for an administrator's choice among the tied games. Administrators can close voting early.
4. Players press **Join tournament**. Each account is mapped to a Bracket player and an initial individual team. The organizer uses **Manage bracket** to create stages, assign teams, schedule matches and enter scores. The portal's server-launch link preselects the winning game; it does not launch a match automatically.
5. When the tournament is actually finished, the administrator chooses the gold, silver and optional bronze teams and confirms the results. Those teams' players must have signed up through the portal. This is an explicit confirmation of final placings, not an inference from provisional rankings.
6. Confirmed results automatically appear in the tournament thread and grant trophies on `/profile/` and the forum's **Trophies** profile tab. Repeated confirmation/publication does not duplicate awards or replies. The gateway blocks further tournament edits after confirmation.

Bracket supports different competition formats through its own organizer screens. Signups initially create individual teams; when combining them into team events, keep the account-mapped players in the teams. Upstream limits include 64 teams per tournament and 64 tournaments per club. The portal caps signups at 64 accounts. There is no automatic tournament game-server orchestration, seeding, score collection from games or chat announcement bot.

## Cancel when too few players show up

Administrators can press **Delete tournament** on any unfinished tournament, even with zero or one signed-up player. Confirm the dialog to remove it from the active list. Its existing Tournament thread is marked cancelled and gets a cancellation notice; no trophies are created. Voting, signups and native Bracket edits are blocked while deleted. This does not stop a separately launched game server.

Use **Show deleted tournaments** to view the retained record. Administrators can **Restore tournament**, preserving votes, signup mappings and the existing bracket. If an old vote deadline has passed, normal deadline processing resumes. Confirmed tournaments with awarded trophies cannot be deleted by this control. The retained forum thread, native bracket data and audit history make deletion recoverable; it is not a database purge.

## Forum

Simple Machines Forum 2.1.7 replaces the old forum at `/forum/`, with General, Games, Servers, Tools, Emulators and Tournaments boards. Native topics, replies, moderation, private messages and member profiles use LAN identities. Account names, passwords and administrator roles stay owned by the LAN account service. The administrator security prompt verifies the current LAN password without storing it in SMF. Changing an account's interface or disabling it affects forum access too.

The forum, including its post editor, uses the portal's dark background, white text and cyan links. Formatting uses SMF's normal BBC editor and filtering. The retired plain-text forum is backed up privately; its write API is disabled. Migration found zero legacy topics and posts, so there was no historical post content to import. Existing user accounts and the real UT tournament were retained.

## Deployment and private state

The current Linux installation uses official pinned sources:

- [Bracket](https://github.com/evroon/bracket/tree/04d914157565683cda47e481c56c83b4b3051475), commit `04d914157565683cda47e481c56c83b4b3051475`, AGPL-3.0.
- [Simple Machines Forum](https://github.com/SimpleMachines/SMF/tree/d49255b955cbeeb3a702d77009c85aae517ed1e4), 2.1.7 commit `d49255b955cbeeb3a702d77009c85aae517ed1e4`, BSD license.

License copies are in `docs/licenses`. The local Bracket source and integration patch are available to logged-in LAN users at `/community-source/`; this is separate from game downloads.

Services: `lisp-community-postgres`, `lisp-bracket`, `lisp-forum`, `lisp-community`. PostgreSQL listens on loopback 5433, Bracket on 8793, the community gateway on 8791, and the signed forum bridge on 8792. PHP uses a private Unix socket. No additional LAN firewall port was opened.

Private state: `/var/lib/lisp-community/community.sqlite3`; PostgreSQL's `lisp_bracket` and `lisp_forum` databases in `/var/lib/lisp-postgres`; app credentials in `/etc/lisp/community/settings.json`; native attachments and custom avatars in `/opt/lisp-forum`. Back up these together with the existing account database. Do not share them. Browser requests never receive the native Bracket organizer JWT or app database passwords. Publication failures retry without exposing response bodies or credentials.

For another CachyOS/Arch host, first install the base LAN portal and the dependencies `postgresql php php-fpm php-pgsql php-gd composer git uv nodejs pnpm`. Run `sudo python3 scripts/install-community-runtime.py`, then `sudo python3 scripts/deploy-community.py`. Set `LAN_HOST` for another host. The second script builds the official frontend under its dedicated user, backs up/migrates the old forum, and publishes the community routes. It restarts account/community/forum services, never the game controller. The existing Nginx configuration must contain the two optional community include globs in `config/nginx.conf`; custom configurations must incorporate these before publication. Scripts do not change firewall rules or bootstrap a new administrator.

## Validation — 2026-10-08

Twenty-one account/community unit tests passed. The live integration test used separate loopback-only Bracket and SMF databases and test-local accounts, guarded against production endpoint access. It passed one-vote changes, closed votes, tie choice, automatic native Bracket creation, real SMF thread updates, two signup mappings, a real scored single-elimination match, admin-confirmed gold/silver trophies in both profile views, duplicate finalization/publication, player restrictions and CSRF rejection.

The staging forum failure was a test socket under the production service's private directory. Validation now uses its own `/run/lisp-community-validation` socket directory; production privacy was retained. An earlier staging path error had published a test result into the real UT thread. Its identified test-only reply/event were removed; the UT vote and roster were retained. The administrator later cancelled the tournament and had removed its native event. Restore now rebuilds missing native data when needed. Subsequent validation was isolated and guarded.

Canonical live test: `tests/test_community_live.py`. It refuses production URLs/databases and requires an operator-prepared private validation runtime. It is not a production account-creation test. Actual browser results and screenshots are recorded in `docs/VALIDATION.md` and `outputs/Community-status.md`.

Native Bracket Delete is routed through the same recoverable cancellation. Restoration rebuilds account mappings if an event had already been purged through the native UI before this fix. Both paths passed isolated live tests. The blank native stage screen for a missing event now provides an unavailable message and a return link. SMF uses its bundled local jQuery, so the editor works without external CDNs.

## Forum runtime repair — 2026-10-08

`sudo python3 scripts/repair-forum-runtime.py` repairs the pinned SMF runtime without changing member roles, board permissions, posts, uploads or service filesystem restrictions. Installation and deployment also invoke it. Private backups are stored under `/srv/lan-party/community-setup/backup/forum-repair-*`.

SMF asset minification is disabled because the theme CSS/scripts directories are intentionally read-only. The normal original assets remain available. The attachment directory setting is stored as a JSON object keyed by the selected directory ID, matching SMF 2.1's maintenance expectations. Two guarded assignments in `Sources/Session.php` and `Sources/Load.php` handle PostgreSQL's false return for missing session/last-visit rows without PHP warnings. The script refuses unexpected upstream source or unknown upload paths rather than overwriting them.

`php -c /etc/lisp/community/forum-php.ini tests/test_forum_runtime.php` checks the installed missing/existing/invalid session behavior and missing/existing last-visit results. Fresh administrator login and five authenticated forum pages passed; error count and last error ID stayed at 180. Existing historical errors and failed-login audit entries are retained.

## Personal activity bar — 2026-10-08

Logged-in players see their forum avatar and name in the top bar, with links to
their own starting/running game servers, unread visible forum topics, unread
private messages and their next scheduled tournament match. Counts and match
links refresh every 30 seconds while the page is visible. Only the verified
account's information is returned; administrator status does not make the
personal server count include other players. Match times come from scheduled
Bracket matches for the account's mapped team. Unscheduled, draft, scored,
cancelled and past matches are excluded. Unavailable services are labelled.

Use **My profile → Change avatar** to open the native forum uploader. The
supplied `avatar/avatar.png` was saved for admin through that uploader. Avatar
images need a readable/traversable `custom_avatar` directory; installation and
repair preserve mode 0755 for this image folder. Private attachments and
configuration retain their restrictions. The native signature-preview cache
now uses the numeric member ID, avoiding an array-to-string warning on profile
saves. The home hero and top bar no longer show the coat of arms; sidebar
branding is retained.

Validation: 26 account/community/personal-status unit tests passed on Linux.
Separate loopback SMF/Bracket databases passed actual next-match selection,
forum counts, verified identity, anonymous rejection and the existing voting,
deletion, restoration and trophy checks. Fresh authenticated HTTPS verified
the saved PNG and status endpoint. The real browser showed two owned running
servers; only the temporary Elite Force test was stopped. The player's Quake
Live match stayed running. Isolated validation services were stopped.
Installed PHP regression tests passed sessions, last visits and signature
preview with warnings promoted to exceptions. Screenshot:
`outputs/Personal-bar.png`; sanitized result:
`outputs/Personal-bar-validation.json`.

## Forum notification repair — 2026-10-08

The error log contained three new cron warnings in
`Sources/tasks/CreatePost-Notify.php:134`. The permission loop unpacked
PostgreSQL's `false` end-of-results value as an array. It now checks the fetched
row before unpacking it. Allowed and denied groups are preserved; no board
permissions or notification preferences changed.

The installed PHP regression test passed empty permission sets and allowed,
denied and mixed rows with warnings promoted to exceptions. The actual installed
notification task also passed native PostgreSQL queries for General and
Tournaments. That check uses an edit with no mentions/quotes and message ID 0;
it sends no notifications and edits no posts. Its native task base is loaded from
the pinned cron source. Test: `tests/test_forum_notification_live.php`.

A fresh authenticated login passed the index, both demo threads and admin error
log. The normal web cron endpoint returned HTTP 200 with its GIF response.
The error log remained at four retained entries (last ID 184), and the background
queue was empty after verification. The older signature-preview warning is
historical and was repaired earlier. Existing posts, private messages, tournament
data, accounts and game services were preserved; no service restart was needed.
