# Device debug: devicectl screenshot + build-artifact verification + input-binding failure

Session 2026-08-08 (HermesWatch). Three reusable techniques, in the order they were needed.

## 1. See the phone with `devicectl device capture screenshot`

The old syntax `xcrun devicectl device screenshot --device <UDID> <path>` no longer exists on
Xcode 27 (`Unknown option '--device'`; screenshot is now a subcommand of `capture`).

```bash
xcrun devicectl device capture screenshot --device <UDID> --destination /tmp/shot.png
# → "Screenshot saved to: /tmp/shot.png" + "Dimensions: 1206x2622 pixels"
```

Then load the PNG with vision_analyze (the CLI session's model reads pixels directly).
Use this whenever the user's report and the actual UI disagree — a screenshot settles it
in one round-trip instead of three questions. In this session it proved decisive: the
user swore the IP was typed, but the screenshot showed both fields empty with the
`⚠️ 请先输入 Mac 的 IP` warning visible — the binding, not the network, was the problem.

## 2. Xcode 27 Debug builds: verify strings in `*.debug.dylib`, NOT the main binary

New Debug build layout (Previews injection mode):

```
HermesWatch.app/
  HermesWatch              # ~90KB Previews stub executor (strings: __PREVIEWS_AGENT_STUB_EXECUTOR,
                           #   HermesWatch.debug.dylib, __debug_blank_executor_run_user_entry_point)
  HermesWatch.debug.dylib  # ~545KB — the REAL Swift code (all app strings live here)
```

- `file`/`otool -hv` on the stub still says a normal `MH_MAGIC_64 ARM64 EXECUTE`.
- grep for ANY app string (UI text, hard-coded IPs, old strings) in the main binary
  returns nothing — a guaranteed false FAIL in verification scripts.
- Correct check:

```bash
python3 -c "
data = open('<app>/HermesWatch.debug.dylib','rb').read()
for s in ['一键填入', '172.20.10.5', '保存并测试连接']:
    print(s, s.encode('utf-8') in data)   # utf-16 is NOT used
"
```

Also note the verification-script lesson: `strings` only dumps ASCII by default, so
Chinese text needs a raw UTF-8 byte search, not `strings`.

## 3. TextField input "lost" on device — diagnosis and defensive fix

Symptom chain: user types the Mac IP, taps "保存并测试连接", app answers
`⚠️ 请先输入 Mac 的 IP` (the empty-host guard). Screenshot confirms the field IS empty.
Earlier symptom that now makes sense: "zero packets arrive at the Mac" — if the host
never reaches the model, the request never fires.

Root cause not fully pinned (iOS/Xcode beta binding behavior), but the fix must not
depend on knowing it. Defensive pattern applied:

```swift
@State private var hostInput: String = ""   // local buffer, TextField binds HERE
@State private var tokenInput: String = ""

TextField("Mac 的 IP, 如 172.20.10.5", text: $hostInput)
    .onChange(of: hostInput) { _, new in bridge.host = new }   // live sync
// button action:
let h = hostInput.trimmingCharacters(in: .whitespaces)
guard !h.isEmpty else { statusText = "⚠️ 请先输入 Mac 的 IP"; return }
bridge.host = h; bridge.token = tokenInput; bridge.saveConfig() // explicit sync
// diagnostic line reads the buffer, so it always mirrors the field:
Text("当前地址: [\(hostInput)]\n实际连接: \(bridge.currentURL)")
```

Plus a one-tap preset button so the user never has to type at all:

```swift
Button { hostInput = "172.20.10.5"; bridge.host = hostInput } label: {
    Label("一键填入热点 IP 172.20.10.5", systemImage: "bolt.fill")
}
```

Reinstall flow: `xcodebuild -project App.xcodeproj -scheme App -destination 'platform=iOS,id=<UDID>' -allowProvisioningUpdates build` → `xcrun devicectl device install app --device <UDID> <DerivedData>/.../Debug-iphoneos/App.app` (watch for `databaseSequenceNumber` in output as install proof). `NSAllowsArbitraryLoads` was already in place; macOS Application Firewall was off — neither was the blocker this round.
