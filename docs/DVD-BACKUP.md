# World at War DVD image

The original CODWAW disc in drive I: was copied to `Game Files/World-at-War-DVD.iso` (7,325,483,008 bytes). The adjacent `.iso.sha256` file contains its SHA-256 checksum:

`f0b736dae8b9ef4bb67c794092d995effe56b49d8b4584b956745f985688c269`

The earlier raw copy stopped 65,536 bytes from the end because Windows limited access at the volume boundary. A read-only handle using `FSCTL_ALLOW_EXTENDED_DASD_IO` read those final bytes successfully. The retained prefix was compared with the DVD at six positions, including the copy boundary, and the complete saved image was hashed and checked against the retained prefix plus the newly read tail. This was not a new comparison of every earlier sector with the DVD.

All ISO9660 and Joliet file extents fit within the completed image. `CoDWaW.msi`, `setup.exe` and `autorun.inf` matched the DVD byte for byte. No game installation was started. The ISO and game files are excluded from the shareable source ZIP.

Windows API reference: [FSCTL_ALLOW_EXTENDED_DASD_IO](https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_allow_extended_dasd_io).
