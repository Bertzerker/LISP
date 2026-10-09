# Server load and Credit Tokens

Game Servers and My Servers display each engine's current CPU use, rolling CPU
average, received/sent LAN traffic and network average. Samples arrive every
five seconds; visible cards refresh every ten seconds. The rolling window is
about a minute, shorter just after launch. CPU 100% means one core, so a
multithreaded engine may exceed 100%. Stopped entries retain their last sample.

Linux cgroup v2 CPU accounting includes the engine and its descendants, including
Wine/Java processes. A small privileged local service counts incoming/outgoing
IPv4 LAN bytes on the instance's game, query and admin ports. Counters include IP
headers and discovery/admin traffic, not Internet updates/downloads or unrelated
host traffic. No packet contents are recorded. Counter rules have no accept/drop
verdict and change no existing firewall permissions. The helper and internal
billing operations accept only root or the actual systemd controller process;
game processes cannot directly manipulate billing through the local socket.

See the [Linux cgroup documentation](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html)
and [nftables counter documentation](https://wiki.nftables.org/wiki-nftables/index.php/Counters).

## Admin setup

At /accounts/, every account has a balance and **Add Credit Tokens** control.
Top-ups are positive, audited and idempotent; they do not revoke player sessions.
At the bottom, **Credit Token worth** defines:

- CPU core-minutes per token (default 60).
- Network GiB per token, received plus sent (default 1).
- Maximum negative balance in tokens (default 0).

These defaults mean one CPU core running fully for an hour costs one token;
one GiB of combined LAN traffic costs another. For example, 25% of one core for
an hour plus 0.5 GiB costs 0.75 tokens. CPU and network charges are added.
With the default negative limit of zero, players need a positive balance before
starting. Set a positive debt allowance or grant tokens to let them play.
Administrator-owned servers are exempt, even with zero tokens. Restarting
another player's entry as admin retains that player's ownership and billing.

Rates apply to subsequently settled usage intervals, about five seconds. Charging
uses accumulated core-time and bytes: average load multiplied by elapsed time.
There is no flat time charge or repeated charge for each card refresh. Fixed
millionths of a token and fractional carry avoid lost small charges. The
per-session ledger and cumulative counters prevent duplicate charges on retries.
Balances are shared across all servers owned by the account. CPU includes launch
and shutdown work; stopped servers cost nothing. Only the creator/admin sees
that entry's session cost and estimated tokens/hour. Own balance and debt limit
appear on the game pages.

At the configured debt floor, all of that player's running servers use their
normal save-and-stop path; their entries, settings and worlds remain. The balance
never debits below the limit. Top up before restarting. Admin servers remain
unaffected. If monitoring/accounting fails for 30 seconds, charged servers stop
safely; admin servers remain running. Pending cumulative samples are stored
privately and retried without duplicate debits. A stopped entry explains why.

Account database/ledger, presets, worlds and pending samples remain private and
are excluded from source archives/Git. This is a local credit system only:
no real payments, purchases or currency exchange are connected yet.

## Validation

Thirty isolated Linux tests passed for accounts, shared balances/debt limits,
CPU+network math, fractional carry, retries, persistent records/worlds, controller
peer restrictions, owner-only stopping and counter scoping. UI fixtures verify
CPU/network/cost labels and preserve Join, stopped port controls and management.
Two real Quake Live instances passed separate cgroup CPU and Windows LAN byte
counters: admin cost stayed zero and the disposable player's balance decreased.
The browser Add tokens button and bottom settings were verified. At the unchanged
production floor (zero), only the disposable player's server stopped; the admin
instance kept running. A negative allowance of two tokens was tested in the
isolated account database. The hardened controller channel was retested live;
an ordinary lanserver process was rejected. No existing accounts, matches,
worlds, ports or firewall permissions were changed. Disposable test account and
test metadata were removed/archived privately; both baseline entries remain.
Native survival-world save behavior was already validated in SURVIVAL.md; this
change reuses that path and did not launch heavy survival worlds for billing tests.

Evidence: outputs/Credit-load-live.json, outputs/Server-load-cards.png and
outputs/Credit-token-settings.png. All eight checked services remained active.
