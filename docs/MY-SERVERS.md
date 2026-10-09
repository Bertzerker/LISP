# My Servers

Open **03 / MY SERVERS** or the server activity link in your top bar.
Your own starting, running, failed and stopped servers remain listed separately.
**Stop** saves a persistent world and releases its ports. **Restart** reuses the
same server entry, owner, game, map, mode, player limit, passwords and world.
Restarting a running server first stops it safely. Stopped entries survive a
controller or PC restart and do not start automatically.

Only the creator or an administrator can stop or restart a server. Admins also
see other owners' entries; restarting those keeps the original owner. Saved
world selection is limited to its owner or an admin. Account binding, CSRF
protection and roles remain. Game Servers has launch and Join controls; all
management buttons are on My Servers. Stopped entries have **Delete entry** on My Servers. This hides the entry and
keeps its world. **Deleted server entries → Restore entry** brings back its
settings without starting it. Only its creator or an admin can delete/restore.
Game Servers has no management or delete controls.

While a server is stopped, its creator or an administrator can select a new
**Server port**, then click **Save port**. **Automatic — choose a free port**
selects one for you. Saving does not start the server; use **Restart server**
when ready. The same entry, owner, saved world, map, mode, player limit and
passwords are retained. Join instructions and related admin ports update.

Stopped servers release their ports. If another server takes one, the entry
shows **This port is in use**, and Restart stays disabled until you save a free
port. Busy choices are disabled. Game, query and admin sockets, plus instances
still starting, are checked when saving and again at restart. A saved port is
not reserved while stopped, so another player may take it later.

There are **36 port choices (27015–27050)**: the original four plus 32 new choices.
Automatic selection skips busy game/query/admin ports. Six servers may run at
once; stopped and failed entries do not occupy a slot. Multi-port games reserve
additional ports, so not every base port is valid for every engine.
Large survival worlds share this PC's memory; six is the controller limit,
not a guarantee that six heavy worlds will perform well together.

Private restart presets under `/srv/lan-party/servers/records` have owner-only
permissions. They contain launch passwords and are never returned by the API
or included in the shared source. Deleted presets remain privately under
`deleted-records` for Restore; saved worlds stay selectable. Disposable copies are removed on clean stop;
survival progress is separate under `worlds/GAME/ID`. A requested restart after
an interrupted exit checks that no live process references that exact instance
folder before preserving its stale logs under `retired-instances`. Installed
games and worlds are not deleted. Nothing starts automatically after reboot.

The page refreshes every 10 seconds while visible; the top bar every 30 seconds.
Tests cover ownership, secrets, durable records, limits, Stop/Restart controls
and stopped-server port changes, including related socket collisions.
See [Survival servers](SURVIVAL.md) for game versions and native admin differences.
