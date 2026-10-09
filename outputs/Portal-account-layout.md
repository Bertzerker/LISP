# Portal account layout — 2026-10-09

Live: https://192.168.8.138/

- Home removed; logged-in default is Forum.
- Top bar shows own name, role, IP and MAC beside avatar/activity.
- Forum has Log out and Change password, using the existing bound account session and CSRF protection.
- Public `/login/` handles login, registration and required temporary-password changes.
- IRC code creation moved to the chat sidebar.
- Live route/access/logout checks and shared form-transition tests passed. Browser root-to-Forum and forum password-panel checks passed.
- No real password was changed; successful password changes were tested with a fake transport. Existing authentication and roles remain intact.
- Website and forum worker reloaded; game controller and matches were not restarted.

Screenshot: Portal-forum-account.png

## Forum refinement

Menu order: Forum (home), Game Servers, My Servers, Tournaments, Trophy Room, Downloads, admin-only Accounts, admin-only Network.

Headline and SMF branding are hidden. Search input and scope dropdown share one line. Profile, My Messages and Alerts have explicit spacing without being squeezed; search wraps as a complete row on smaller screens. Log out and Change password are below the forum footer. Actual search, live menu/landing-page checks and unchanged account protections passed. See Portal-forum-layout.png.
