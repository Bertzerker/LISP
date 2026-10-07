# Community integration completed — 2026-10-08

Forum: https://192.168.8.138/forum/ — Simple Machines Forum 2.1.7, existing LAN login, dark portal backgrounds, white text and cyan links, including the post editor.

Tournaments: https://192.168.8.138/tournaments/ — game voting, automatic Bracket creation, account-mapped signups, forum thread updates and administrator-confirmed profile trophies. Twenty-one unit tests and the separate-database live workflow passed. Match scoring uses Bracket's organizer UI; final podium requires explicit admin confirmation.

Admins now have Delete tournament for unfinished zero/one-player events. It removes the active card, publishes cancellation, blocks further activity and awards no trophy. Show deleted tournaments provides restoration. The administrator subsequently cancelled UT through the new control; its retained roster and forum thread show cancellation. Validation did not delete this event.

Validation proof: Community-live-validation.json. Screenshots: Forum-dark-theme.png, Tournaments-admin-controls.png, Bracket-home.png. Temporary validation services were stopped; normal services remain active.

Docs: docs/COMMUNITY.md. Reproducible runtime/deployment/frontend/source-package scripts are included. The shareable LISP-source.zip excludes the entire Game Files directory, game data/binaries/ISOs, private databases, app credentials and keys. Bracket corresponding source is offered separately at /community-source/.
