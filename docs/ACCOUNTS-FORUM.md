# Local accounts and forum

Open `https://192.168.8.138/`. HTTP redirects to HTTPS. The root opens Downloads for logged-in players and sends guests to `/login/`. Only the login screen, appearance assets and login/registration endpoints are public. Downloads (including direct URLs, HEAD and range requests), servers, browser chat, forum and administration require a valid account session. The local CA certificate is available at `/style/lisp-lan-ca.crt`; trust this CA on player machines after checking it with the LAN host. This change does not install a trust certificate on players' computers.

The initial administrator is **admin**, using the existing network-administration password. Its existing password-change requirement is retained. It was bound to the administrator PC's server-observed LAN IP and MAC during deployment. SSH and game passwords remain separate. Existing old network-admin and nickname-chat cookies no longer grant access.

## Players

Create an account at `/login/` with a name of 2–20 letters, digits, underscores or hyphens, starting with a letter, and a password of 12–128 characters. Registration creates a player, never an administrator. The server binds the account to the actual request IP and the MAC seen on its directly connected LAN interface; clients cannot submit their own MAC or identity headers. Players must be directly on the same LAN as the server. Routed connections and unidentified interfaces are rejected.

Sessions last eight hours, use HttpOnly/Secure/SameSite cookies, and are checked against both the saved IP and MAC on every request. The password is stored as a salted scrypt hash. DHCP address changes and randomized/new MACs require rebinding by an administrator. DHCP reservations and stable client MAC settings reduce interruptions. A MAC identifies an observed LAN interface, not a tamper-proof hardware identity; passwords are still required.

Use the account controls at the top of the forum to change your password or log out. Name, role, IP and MAC appear in the shared top bar. Temporary passwords set by an admin must be changed before downloads, chat or any other protected functionality becomes available. Browser chat automatically uses the account name. IRC clients use the same account name and a one-time two-minute connection code generated under **Use an IRC client** in the chat sidebar as the server password on port 6667, channels `#general`, `#shooter` or `#strategy`. Never enter an account password into the IRC client. Codes are bound to IP/MAC; account changes revoke IRC sessions and unused codes.

## Administration

The Accounts page lists account names, roles, bound IP/MAC, enabled state and temporary-password status. Administrators can create accounts, set a temporary password, disable/re-enable a player, change another account's role and bind a changed interface selected from the server's observed neighbour list. A changed/new device must connect to the LAN and contact the server before it appears. Rebinding and resets revoke existing sessions. Administrators cannot disable or demote their current account; at least one enabled admin is retained.

The Network page now uses this same administrator session. Its existing gateway settings, firewall rules and network rollback mechanisms are preserved. All authenticated players can see and join active matches. The controller assigns the creator from the authenticated session, ignores a submitted owner ID, and permits stopping only by that creator or an administrator. Unauthorized stop requests are rejected by the backend, even if a player constructs the request manually. Browser Stop buttons follow the same rule.

Interface binding applies to the portal and IRC; it does not replace game-engine connection/password controls, SSH/SFTP authentication or household-router security. Game clients still use the running server's game password when configured.

## Recovery when an admin interface changes

Another logged-in administrator can bind the new interface. If no administrator can log in, connect through the existing SSH account and run on the Linux PC:

```sh
sudo lisp-account-recovery bind --name admin --ip NEW_LAN_IP
sudo lisp-account-recovery password --name admin
```

The new device must be visible on the directly connected LAN. Password recovery prompts locally, never accepts a secret as a command-line argument, and requires a new password at the next login. Recovery preserves forum posts and game files. Use `BOOTSTRAP_IP` when installing a fresh server; bootstrap imports the existing network admin hash when available or prompts for an initial password. Never include private database or bootstrap credential files in a source archive.

## Forum

Simple Machines Forum 2.1.7 now provides General, Games, Servers, Tools, Emulators and Tournaments. It uses the existing LAN account and server-observed interface binding. Players can start topics/reply and use native forum features; administrators moderate. Names, passwords and roles are managed in the LAN Accounts page, with no separate forum registration. Native forum formatting and filtering replace the old plain-text renderer.

Voting, Bracket tournaments, automatic Tournament threads and trophies are integrated; see [community guide](COMMUNITY.md). SMF stores posts in the private `lisp_forum` PostgreSQL database. The previous account database and legacy forum backup remain private; old forum writes are disabled. Nginx checks the bound account for every protected route. Public profile responses contain names, dates and trophies, never IP/MAC or password hashes.

## Validation

Run `python tests/test_accounts.py` for binding changes, session theft across interfaces, CSRF, reset/change, roles, disabling, session expiry/logout, one-use IRC codes, forum persistence and moderation. The live integration test requires a LAN client, the trusted LAN CA and SSH administration for its disposable test accounts. It uses two free slots and stops only its own SoF2 tests. Existing legacy test tools that call unauthenticated APIs must be updated to provide the bound session and CSRF token.

## Trophy Room — 2026-10-09

The authenticated Trophy Room lists enabled accounts with forum avatars and
gold/silver/bronze totals. Clicking a player shows confirmed medals and games.
Its API returns no interface binding or credential data. Profiles and avatar
editing remain available through the forum and top-bar avatar.
