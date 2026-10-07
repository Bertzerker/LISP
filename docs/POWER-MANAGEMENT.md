# Keeping the LAN server awake

KDE suspended the mini PC during an owned game-client test on 2026-10-06.
The previous boot journal recorded PowerDevil requesting suspend at
06:38:59 CEST, followed by NetworkManager disabling the interfaces and the
kernel entering deep sleep. The server later became reachable again.

`lisp-keep-awake.service` now holds a systemd block inhibitor for idle and
sleep while the LAN portal is installed. The service is enabled at boot;
its running process and actual inhibitor entry were verified. This keeps
automatic desktop sleep from taking the portal, downloads and matches offline.
A privileged deliberate override can still force sleep. Screen blanking,
firewall settings and account permissions are unchanged.

The regular installer copies, enables and starts this unit. For an existing
installation, copy config/lisp-keep-awake.service to /etc/systemd/system/,
then run:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now lisp-keep-awake.service
systemd-inhibit --list
```

To restore desktop sleep behavior:

```sh
sudo systemctl disable --now lisp-keep-awake.service
```

Reference: [systemd-inhibit documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd-inhibit.html).
