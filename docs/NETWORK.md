# Network & Internet Management

Network administration is at `https://192.168.8.138/admin/`. Log in through Home with an administrator account first. The original administrator is named admin and retains the existing network-administration password. Accounts and sessions are bound to the actual LAN IP/MAC; players cannot access the network controls. Passwords set by an administrator must be changed on Home before accessing protected pages. Authentication and network configuration are not exposed over HTTP. See ACCOUNTS-FORUM.md for account management and recovery.

## Current wiring

The management/upstream Ethernet port `enp3s0` holds 192.168.8.138 and is protected. Wi-Fi is not offered as a managed wired port. The spare Ethernet port `enp2s0` can provide a separate LAN. A bridge requires two spare wired ports; attach another Ethernet adapter before choosing bridge mode. Installation has not moved any existing connection or enabled a new gateway.

## Create the managed LAN

1. Log in and replace the initial password.
2. Choose Separate with one spare wired port, or Bridge with at least two spare wired ports.
3. Preview the plan. The default managed address is 10.42.0.1/24. Overlapping existing networks are rejected.
4. Apply and confirm before the displayed deadline. NetworkManager checkpoints automatically roll back an unconfirmed change after 120 seconds. Existing management/upstream connections are excluded.
5. Connect the player switch to a selected port. DHCP supplies the mini PC as the gateway. Internet starts blocked; enable it globally or restrict individual devices from the dashboard.

Only traffic forwarded through this managed gateway is controlled. Players still connected directly to the household router bypass these controls. The device list combines reachable neighbour entries and DHCP leases, so it is not a guaranteed inventory of every physical device. Per-device rules identify MAC addresses; clients that change their MAC appear as different devices. Local portal, chat and game traffic remain available when Internet is blocked.

The helper installs its own `inet lisp_access` nftables forwarding table, drops managed IPv6 forwarding, and uses NetworkManager's IPv4 DHCP/NAT. When a gateway is explicitly activated, it adds LAN-scoped UFW rules for its services and DHCP/DNS plus a route rule to the protected upstream. It does not replace unrelated firewall rules. Global/per-device Internet controls do not block host input.

## Services and recovery

`lisp-network.service` is a narrow root Unix-socket helper; only the `lanadmin` account or root can call it. `lisp-admin.service` serves the authenticated API on localhost:8788. The website proxies it only through TLS. State and audit records are in `/var/lib/lisp-network`; authentication state is in `/var/lib/lisp-admin`; private certificates are in `/etc/lisp/tls`.

Use the Roll Back button while a plan is pending. Unconfirmed changes also roll back automatically. If a cable or adapter is missing, keep using the original management address. The current physical bridge/DHCP setup needs validation after the player switch and extra adapter are connected; forwarding policy was tested using isolated real Linux virtual networks.
