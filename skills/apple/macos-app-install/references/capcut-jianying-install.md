# Worked example: 剪映专业版 (Jianying Pro / CapCut CN) install — 2026-08-07

Task: user asked to download 剪映 Mac 版 on macOS 27 (M2). Result: installed via Mac App Store with `mas`, version 11.1.1, app bundle `/Applications/VideoFusion-macOS.app` (bundle id `com.lemon.lvpro`).

## What failed (do not repeat)

1. `web_search` returned third-party download portals (jxdown.com, capccutapk.com) — all untrusted/pirated. Never use these for Chinese apps.
2. `web_extract` on https://www.capcut.cn/ → `Blocked: URL targets a private or internal network address` (extractor blocked; curl still works).
3. curl the site's actual download URL (`https://lf3-package.vlabstatic.com/obj/faceu-packages/installer/jianying_jianyingpro_0_1.2.14_installer.dmg`, extracted from the homepage's `download-guidance?download_url=...` href) → HTTP 200 but **3,616,214 bytes (~3.5 MB) of zlib-compressed zeros**:
   - `xxd -l 8` showed `78 da 63 60 ...` (zlib stream header), not a DMG.
   - `zlib.decompress` → 512 bytes of `\x00` — the CDN object was junk/signed-gate.
   - `hdiutil verify` claimed "checksum VALID" anyway — do NOT trust hdiutil on a blob; trust xxd.
4. Reverse-engineering the `download-guidance` JS (`download-guidance.b9c2ee03.js` is a webpack chunk; real logic in lazy chunks 947/339/481) — dead end, abandoned. The site gates downloads behind JS/signing specifically to stop curl.

## What worked

```bash
# 1. Confirm the app exists on Mac App Store (iTunes lookup API — no auth)
curl -s "https://itunes.apple.com/search?term=剪映&country=cn&entity=macSoftware" -A 'Mozilla/5.0'
# → 剪映专业版, trackId 1529999940

# 2. Install mas CLI (if missing)
brew install mas          # v7.0.0

# 3. Search to confirm ADAM ID
mas search 剪映           # → 1529999940  剪映专业版  (11.1.1)

# 4. Install (needs App Store login; sudo required on this machine)
sudo -S mas get 1529999940 <<< '<sudo password>'

# 5. Verify
mas list | grep 1529999940                    # → 1529999940  剪映专业版    (11.1.1)
mdfind -name '剪映'                            # → /Applications/VideoFusion-macOS.app
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' \
  /Applications/VideoFusion-macOS.app/Contents/Info.plist   # → 11.1.1
du -sh /Applications/VideoFusion-macOS.app    # → 3.2G
open -a /Applications/VideoFusion-macOS.app   # launch check; pgrep -fl VideoFusion
```

## Notes

- App Store bundle name ≠ marketing name: 剪映专业版 ships as `VideoFusion-macOS.app`, bundle id `com.lemon.lvpro` (check with `mdfind 'kMDItemCFBundleIdentifier == "com.lemon.lvpro"'`).
- `mas install <id>` failed with `Failed to lookup app for ADAM ID ... unexpectedEndOfInput`; `mas get <id>` is the working equivalent.
- Free apps: no payment needed, but the App Store account must be signed in (mas signin).
- App Store route is strictly better than the vendor CDN: signed app, auto-updates via App Store, no junk files.
