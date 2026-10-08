# My Servers

Use **04 / MY SERVERS** or the server activity link in your top bar to open
https://192.168.8.138/my-servers/. Your servers lists instances created by your
account, including starting, running and failed instances. Multiple servers of
the same game are shown separately with their ports. Running servers retain
their Join buttons and connection instructions.

Stop a server here, or dismiss its entry if startup failed. Persistent worlds
keep their Save & stop behavior. A stopped entry disappears after the request
completes; failures remain visible with an error so you can retry.

Administrators also have an Other players’ servers section for authorized
management. Players do not see that section. Existing backend permission checks
still require the creator or an administrator and a bound account/CSRF token;
the page does not change account roles or permissions.

Game Servers remains the launcher and public active-server list for logged-in
players. It has Join controls and a link to My Servers, with no Stop or failed
entry dismissal controls. Neither page deletes installed games or game files.

The page refreshes every 10 seconds while visible. The top-bar activity keeps
its existing 30-second refresh. Installation and community deployment scripts
publish both pages and their shared server-card script. Production publication
was static only: no controller restart, firewall change or existing match stop.

Validation on 2026-10-09: isolated JavaScript fixtures cover ownership filtering
across same-game instances, administrator controls, forbidden Stop controls on
the public list, retained Join controls, failed dismissal, refresh and empty
state. Run `node tests/test_my_servers.js`. Live HTTPS checks passed new-page and
script authentication. The real browser launched one temporary Quake Live match
as Robertkopp, verified no Stop on Game Servers, navigated through the activity
bar, and stopped that exact owned match on My Servers. The test was cleaned up.
Screenshots: outputs/My-servers.png and outputs/Game-servers-no-stop.png.
