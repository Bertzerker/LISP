# Trophy Room

Open https://192.168.8.138/trophies/ or **07 / TROPHY ROOM** with your LAN account.
Every enabled player appears with their forum avatar (or initial when none is set)
and separate gold, silver and bronze totals. Players are ordered by gold, silver,
bronze and then name. Click a player to see the medal, game, tournament link and
award date. Players without awards have an explicit empty state.

Only administrator-confirmed final tournament results count. The stored voting
option supplies the game name even if that game is later removed from the server
catalog. No new awards or sample production trophies are created by this page.
Disabled accounts are omitted. Account identifiers, names, avatars and medal
totals are returned; password data, IP and MAC addresses are not included.

Profiles and avatar editing remain in the forum. The top-bar avatar opens the
native forum profile. Old `/profile/?user=ID` links redirect to the corresponding
Trophy Room player page; the native forum Trophies tab links there too.

The existing bound LAN login protects both the page and its API. A signed,
loopback-only forum bridge reads native avatars, cached for 25 seconds. If the
forum is temporarily unavailable, medal totals remain available with initials.

Deploy with `scripts/deploy-community.py` as part of the existing community
installation. This feature adds no database migration or firewall rule. The
production change has a private backup under community-setup/backup/trophy-room-*.

Validation on 2026-10-09: 15 isolated Linux unit tests passed, including historical
game labels, all medal ranks, final-only counting, zero-award players, sorting,
avatar caching and recovery. Live HTTPS checks verified all 10 enabled players,
avatar images, matching totals, anonymous rejection and the forum-profile link.
Browser checks verified the directory and Robertkopp detail/back navigation.
The live database currently has zero confirmed awards; none were fabricated.
See `outputs/Trophy-room-validation.json` and `outputs/Trophy-room.png`.
