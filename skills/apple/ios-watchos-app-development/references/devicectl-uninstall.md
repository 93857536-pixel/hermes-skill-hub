# devicectl app uninstall — syntax + pitfalls

Verified 2026-08-08 while removing the HermesWatch iOS app from a physical iPhone.

## Syntax

```bash
xcrun devicectl device uninstall app --device <UDID> <bundle-id>
# bundle id is a POSITIONAL argument — there is NO --bundle-identifier flag
```

Find the bundle id first:

```bash
xcrun devicectl device info apps --device <UDID> | grep <name>   # → "Hermes Watch   com.example.app   1.0   1"
xcrun devicectl device uninstall app --device <UDID> com.example.app   # → "App uninstalled."
```

## Pitfalls

- **`--bundle-identifier` does not exist**: `xcrun devicectl device uninstall app --device <UDID> --bundle-identifier com.x.y` errors `Error: Unknown option '--bundle-identifier'` (exit 64, usage dumped). The bundle id is positional after `--device <UDID>`.
- **Uninstalling the iOS app also removes its embedded companion Watch app** from the paired Apple Watch — watchOS companion apps don't survive iOS-app removal (they're delivered via the iOS app's embedded Watch content). The Watch may be offline/shutdown during uninstall; removal still applies when it syncs.
- Full uninstall also wipes UserDefaults + Local Network permission state (useful as the "nuclear reset" when stale host values or permissions block LAN debugging — see main SKILL.md §3).
