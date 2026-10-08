# Voice and Steam additions — 2026-10-09

Enabled: Contagion and Brink. All 21 earlier games remain present. Catalog and
active-server view sort by game name. Both additions passed paired engine,
LAN/password and authenticated portal ownership/readiness/independent-stop checks.
Contagion has 83 maps/six modes; Brink has 10 maps/two modes. Private official
runtime compatibility repairs preserve Steam originals. Game client joining
has not been tested. See docs/STEAM-EXTRAS.md.

Mumble runs on 192.168.8.138:64738, LAN-only TCP/UDP, with three real channels.
Authenticated portal tabs toggle CHAT // MUMBLE with highlight and remembered
selection. Seven temporary clients plus the existing admin proved all eight
users display without clipping: box grew about 186 pixels and shrank on cleanup.
Existing native admin connection was preserved. No microphone/audio test.
Native guests are separate from portal account authentication. See docs/MUMBLE.md.

Chat expiry is 7200 seconds across all rooms, with a 30-second idle sweeper
and server-clock frontend expiry. Nine Linux tests and live API checks passed.
No game test instances or seven test voice clients remain. Game files, private
credentials/databases, runtime binaries and the entire Game Files folder are
excluded from the refreshed shareable source archive.
