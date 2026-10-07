# Quake Live connection diagnosis

The original configuration used `sv_serverType 1` and `sv_lan 1`. A direct UDP connection challenge from the Windows LAN PC reproduced: `Server is for LAN clients only.` This was a server response, not a firewall timeout.

New instances use `sv_serverType 2`, `sv_lan 0`, and `sv_master 0`. This avoids the game's LAN-only address rejection while leaving public listing disabled. The host firewall still permits game traffic only from the configured LAN. No router forwarding is needed.

Default game ports are UDP 27015–27018, one per instance, with separate home/config/log directories. Choose automatic assignment or a specific free port. The Steam LAN browser's conventional 27015–27020 scan range does not make a hidden server visible: `sv_master 0` deliberately disables browser queries. Use `/connect SERVER_IP:PORT`.

The portal checks the `getchallenge` endpoint instead of `getinfo`, because hidden servers suppress browser queries. It displays configured player slots; it does not claim to measure live player counts. The unauthenticated probe now receives `No Steam auth token.` instead of `Server is for LAN clients only.` The readiness check accepts that authentication-stage response or a challenge response. This verifies server reachability and removal of the LAN rejection, not the full Steam-authenticated player join. Test that final step in a licensed Quake Live client signed in to Steam.

The supplied `quake live.MD` is retained as a research note. Its claims that all LAN play is disabled or that free accounts require old paid subscriptions are not established by the shipped server documentation. The installed dedicated-server default configuration documents server types 0/1/2 and the browser-query behavior of `sv_master`.

References: installed `baseq3/server.cfg` and `server_readme.txt`; https://steamcommunity.com/sharedfiles/filedetails/?id=542966946 (readme repost with additional community notes).


Confirmed: the user successfully connected from Quake Live after this fix.
