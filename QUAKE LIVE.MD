Quake Live has effectively disabled true LAN play; the game is designed to connect exclusively to id Software's online servers.  While the server command sv_serverType 1 (LAN) exists, it is often bugged or blocked by Steam's infrastructure, resulting in the "server is for lan clients only" error even for local connections.

To host a playable game locally, you must use the following workaround:

Set the server variable to sv_serverType 2 (Internet) in your server.cfg or launch parameters.
Set sv_master 0 to prevent the server from listing on public internet master servers. 
Ensure the server is listening on ports 27015–27020, as these are the only ports scanned by the Steam LAN browser filter. 
Clients must connect manually using the console command: connect <LAN_IP>:<PORT> (e.g., connect 192.168.1.50:27015), as the server will not appear in standard game browsers.
Note that this method requires Steam to be running and may still be restricted by id Software's infrastructure for free-to-play accounts, which often require paid subscriptions to host private servers.