# Download refresh — 2026-10-08

Fixed the automatic download index. Windows CRLF line endings in the deployed generator caused systemd to fail with `203/EXEC` on every timer run.

The deployed file now uses LF. The service and installer invoke Python explicitly to prevent the same failure when source files are copied from Windows.

The normal timer successfully detected an owned test upload without manual indexing. It remains active and enabled after reboot. The probe was removed. All 84 generated links match the current completed uploads; the recent emulator, Generals and Carmageddon additions are included.

Uploads belong in `/srv/lan-party/files`. Wait about a minute, then reload `/downloads/` to see new links.
