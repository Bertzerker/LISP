# Soldier of Fortune II Gold

The launcher now uses the community-patched Gold Linux executable supplied by SoF2.org: https://www.sof2.org/download.php?id=3597&current=1 . Its downloaded archive SHA-256 is `8bd4721b6ffe0840040b0250e2216a7b3cc333a84945c6664c18d5d0559fe3d5`; executable SHA-256 is `3d477bd0225d77d1be2e792fac9e07e38b43e21ef18a1c5962ef3b75fe467009`.

Select **Soldier of Fortune II Gold (1.03)** at http://192.168.8.138/servers/. Templates live in `/srv/lan-party/servers/templates/sof2`. Gold update102.pk3 and update103.pk3 are now active alongside update101 and the retail data. The previous 1.01 installation is preserved at `/srv/lan-party/servers/sof2-backup-101`.

The Linux engine retains its historical `SOF2MP V1.02a` and `sof2mp-1.02` strings while reporting protocol **2004**. The LinuxGSM Gold reference executable has the same historical version string; these strings alone do not indicate a failed update. A real Gold player connection has not yet been tested.

Five modes and the maps discovered from installed PK3 files remain available. Each match has its own data copy, private configuration, home and UDP port within existing LAN ports 27015–27018. Two simultaneous matches of the same game are supported. No firewall changes were needed. Internet master registration, PunkBuster and server downloads remain disabled for LAN use.

## Runtime compatibility

The Gold binary requires the Intel legacy `libcxa.so.1`. It is installed beside the executable, extracted from the LinuxGSM Gold package (https://linuxgsm.download/SoldierOfFortune2/sof2gold-1.03.tar.xz; upstream MD5 `201e23bab04207d00ce813d001c483d9`). Its lookup path is private to SoF2 children.

On this PC the old Intel-compiled binary crashed in modern `libnss_resolve` because its DNS calls use a four-byte-aligned stack. `src/sof2-dns-compat.c` realigns that call before forwarding it to the normal resolver. Its compiled library is preloaded only for SoF2; system DNS settings remain unchanged.

## Joining and administration

Use the running match's Join button for console-command assistance. Open the multiplayer console (~), then enter `connect 192.168.8.138:PORT`. For protected matches set `password YOUR_JOIN_PASSWORD` first. For administration set `rconpassword YOUR_ADMIN_PASSWORD`, then use `rcon status` or another command. The portal keeps both passwords in private instance files and never returns them through its API. Browser launch of a non-Steam game requires a separately configured client protocol handler.

CLI: `lan-server start --game sof2 --mode dm --map mp_shop --players 8 --ask-passwords`. Use `lan-server list` and `lan-server stop INSTANCE_ID` for the same instances.

## Reproduce the update

First install the existing retail template with `scripts/install-sof2.sh`. Then obtain the two checksum-matched archives above and run `sudo bash scripts/update-sof2-gold.sh /path/sof2dedGOLD.zip /path/sof2gold-1.03.tar.xz`. The updater requires no active matches, stages the change, compiles the private compatibility library with 32-bit GCC support, and saves a timestamped rollback template. Deploy the current adapters.py and restart lan-portal only with no active matches. Source archives exclude licensed game files and compiled binaries.

For rollback, stop all matches, preserve the Gold template, restore the 1.01 backup and restore the previous 1.01 adapter launch configuration before restarting the controller.

## Validation

Two Gold instances passed live UDP readiness with Deathmatch/mp_shop and Team Deathmatch/mp_kam1, distinct ports, actual protocol 2004 and g_needpass=1. Correct RCON authentication succeeded and the incorrect password was rejected. Stopping one preserved the other. All test matches were cleaned up. The user subsequently confirmed a successful connection and working match.
