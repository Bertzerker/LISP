# Local chat

Chat appears on the right of each portal page and requires a logged-in local account. Your nickname is your account name; it cannot be freely changed to impersonate another player. Browser chat uses HTTPS and shares local history with authenticated IRC clients.

Use the Chatroom selector in the right sidebar to choose **General**, **Shooter** or **Strategy**. Each room has separate messages and an online-player list. Your room selection is remembered in the browser, and unsent drafts are retained separately while switching rooms. Existing chat messages were migrated to General without changing their contents or IDs.

For IRC, open **Use an IRC client** in the chat sidebar and generate a one-time connection code. Use your account name as nickname and the code as the server password, connecting to 192.168.8.138:6667 and join #general, #shooter or #strategy. The old #lan channel remains an alias for General. IRC clients can join multiple rooms; messages are delivered only to the matching room. Codes expire after two minutes, work once and are bound to your LAN IP/MAC. Never enter your permanent account password into IRC. Resetting, disabling or rebinding an account revokes its old sessions and unused codes.

Messages are limited to 500 characters and rate limited. Browser messages are rendered as text. Messages expire after two hours in every room, with a cap of 1,000 messages per room. Expired rows are removed on reads, sends and startup, and by an idle cleanup every 30 seconds. Already-open pages remove expired messages using the server clock. Rate limiting applies across rooms, so switching rooms does not bypass it. The account service owns identities; `lisp-chat.service` owns chat history at `/srv/lan-party/chat/chat.sqlite3`, runs as lanserver, and serves its web API only on localhost:8789. Restarting chat disconnects IRC clients without stopping game matches. Keep histories and session cookies outside the source archive.

See [ACCOUNTS-FORUM.md](ACCOUNTS-FORUM.md) for registration, binding and recovery.


Chatroom deployment was validated on 2026-10-06: 13 Linux tests passed,
including legacy database migration, room/history/presence isolation, retention,
authentication and actual loopback IRC sockets. Real LAN HTTPS and authenticated
IRC checks passed all three rooms, cross-room isolation and PART presence.
Owned test accounts/messages were removed. Browser switching passed General,
Shooter and Strategy; the old General message remained visible. Only chat was
restarted; the game controller was not restarted. A private pre-update database
snapshot is retained under /srv/lan-party/chat/update-backups for rollback.

Click **CHAT // MUMBLE** at the top of the sidebar to switch between text chat
and voice channels. The active tab is highlighted; the chosen view and chatroom
are remembered. Unsent drafts remain when switching views. Mumble refreshes
every 15 seconds while its tab is visible. See [MUMBLE.md](MUMBLE.md).
