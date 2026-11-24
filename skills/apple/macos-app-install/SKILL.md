---
name: macos-app-install
description: "Use when installing macOS apps via App Store or DMG."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
---

# macOS App Install (App Store / DMG)

Trigger: user asks to download/install a macOS application ("帮我下载/安装 XX", "install XX on my Mac"). Covers the reliable path: Mac App Store via the `mas` CLI, plus how to verify raw DMG downloads and when NOT to trust vendor CDN links.

## Decision order (fastest → most reliable)

1. **App Store first** — if the app is on the Mac App Store, install via `mas`. Signed, auto-updates, no junk.
   - `brew install mas` (if missing)
   - `mas search <name>` → find the ADAM ID (first column)
   - `mas get <ADAM_ID>` — may require App Store login (`mas signin` prompts) and/or sudo; on this machine `sudo -S mas get <id> <<< '<sudo pass>'` worked
   - Verify: `mas list | grep <ADAM_ID>` and `mdfind -name '<name>'` or check `/Applications`
2. **Vendor official site** — only if not on App Store. Scrape the real download button URL; verify the download is actually a DMG before installing (see Verification below).
3. **App metadata before installing**: `curl -s "https://itunes.apple.com/lookup?id=<ADAM_ID>&country=cn"` returns JSON (trackName, version, fileSizeBytes, minimumOsVersion, averageUserRating). Use it to confirm you have the right app and it runs on this macOS version.

## Pitfalls (all hit in real sessions)

- **Chinese vendor CDN links (ByteDance/火山 etc.) often serve garbage to curl.** The site's "download" href points at a JS-signed `download-guidance` URL; the underlying `lf*.vlabstatic.com` CDN object returned a ~3.5 MB blob that was **zlib-compressed zeros** — not a DMG. Symptoms: small download size, `xxd -l 8` shows `78da` (zlib) instead of `koly`/`\x78\x01` (UDIF DMG). Don't burn time reverse-engineering the signature JS; jump to App Store. Even `hdiutil verify` can pass on garbage — always `xxd` the header first.
- **`file` may be broken in sandboxed/VMs** (magic.mgc version mismatch spew). Don't rely on it; use `xxd -l 8 <file>` + `hdiutil verify`.
- **macOS has no `timeout` command** (GNU coreutils). Use curl `--max-time`, python, or generous tool timeouts instead.
- **Homebrew installs hang/fail on ghcr.io in China** — `brew install node` stalled >10min downloading bottles from ghcr.io (connection CLOSED). Fix: `export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles HOMEBREW_API_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles/api HOMEBREW_NO_AUTO_UPDATE=1` then reinstall — completes in ~1 min. Diagnose: `ps aux | grep curl` + `lsof -p <curl_pid>` shows ghcr.io TCP CLOSED = mirror needed. Kill stuck brew with `pkill -f "brew install"`.
- `mas install <id>` can fail with `Failed to lookup app for ADAM ID` — `mas get <id>` is the equivalent command that worked.
- `mas` versions differ: old docs mention `mas account`; v7 has no `account` subcommand — use `mas config` and `mas search`.

## Verification

```bash
xxd -l 8 <file.dmg>          # expect koly (UDIF) or 78 01, NOT 78 da (zlib junk)
hdiutil verify <file.dmg>    # then attach/mount and copy .app to /Applications
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' /Applications/<App>.app/Contents/Info.plist
```

## Support files
- `references/capcut-jianying-install.md` — worked example: 剪映专业版 install via mas (ADAM ID 1529999940), full command transcript, CDN-garbage diagnosis.
- `references/disable-autostart-electron.md` — kill 开机自启 for Electron/Chromium apps (QuarkCloudDrive worked example): clear login items + launchd + app-internal preference.json `autoLaunchEnable`/`initedAutoLaunchEnable` (all three, or the app re-registers).
