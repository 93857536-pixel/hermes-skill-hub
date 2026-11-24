# HermesWatch — worked example: Watch control surface for a Mac agent

Full project: `/Volumes/Programming/Projects/HermesWatch/` (git, 2 commits). Architecture and the decisions that mattered — reuse the shape for any "watch remote control" project.

## Architecture

```
Apple Watch (SwiftUI) → WCSession → iPhone app → HTTP (Bearer token) → Mac FastAPI bridge → hermes CLI
```

- Watch never talks to the Mac directly — it relays through the iPhone app. Works over cellular (Watch→iPhone) even when neither is on the Mac's LAN.
- iPhone app is a thin WCSession relay + config store (host + token in UserDefaults).
- Mac bridge (`server/bridge.py`, FastAPI on :8765) runs as a **launchd LaunchAgent** (user context — a LaunchDaemon runs children as root and Hindsight's local_embedded Postgres refuses root).

## Bridge API (reuse as-is)

| Endpoint | Purpose |
|---|---|
| GET /api/status | system (load/mem/disk/host/hermes_procs) + cron tasks + recent sessions |
| GET /api/tasks | cron list (parses `hermes cron list` text fallback) |
| GET /api/sessions | recent sessions (skips `─` decoration lines) |
| POST /api/command {"text": ...} | enqueue `hermes chat -q "<text>" -Q`, returns job_id |
| GET /api/command/{job_id} | poll: done, exit_code, result |
| WS /ws?token= | 15s heartbeat snapshot push |

All endpoints require `Authorization: Bearer <token>`; token auto-generated into `server/.token` on first start (env `HERMESWATCH_TOKEN` overrides).

## Key implementation decisions

- **Command execution is async job-based** (POST returns job_id; client polls GET). Watch UI shows ProgressView while polling every 3s — a synchronous request would hang the whole relay.
- **hermes binary resolution**: launchd env has no user PATH → probe candidates: `os.environ.get("HERMES_BIN")`, `shutil.which("hermes")`, `~/.local/bin/hermes`, `~/.hermes/hermes-agent/venv/bin/hermes`, `/opt/homebrew/bin/hermes`.
- **macOS system stats without psutil**: `sysctl -n vm.loadavg` for load; `vm_stat` for memory — parse "page size of (\d+) bytes" with regex (last token is `bytes)` not the number!), keys are `Pages free`, `Pages active`, `Pages wired down`, `Pages speculative`; `shutil.disk_usage("/")` for disk.
- **WCSession relay in Swift 6 mode**: delegate methods are `nonisolated`; hop to MainActor with `Task { @MainActor in ... }` before touching @Published state or replying.
- **xcodegen** generates the .xcodeproj from `app/project.yml` (iOS + watchOS targets; `WKCompanionAppBundleIdentifier` must equal iOS bundle id).

## E2E verification recipe

1. `xcodebuild -project app/HermesWatch.xcodeproj -scheme HermesWatch -destination 'generic/platform=iOS Simulator' build` → BUILD SUCCEEDED (compile check, no signing).
2. `launchctl print gui/$(id -u)/com.hermeswatch.bridge` → running, pid, user.
3. `curl -H "Authorization: Bearer $(cat server/.token)" http://127.0.0.1:8765/api/status` → ok + fields.
4. POST a real command, poll job until done — verify the agent's actual reply text arrives (proves the hermes CLI path, not just HTTP plumbing).
5. Auth negative test: no token / wrong token → 401.
6. **LAN reachability (loopback success ≠ phone success)**: `lsof -iTCP:8765 -sTCP:LISTEN` must show `*:8765` (0.0.0.0), not `127.0.0.1`; check `socketfilterfw --getglobalstate` (Firewall is disabled is fine); then `curl -H "Authorization: Bearer $TOK" http://$(ipconfig getifaddr en0):8765/api/status`. When the Mac is tethering to the iPhone's hotspot the LAN IP is in the `172.20.10.x` range — that's the address the phone app should use. Skip step 6 and the phone app gets "连接失败" despite everything passing on 127.0.0.1.
7. Watch device check: `xcrun xcdevice list` shows NO physical Watch even when paired — normal (see SKILL.md pitfall). Confirm delivery via `xcrun devicectl device info apps --device <iPhoneUDID> | grep <name>` (iOS app present) + user checking the Watch home screen.

## Deployment notes for this machine

- LaunchAgent plist: `server/com.hermeswatch.bridge.plist` → `~/Library/LaunchAgents/`; logs at `~/Library/Logs/hermeswatch/bridge.log` (NEVER /Volumes — EX_CONFIG 78).
- Free-Apple-ID device install: unique bundle id in project.yml, sign in Xcode, ⌘R to iPhone; Watch app installs automatically to the paired Watch.
- To install on the user's devices: iPhone 17 Pro 国行, Apple Watch S10 46mm 国行蜂窝版. Voice input via system dictation (DictationSession removed in Xcode 27 beta).
- **Project docs encoding pitfall**: a README written by an earlier session landed as UTF-16 (BOM), which made `read_file` report "Binary file - cannot display as text" and `file`/`iconv -f UTF-16` fail (`iconv` silently produced mojibake `⌠䡥牭敳...` output; `mv` over the file also failed with "set owner/group (was: 501/0): Operation not permitted" because the file's owner/group mismatch blocks atomic rename on the volume). Fix: detect encoding in Python (`data.decode('utf-8-sig')` worked for UTF-16LE-with-BOM content — `utf-8-sig` tolerates it), then rewrite the file with `write_file` (UTF-8) rather than shell redirects. If the bytes are unrecoverable mojibake, rewrite from a known-good copy of the content. Write project docs with `write_file` from the start to avoid the class of problem.
