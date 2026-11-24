# App Icons & the "Local Network list is empty" diagnostic

Worked examples from the HermesWatch project (2026-08-08).

## 1. Generating an app icon headlessly (no Photoshop/Pillow)

macOS system Python has no Pillow (`~/.local/bin/python3.11 -c "import PIL"` fails),
so generate the icon with **Swift + AppKit/CoreGraphics** instead — every macOS has
`swift` and AppKit, zero dependencies:

```bash
cd app
swift make_icon.swift AppIcon.png   # see scripts/make_app_icon.swift
sips -z 1024 1024 AppIcon.png        # NSImage lockFocus renders @2x = 2048px; downscale!
```

Key gotcha: `NSImage.lockFocus()` output is **2048x2048 even though you drew a
1024x1024 rect** (Retina backing scale). Always `sips -z 1024 1024` the result
before shipping; Xcode icon validation rejects non-1024 sources.

## 2. Wiring the icon into xcodegen (dual-target project)

Create `Assets.xcassets/AppIcon.appiconset/` in BOTH target source dirs, with the
1024 PNG + a `Contents.json`:

```json
{
  "images" : [ { "filename" : "AppIcon.png", "idiom" : "universal",
                 "platform" : "ios", "size" : "1024x1024" } ],
  "info" : { "author" : "xcode", "version" : 1 }
}
```

(watchOS variant: same JSON but `"platform" : "watchos"`.)

In `project.yml`, each target that should show the icon needs:

```yaml
settings:
  base:
    ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon
```

- The asset catalog is picked up automatically because `sources: [ios]` globs the
  whole dir — you do NOT list Assets.xcassets explicitly in project.yml.
- Verify the icon actually compiled into the build product (not just project.yml):
  `ls <DerivedData>/.../Debug-iphoneos/App.app/AppIcon*.png` and
  `Assets.car` present (a few hundred KB).
- **Editing project.yml watchOS target: do NOT drop its `info:` block.** When
  adding settings/sources to a watchOS target, xcodegen's `info:` block is what
  emits `WKApplication: true` + `WKCompanionAppBundleIdentifier`. Accidentally
  removing it (easy when restructuring) breaks the independent-watch-app build
  (see SKILL.md §3 pitfalls). Keep `info:` + `settings:` side by side.

## 3. "Local Network list is empty" — the request never fired

Symptom chain (real session): iPhone app reports "could not connect to the
server"; tcpdump on the Mac shows **zero packets**; user opens the URL in iPhone
Safari and it works; Settings → Privacy & Security → Local Network does NOT list
the app at all, and no permission prompt appears no matter how many times you
reinstall.

Read: **an app absent from the Local Network list = iOS never saw a LAN attempt
from it.** The permission prompt only fires when the app actually tries a
local-network connection. An empty list means the request was killed EARLIER —
i.e. ATS (NSAllowsArbitraryLoads missing) blocked it before the Local Network
layer. So:

1. Safari (system app, no ATS restriction) loading `http://<mac-ip>:<port>/...`
   proves the network path is fine → the block is client-side app config.
2. App missing from Local Network list + no prompt → ATS is still blocking;
   re-verify the SHIPPED Info.plist (`plutil -p <app>/Info.plist | grep -A6
   NSAppTransportSecurity`) after rebuild+reinstall — devicectl reinstall does
   NOT refresh plist changes unless the app was actually rebuilt.
3. `devicectl device uninstall app --device <UDID> <bundle-id>` (full uninstall,
   wipes UserDefaults + permission state) then `device install app` — a
   *reinstall over the top* can preserve stale permission state; uninstall is
   the stronger reset.
4. If still nothing after all that, the app may genuinely never call the URL
   (e.g. "test connection" button not wired, wrong text field bound) — check the
   app's own code path, not the OS.
