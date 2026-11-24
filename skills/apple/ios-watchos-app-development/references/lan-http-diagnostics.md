# LAN HTTP Diagnostics: iPhone "could not connect to the server"

Worked example from the HermesWatch project (2026-08-08): the iOS app on a real
iPhone reported "could not connect to the server" when tapping "test connection"
against a Mac FastAPI bridge on `http://<mac-ip>:8765`, while the same endpoint
answered fine from the Mac itself (`curl 127.0.0.1:8765` and `curl <mac-ip>:8765`
both returned HTTP 200).

## The decisive observation

The bridge server's log file mtime never advanced and no access-log line appeared
— **the request never reached the Mac**. When a server is provably listening on
`*:PORT` and the phone still can't connect, the block is client-side. Two causes
in order of likelihood:

1. **ATS (App Transport Security)**: `NSAllowsLocalNetworking: true` alone does
   NOT reliably allow plain-IP HTTP. Symptom identical to "server down". Fix in
   project.yml `info.properties`:

   ```yaml
   NSAppTransportSecurity:
     NSAllowsArbitraryLoads: true
     NSAllowsLocalNetworking: true
   ```

   Then regenerate + rebuild + reinstall (config changes do NOT hot-reload into
   an installed app).

2. **iOS 14+ Local Network privacy permission**: first LAN access must be allowed
   via system prompt. If the user dismissed/denied it, requests are silently
   dropped. Fix: Settings → Privacy & Security → Local Network → enable the app.
   A reinstall usually re-prompts. Info.plist must contain
   `NSLocalNetworkUsageDescription` or the prompt never shows properly.

## Diagnostic ladder (run top-down, stop when a step fails)

```bash
# 1. Server alive on loopback?
curl -s -m 5 http://127.0.0.1:8765/api/status -o /dev/null -w "%{http_code}\n"

# 2. Listening on ALL interfaces (*:PORT), not 127.0.0.1?
lsof -iTCP:8765 -sTCP:LISTEN

# 3. Mac's current LAN IP — does it match what the app has?
ipconfig getifaddr en0
# 172.20.10.x = Mac is tethered to the iPhone's Personal Hotspot:
#   gateway is 172.20.10.1 (the iPhone itself) → phone↔Mac routing already exists.

# 4. Did ANY request arrive from the phone? (mtime is the cheap tell)
stat -f "%Sm" -t "%H:%M:%S" server.log   # compare to current time
tail -20 server.log

# 5. Ground truth: sniff the port while the user taps "test"
sudo tcpdump -i en0 -nn 'tcp port 8765' > /tmp/tcpdump8765.log 2>&1
# run in background; any packet = the phone reached the Mac → problem is
# app-side (wrong IP/token in the app, or ATS/local-network permission).
# For USB-tethered topology (Mac on iPhone Personal Hotspot, en0 is a
# 02:00:00:00:00:00 virtual NIC) sniff ALL interfaces instead:
sudo tcpdump -i any -nn 'tcp port 8765' > /tmp/tcpdump8765.log 2>&1
# ZERO packets across both = the request never left the phone at all.
```

## When the ladder is exhausted: surface the NSURLError code in the app

If the user keeps reporting the same generic "could not connect to the server"
and steps 1–5 all pass server-side (or all show zero packets), stop guessing:
**patch the app to display the underlying error code, rebuild, reinstall, and
have the user tap "test" once more.** The code disambiguates instantly:

```swift
// BridgeClient: wrap errors with code + hint
static func describe(_ error: Error, url: String) -> String {
    let ns = error as NSError
    var s = "❌ \(error.localizedDescription)\n错误码: \(ns.code)"
    if let u = ns.userInfo[NSURLErrorFailingURLStringErrorKey] { s += "\nURL: \(u)" }
    let hints: [Int: String] = [
        -1004: "无法连接到主机 (网络/权限拦截)",
        -1009: "网络连接已断开",
        -1022: "ATS 禁止明文 HTTP (需 NSAllowsArbitraryLoads)",
        -1021: "请求被系统拦截 (本地网络权限未授权?)",
        -1003: "主机名无法解析",
        -1100: "URL 无效",
    ]
    if let h = hints[ns.code] { s += "\n提示: \(h)" }
    return s
}
// catch 块: lastError = Self.describe(error, url: baseURL + path)
```

Then show `lastError` unconditionally in the UI (red text), not only after a
successful first save. Have the user read back the 错误码 line — it settles
ATS vs permission vs URL-format in one round-trip instead of blind re-toggles.
This was the decisive escalation in the HermesWatch session (2026-08-08): every
generic retry failed; the code-bearing build turned the next tap into data.

Also remember to bump `CFBundleVersion` (or check binary mtime vs source mtime,
`stat -f '%m'`) — an unchanged bundle version makes "did the reinstall actually
take the new build?" unanswerable from `devicectl device info apps` alone.

## Epilogue: the -1004 was a stale `localhost` saved in UserDefaults

In the HermesWatch session the code-bearing build reported `错误码: -1004` with
`URL: http://locaalhost:8765/api/status` — note the host: not the Mac's LAN IP,
but a **saved host string** ("locaalhost", double-a typo; later builds showed
`localhost`). That single URL line was the whole answer, and it explains every
earlier mystery:

- **`localhost` on the iPhone = the iPhone itself.** The Mac is a different
  machine and must be reached by its LAN IP. Requests to `localhost` loop to
  the phone → server sees nothing (zero tcpdump packets) → no Local Network
  permission prompt (localhost is not LAN traffic) → generic -1004. It
  masqueraded as ATS / permission / server problems for many rounds.
- **The stale value lived in UserDefaults and survived overwrite-installs.**
  `devicectl device install app` (overwrite) keeps app data; only a full
  `devicectl device uninstall app` wipes it. The user had saved the typo once,
  edited the TextField later, but the app kept using the saved value — and the
  user reasonably insisted "I didn't type that / it's your program's bug".
- **Fixes that actually worked:**
  1. Display the value the app REALLY uses — `当前地址: [host]` + `实际连接:
     baseURL+path` (computed URL) in the UI, so the saved-vs-typed mismatch is
     visible instead of argued about.
  2. Change the UserDefaults key (`bridgeHost` → `bridgeHostV2`) — the stale
     value is orphaned, field starts empty. Add a destructive "清除已保存的配置"
     button (`clearConfig()`: reset host/token + `removeObject` both keys).
  3. Fool-proof the input: inline orange warning when
     `host.localizedCaseInsensitiveContains("localhost")` ("localhost 指 iPhone
     自己! 必须填 Mac 的局域网 IP"), placeholder = the concrete IP format
     (`Mac 的 IP, 如 172.20.10.5`).
- **Takeaway: when the user swears the app is wrong and the network/server
  checks all pass, instrument the app to SHOW the exact host + URL it uses —
  the printed URL is ground truth about where the request actually goes.**

## devicectl subcommand syntax (Xcode 27)

`devicectl device info` takes the subcommand FIRST; `--device` goes after it:

```bash
xcrun devicectl device info apps --device <UDID> | grep -i hermes
xcrun devicectl device info processes --device <UDID>
xcrun devicectl device install app --device <UDID> <path.app>
xcrun devicectl list devices          # physical vs simulated reality column
```

`device info --device X` (flag before subcommand) fails with
"Unknown option '--device'" — that's a syntax error, not a missing feature.

## After changing project.yml / Info.plist

Config changes do not apply to an already-installed app:

```bash
cd app && xcodegen generate
xcodebuild -project App.xcodeproj -scheme App \
  -destination 'platform=iOS,id=<UDID>' -allowProvisioningUpdates -quiet build
xcrun devicectl device install app --device <UDID> \
  ~/Library/Developer/Xcode/DerivedData/App-*/Build/Products/Debug-iphoneos/App.app
# Verify the SHIPPED plist (not just project.yml):
plutil -p <that app path>/Info.plist | grep -A6 NSAppTransportSecurity
```
