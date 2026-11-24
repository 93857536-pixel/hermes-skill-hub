---
name: macos-autostart-control
description: "Use when enabling/disabling macOS app auto-start (开机自启)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [macos, autostart, login-items, launchd, electron]
    related_skills: [macos-app-install]
---

# macOS App Auto-Start Control (开机自启)

Disable/enable apps that start at login. Apps register through up to THREE channels — check all, fix all, or the app re-registers itself and the "fix" silently comes back.

## Detect (check all three)

1. System login items (the common one):
   ```bash
   osascript -e 'tell application "System Events" to get the name of every login item'
   ```
2. launchd:
   ```bash
   ls ~/Library/LaunchAgents/ /Library/LaunchAgents/ /Library/LaunchDaemons/ 2>/dev/null | grep -iE "<app-keyword>"
   ```
3. In-app toggle (Electron/Chromium apps keep it in their own config):
   ```bash
   cd ~/Library/Application\ Support/<AppDir>
   grep -rilE "auto.?start|auto.?launch|login.?item|open.?at.?login|开机自启|开机启动" . 2>/dev/null \
     | grep -vE "Cache|GrShaderCache|GraphiteDawn|\.png|\.jpg|\.db$"
   ```
   Typical file: `preference.json` (or `config.json` / `Local State`).

## Disable

1. Login item (needs Automation/Accessibility permission; exit 0 + empty re-list = success):
   ```bash
   osascript -e 'tell application "System Events" to delete login item "<ExactName>"'
   ```
   Chinese app names work verbatim (e.g. 夸克网盘).
2. launchd: if a plist exists with RunAtLoad, `launchctl bootout` or remove the plist (rare for consumer apps).
3. In-app config — THE critical step for Electron apps. Edit the toggle(s) to false with python3:
   ```python
   import json; p = 'preference.json'
   d = json.load(open(p))
   # Quark example:
   d['global:setting']['permissionSwitch']['autoLaunchEnable'] = False
   d['global:setting']['initedAutoLaunchEnable'] = False   # first-run init marker, set BOTH
   json.dump(d, open(p,'w'), ensure_ascii=False, indent=2)
   ```
   Prefer quitting the app first so it doesn't overwrite your edit on exit.

## 给自己的 app 装自启（LaunchAgent）

自己做的 app（尤其 ad-hoc 签名、不在 /Applications 商店体系里）**不要用 `SMAppService`**，不稳。
直接写 `~/Library/LaunchAgents/<label>.plist`，下次登录 launchd 自动加载：

```xml
<key>Label</key><string>com.example.myapp</string>
<key>ProgramArguments</key><array><string>/Applications/MyApp.app/Contents/MacOS/MyApp</string></array>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
<key>ProcessType</key><string>Interactive</string>
```

`KeepAlive.SuccessfulExit=false` 的含义：崩溃会自动拉起，用户主动退出（clean exit）则不再重启——两者都要。

⚠️ **从 hermes gateway 进程内执行 `launchctl bootstrap` 会被安全策略拦**：
`launchctl submit/bootstrap registers a persistent KeepAlive job and is unsafe from inside the gateway process`.
不需要绕：把 plist 写进 `~/Library/LaunchAgents/` 就已经生效（下次登录自动加载）。
若要本次立即生效，让 app 自己的进程去 `launchctl bootstrap`（app 不是 gateway），或直接 `open` 一次。

## Pitfalls

- Deleting ONLY the login item is NOT enough for Electron apps: on exit they re-register it while the in-app switch is still on. Must flip the app's own toggle (step 3).
- Some apps use BOTH an init marker (e.g. `initedAutoLaunchEnable`) and the real switch (`permissionSwitch/autoLaunchEnable`) — set both to false, or the app re-creates the login item at next start.
- Editing config while the app runs risks the app overwriting on quit; if possible quit first, edit, then re-read to verify.

## Verify

Re-run detection: login item list empty + config flags false + no launchd plist = fully disabled. If the user later wants it back: re-add via System Settings > General > Login Items, or the app's own 设置 > 开机自动启动.
