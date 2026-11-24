# Disable autostart (开机自启) for Electron/Chromium apps on macOS

Worked on: QuarkCloudDrive (夸克网盘) v7.0.6, macOS 27, 2026-08-07.

## The three layers that must ALL be cleared

Chinese vendor Electron apps (QuarkCloudDrive, likely 百度网盘/迅雷 etc.) register
autostart in up to THREE places. Clear all three or the app silently re-registers
the login item on next quit/launch (the app-internal switch is the one that bites).

### 1. macOS login items (系统登录项)

```bash
# Check
osascript -e 'tell application "System Events" to get the name of every login item'
# Remove (name = the display name shown by the check, e.g. 夸克网盘)
osascript -e 'tell application "System Events" to delete login item "夸克网盘"'
# Verify — empty output = none left
osascript -e 'tell application "System Events" to get the name of every login item'
```

### 2. launchd plists

```bash
ls ~/Library/LaunchAgents/ /Library/LaunchAgents/ /Library/LaunchDaemons/ | grep -iE "quark|pan"
# Empty = not registered via launchd (QuarkCloudDrive wasn't)
```

### 3. App-internal preference.json (the one that re-adds itself)

Electron apps store the switch in `~/Library/Application Support/<App>/preference.json`.
QuarkCloudDrive keys:

```json
{
  "global:setting": {
    "initedAutoLaunchEnable": false,
    "permissionSwitch": { "autoLaunchEnable": false }
  }
}
```

Edit in place with python3 (app is running, so write atomically and immediately):

```bash
cd ~/Library/Application\ Support/QuarkCloudDrive && python3 -c "
import json
p = 'preference.json'
d = json.load(open(p))
d['global:setting']['permissionSwitch']['autoLaunchEnable'] = False
d['global:setting']['initedAutoLaunchEnable'] = False
json.dump(d, open(p,'w'), ensure_ascii=False, indent=2)
"
```

Both keys MUST be false — leaving `autoLaunchEnable=true` means the client re-adds
the login item on next exit. `grep -rilE "auto.?start|auto.?launch|login.?item|open.?at.?login"` in
the app data dir finds which file holds the switch.

## Notes

- Deleting only the system login item is NOT enough — verify the app-internal flag too.
- To restore later: app settings toggle 开机自启, or flip the JSON keys back to true.
- User's QuarkCloudDrive profile dir is a full Chromium profile (Default/, Cache/,
  SingletonLock) — treat it like browser data, don't rename/delete blindly.
