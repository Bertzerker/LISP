# Server port changes

Deployed at https://192.168.8.138/my-servers/ on 2026-10-09.

Stop the server, select Server port (or Automatic), click Save port, then Restart
server. Busy ports are disabled and restart checks availability again. Only the
creator or an administrator can change a stopped entry. Settings, passwords,
world and ownership stay intact. Related Join/admin ports are updated.

Validation: ten isolated Linux tests and JavaScript fixtures passed. Real HTTPS
and browser checks passed occupied-port rejection, saving while stopped,
restarting two isolated instances on different ports and independent stopping.
Only the two owned tests were stopped and their entries soft-deleted. Existing
entries remain. Game/player connections were not part of this change.

Evidence: Server-port-live.json and Server-port-change.png.
