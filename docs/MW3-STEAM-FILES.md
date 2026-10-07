# MW3 legacy server files

The installed Steam version uses newer assets that do not currently load in
the prepared Plutonium server. The private server copy passed the missing DLL
imports but failed loading its default rawfile assets. Anonymous SteamCMD was
refused with `missing license for depot (No subscription)`; no downloaded
legacy files were applied.

Use the Steam account that owns MW3 on the Linux PC. Open Steam's console with
`steam://open/console`, then enter these commands one at a time:

```
download_depot 42680 42682 6067691797475126381
download_depot 42680 42683 6381783964590594065
download_depot 42750 42751 9089183337461621316
```

Wait for `Depot download complete` for every command. These are the older base,
English-language and dedicated-server depots from the
[firsthand Plutonium downgrade guide](https://forum.plutonium.pw/topic/46446/mw3-downgrade-and-update-prevention-guide).
An access error means that depot was not downloaded; do not treat it as a
completed install. No Steam password or product key should be sent to chat.

Leave the results in Steam's `steamapps/content/app_42680/depot_42682`,
`app_42680/depot_42683` and `app_42750/depot_42751` folders and report that
the three downloads completed. They will be inspected and copied into the
private LAN server template for testing. Do not overwrite the working Steam
game, change its manifests or unpack game data into the shareable project.

The current official x64 dedicated launcher was also tested. It reports:
“The Local Dedicated Server function for MW3 is temporarily disabled.”
Direct dedicated engine startup exited without readiness. The player's Steam
installation was not modified.

MW3 stays hidden until its engine starts and its two-instance LAN and password
tests pass. The user explicitly requested skipping player connection tests;
no additional player connection test is required. These
downloads are a compatibility attempt, not a guarantee that every map or DLC
will work. DLC files require their own ownership and were not requested here.
