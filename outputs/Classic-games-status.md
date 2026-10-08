# Additional dedicated servers — 2026-10-08

Enabled in the authenticated LAN launcher:

- Star Trek: Voyager – Elite Force (native cMod 1.30).
- Star Wars Jedi Knight: Jedi Academy (native OpenJK).
- Wolfenstein (2009), patched Lite Server through isolated Wine prefixes.
- Aliens vs Predator 2: Primal Hunt, dedicated server and supplied community patch.

Two instances per game, maps/modes, eight-player limits, password flags,
external Windows LAN queries and independent stopping passed. Correct/incorrect
LAN RCON passed for the first three engines. Primal Hunt's private native
controller/join passwords and all six modes were checked; native admin commands
require a joined player and remain untested in game.

All four also passed authenticated portal launch, ownership, readiness and
independent stop for two concurrent matches. Original files remain intact;
existing games and other portal services were preserved. No firewall change.
All owned test matches and temporary test accounts were cleaned up.

Actual player joining/playing remains untested. See
[setup and commands](../docs/CLASSIC-GAMES.md) and the adjacent validation JSONs.
