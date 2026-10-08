# Local Mumble voice

Connect with the Mumble desktop application to **192.168.8.138:64738**.
The sidebar's **CHAT // MUMBLE** tabs switch between text messages and the
live voice tree. The selected view is highlighted and remembered. **Join voice**
opens the native app using your portal name. General, Shooter and Strategy
are real server channels. The box grows with channel occupants.

The viewer requires a logged-in portal account and refreshes every 15 seconds
while visible; its local snapshot cache lasts 10 seconds. Native Mumble accepts
LAN guest identities independently of portal accounts. It does not authenticate
portal passwords or bind native guests to portal IP/MAC identities. Use the
Mumble client to manage microphone, mute, channel membership and identity.
No browser audio or web microphone permission is required.

## Install and operate

On the configured CachyOS/Arch host, after the portal/community installation:

```sh
sudo env LAN_HOST=192.168.8.138 LAN_CIDR=192.168.8.0/24 bash scripts/install-mumble.sh
sudo systemctl status mumble-server lisp-mumble-view
```

The native service starts at boot. TCP and UDP 64738 are allowed only from
192.168.8.0/24 to 192.168.8.138. Mumble binds that LAN address. Ice RPC is
loopback-only on 6502; the channel viewer's bridge is loopback-only on 8810.
nginx authenticates `/mumble-api/` before forwarding requests.

A random SuperUser password is stored only at
`/etc/lisp/mumble/superuser-password`, readable by root. To administer the native
server, privately read that file on the host, then connect as **SuperUser** in
Mumble. It is separate from the portal administrator password. Config backups,
RPC secrets, native certificate/private key and the server database stay on the
host, outside the source project and archive. The generated native certificate
is self-signed; verify its fingerprint before trusting it in the desktop client.

The viewer runs as the separate unprivileged lispvoice user with distinct read/write Ice secrets. Its service receives only the
read secret and returns channel names, user names and mute/deafen flags, never
IP addresses, certificates or credentials. The write secret is used only by the
root installation/channel setup utility. The bridge uses the installed matching
MumbleServer.ice schema and pinned official `ice` npm package 3.7.100. The local
widget adapts [alfg/mumble-widget](https://github.com/alfg/mumble-widget)'s CVP
concept to safe DOM rendering, without CDN libraries, JSONP or eval. See
[third-party notices](../THIRD-PARTY.md).

## Live verification — 2026-10-09

Windows LAN UDP ping, pinned-certificate TLS authentication, native guest login,
channel switching and actual viewer membership passed. Viewer requests without
portal authentication returned 401. Seven temporary Player1–Player7 clients
joined alongside the existing admin client. All eight appeared in the proper
channels; the box grew from about 435 to 621 pixels with no clipped users and
shrunk after cleanup. Only the seven owned test clients were disconnected.
The real admin client remained in Shooter. Screenshot:
`outputs/Mumble-eight-users.png`; results: `outputs/Mumble-validation.json`
and `outputs/Mumble-growth-validation.json`. Microphone/audio playback was
not exercised by the automated clients.

Sources: [Arch package](https://archlinux.org/packages/extra/x86_64/mumble-server/),
[Mumble administration](https://www.mumble.info/documentation/administration/config-file/),
[Mumble protocol](https://github.com/mumble-voip/mumble/blob/master/src/Mumble.proto).
