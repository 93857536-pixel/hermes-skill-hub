---
name: ios-watchos-app-development
description: "Use when building iOS/watchOS SwiftUI apps with Xcode."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [ios, watchos, swiftui, xcode, xcodegen, wcsession, apple-watch]
    related_skills: [macos-launchd-services]
---

# iOS/watchOS App Development with Xcode

Build SwiftUI apps for iPhone + Apple Watch: generate the Xcode project with xcodegen, verify compilation headlessly with xcodebuild, wire Watch↔iPhone communication via WCSession, and avoid SDK/API traps (Xcode 27 beta quirks, method-shadowing bugs).

For the live "watch the simulator refresh as code is edited" loop (Device Hub window + auto build/install/launch watcher + vision self-review), see the `simulator-live-watch` skill.

## 1. Project generation with xcodegen (no manual .pbxproj)

xcodegen (brew install xcodegen) turns a `project.yml` into `HermesWatch.xcodeproj`. Do NOT hand-edit project.pbxproj.

Dual-target (iOS + watchOS) `project.yml` essentials:

```yaml
name: MyApp
options:
  bundleIdPrefix: com.yourname
  deploymentTarget: { iOS: "17.0", watchOS: "10.0" }
targets:
  iOSApp:
    type: application
    platform: iOS
    sources: [ios]
    info:
      path: ios/Info.plist
      properties:
        UILaunchScreen: {}
        NSLocalNetworkUsageDescription: 需要访问局域网服务
        NSAppTransportSecurity:
          NSAllowsArbitraryLoads: true
          NSAllowsLocalNetworking: true
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.yourname.iosapp
  WatchApp:
    type: application
    platform: watchOS
    sources: [watch]
    info:
      path: watch/Info.plist
      properties:
        WKCompanionAppBundleIdentifier: com.yourname.iosapp
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.yourname.iosapp.watchapp
        WKWatchAppIndependent: YES
```

- `WKCompanionAppBundleIdentifier` MUST equal the iOS app's bundle id — without it the Watch app can't WCSession to the iPhone app.
- Then: `xcodegen generate` → `xcodebuild -project MyApp.xcodeproj -scheme MyApp -destination 'generic/platform=iOS Simulator' build` (no signing needed for simulator).
- Filter build output with `grep -E "error:|BUILD"` — full log is noise.

## 2. Watch ↔ iPhone ↔ remote: WCSession relay pattern

Watch apps can't reach arbitrary hosts reliably (cellular, no per-app networking in all cases). Standard architecture: **Watch → WCSession → iPhone app → HTTP/WebSocket → remote service**.

- iPhone side: `WCSession.default.delegate = self; WCSession.default.activate()`. Handle `session(_:didReceiveMessage:replyHandler:)` and forward to your HTTP client; reply asynchronously via `replyHandler`.
- Delegate methods are `nonisolated` in Swift 6 mode — hop to main actor inside: `Task { @MainActor in ... replyHandler(reply) }`.
- Watch side: `sendMessage(_:replyHandler:errorHandler:)` wrapped in `withCheckedContinuation` → `async` helper. Check `WCSession.default.isReachable` first; return a friendly "iPhone 未连接" error when false.
- iPhone app must be opened once after install to activate the session before Watch can reach it.

## 3. Pitfalls that cost real debugging time

- **Standalone watchOS app (no WatchKit Extension) MUST set `WKApplication: true` — NOT `WKWatchKitApp: true`** in the watch target's Info.plist. Setting `WKWatchKitApp: true` makes the build fail at the ValidateEmbeddedBinary stage with "WatchKit App doesn't contain any WatchKit Extensions" (legacy validation expects an extension). Omitting both keys makes `devicectl install` fail with "does not have a WKWatchKitApp or WKApplication key set to true". Rule of thumb: extension-less independent app → `WKApplication: true`.
- **Embed the watch app into the iOS app** so it reaches the paired Watch: in `project.yml`, iOS target gets `dependencies: [- target: WatchApp, embed: true]` → xcodegen emits an "Embed Watch Content" copy phase placing the watch app at `<iOS.app>/Watch/`. Without embed, running/installing the iOS app never delivers the Watch app.
- **Never `devicectl install` a watchOS .app straight onto the iPhone** — errors with `DeviceFamilyNotSupported (MIInstallerErrorDomain error 10)`. Install the iOS .app (which embeds the Watch app); iPhone syncs it to the paired Apple Watch within minutes.
- Verify embed: `ls <iOS.app>/Watch/` contains `*WatchApp.app`; check the key with `/usr/libexec/PlistBuddy -c 'Print :WKApplication' <watch.app>/Info.plist`.
- **Method-name shadowing in WCSessionDelegate**: inside `session(_:didReceiveMessage:replyHandler:defaultReplyHandler:)`, calling the other overload as `session(session, didReceiveMessage:...)` fails with "cannot call value of non-function type 'WCSession'" — the parameter named `session` shadows the method. Fix: `self.session(session, didReceiveMessage:...)`.
- **`@ObservedObject(wrappedValue:)` for singletons**: `@ObservedObject private var bridge: BridgeClient` with `init() { _bridge = ObservedObject(wrappedValue: WatchRelay.shared.bridge) }` — gives you `$bridge.host` bindings into a shared instance (a `let` property can't be bound directly).
- **SwiftUI `foregroundStyle(cond ? .secondary : .red)` fails to compile** — the ternary mixes `HierarchicalShapeStyle` and `Color`, and Swift can't unify them ("static property 'red' requires the types 'HierarchicalShapeStyle' and 'Color' be equivalent"). Fix: qualify both sides `Color.secondary : Color.red`, or branch instead of a ternary.
- **Xcode 27 beta removed watchOS dictation APIs**: `DictationSession`, `@Environment(\\.dictation)` and the Speech framework are GONE from the watchOS SDK (see `references/xcode27-watchos-sdk-quirks.md`). Voice input = TextField + `@FocusState` to pop the system dictation keyboard.
- **`textSelection(.enabled)` is unavailable on watchOS** — remove for Watch targets.
- **The paired Apple Watch never appears in `xcrun xcdevice list` / Xcode's Devices window — that is NORMAL, not a setup failure.** A standalone watchOS app is delivered to the Watch by the *iPhone* (embedded-watch-content sync), not by direct deployment from Xcode. Do NOT burn time opening Devices & Simulators, hunting menus, or trying to make Xcode "see" the Watch (a past session lost ~30 min here). Verify delivery instead: (1) iOS .app installed on the iPhone, (2) watch app embedded (`ls <iOS.app>/Watch/`), (3) user opens the iPhone app once (activates WCSession). The Watch icon appears within minutes; confirm on the Watch's home screen, not in Xcode. **But if the Watch shows "无法验证 App 完整性 / Unable to Verify App Integrity" instead of installing, that's §4's free-account watchOS restriction — not a delivery problem.**
- **Xcode 27's "Devices and Simulators" menu item is gone** — ⌘⇧2 opens the new Device Hub, which is a **standalone app** at `/Applications/Xcode-beta.app/Contents/Applications/DeviceHub.app` (bundle `com.apple.dt.Devices`, launch with `open -a "<path>"`); driving Xcode's menu bar via `System Events` is fragile (localized/fuzzy menu names → `-1728` errors). Use `xcrun devicectl` / `xcrun xcdevice list` instead of GUI automation. Device Hub's sidebar lists only the iPhone and simulators — the paired Watch never appears there either (see §4, delivery goes through the iPhone).
- **Xcode 27 beta 本机无 `Simulator.app` GUI**(2026-08-30 实测): `open -a Simulator` 与 `find /Applications/Xcode-beta.app -name Simulator.app` 都找不到(只剩 `Contents/Applications/DeviceHub.app`), 所以无法弹出模拟器窗口用 computer_use 点 Tab/UI。`xcrun simctl` 仍可完全无头使用: `simctl boot <UDID>` → `simctl bootstatus <UDID> -b`(等启动完成) → `simctl install <UDID> <App.app>` → `simctl launch <UDID> <bundle-id>` → `simctl io <UDID> screenshot /tmp/x.png`。且 `simctl` **没有** `tap`/`touch`/`input` 子命令(`simctl help` 只有 `ui`=读写外观选项、`io`=screenshot/recordVideo/enumerate/poll), 所以无头也切不了 Tab。务实做法: 启动 App → 截图首 Tab → 确认 TabView 栏(所有 Tab 标签)渲染在截图里; 其余 Tab 的数据用 `curl -H "x-diag-token:..."` 直接打后端接口核对(Store 在 `.task { loadAll() }` 本就一次拉全各数据源)。
- **iPhone "could not connect to the server" for a LAN HTTP service: `NSAllowsLocalNetworking: true` alone does NOT reliably permit plain-IP HTTP** (e.g. `http://192.168.1.100:8765`). On many iOS builds ATS still blocks the request and the server never sees a connection. Fix: also set `NSAllowsArbitraryLoads: true` in `NSAppTransportSecurity` (fine for a dev/LAN tool). This is the #1 cause of an iOS app that works in the simulator but fails on the device.
- **iOS 14+ Local Network privacy permission is a second client-side blocker**: first LAN access triggers a system prompt ("…would like to find and connect to devices on your local network"). If denied (or never prompted), requests are silently dropped → same "could not connect to the server". User must allow in Settings → Privacy & Security → Local Network (reinstall usually re-prompts). Requires `NSLocalNetworkUsageDescription` in Info.plist (or the prompt is a crash/denial).
- **App MISSING from Settings → Privacy & Security → Local Network (empty list) + no prompt = the request never fired, i.e. ATS still blocking** — not a permission-state problem you can fix by toggling. The prompt only appears when the app actually attempts a LAN connection. Decisive checks: (a) open the URL in iPhone Safari — works ⇒ network path fine, block is app-side config; (b) re-verify the SHIPPED plist (`plutil -p <app>/Info.plist | grep -A6 NSAppTransportSecurity`) — devicectl reinstall over the top does NOT refresh plist changes; (c) full `devicectl device uninstall app` (wipes UserDefaults + permission state) then reinstall, stronger than overwrite-install. See `references/app-icons-and-local-network.md` §3.
- **NEVER put `localhost`/`127.0.0.1` in the phone-side host field — on the iPhone it means the iPhone itself.** The Mac is a different device; it must be addressed by its LAN IP (`ipconfig getifaddr en0` on the Mac). A `localhost` host makes the request loop to the phone, so the server never sees it: zero tcpdump packets, no Local Network permission prompt (localhost isn't LAN traffic), generic `-1004 could not connect`. This masquerades as ATS/permission/server problems for a long time.
- **A stale saved host value in UserDefaults survives `devicectl device install` (overwrite) — reinstalling does NOT refresh it.** A previous save of a typo (`locaalhost` double-a) or `localhost` keeps winning even after the user edits the TextField, and the user will insist "I didn't type that / it's your program's bug". Root-cause it by displaying the value the app actually uses: show `当前地址: [host原文]` + `实际连接: baseURL+path` (the built URL) in the UI. If the URL line reads `http://localhost:8765/...`, that string came from saved config, not the program. Fixes: (a) change the UserDefaults key (`bridgeHost` → `bridgeHostV2`) so stale values are orphaned, (b) add a destructive "清除已保存的配置" button calling `clearConfig()` (reset host/token + `removeObject` both keys), (c) full uninstall+reinstall. Fool-proof the field too: inline warning when `host.localizedCaseInsensitiveContains("localhost")` ("localhost 指 iPhone 自己! 必须填 Mac 的局域网 IP") and placeholder = the concrete expected value (`Mac 的 IP, 如 172.20.10.5`).
- **URLSessionWebSocketTask + 服务器一次性鉴权 token:「连接成功(101)→ 立即断开 → 无限重连」= token 没带上**(2026-08-18 实测,某聊天App iOS):服务器对无 token 的 WS 连接**握手成功(101)后马上关闭连接**,客户端表现为 `statusText = "连接断开,正在重连…"` 死循环,非常迷惑。排障顺序:① 先用 curl 验证后端 WS 是否真通(`curl --http1.1 -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" "wss://host/ws?token=..."` → 101 即通;**必须 --http1.1**,HTTP/2 下 Upgrade 无效会得假 404);② 后端通就查客户端拼 URL 的代码——注释写着带 token 但实现忘了拼 query 是常见 bug;③ 一次性 token 意味着**断线重连也必须重新申请**(旧 token 已作废),自动重连若复用旧 URL 会永远失败——需要在 `.reconnecting` 状态回调里重新拉 token 并 `updatePendingUrl`(WebSocketClient 暴露 `func updatePendingUrl(_ url: URL)` 供上层刷新待重连 URL)。\n- **Xcode 27 `devicectl` screenshot syntax changed**: `xcrun devicectl device screenshot --device <UDID> <path>` is GONE (`Unknown option '--device'`). Current form: `xcrun devicectl device capture screenshot --device <UDID> --destination /tmp/shot.png` → prints `Screenshot saved to` + `Dimensions: WxH pixels`. Then inspect with vision_analyze. This is the #1 way to see what the user's phone actually shows instead of asking back and forth.
- **Xcode 27 Debug builds: the main binary is a Previews stub — verify strings in `*.debug.dylib`**: `<App>.app/<App>` is a ~90KB stub executor (`strings` shows `__PREVIEWS_AGENT_STUB_EXECUTOR`, `HermesWatch.debug.dylib`, `__debug_blank_executor_run_user_entry_point`…); the real Swift code lives in `<App>.app/<App>.debug.dylib` (hundreds of KB). Grepping the main binary for app strings (UI text, IPs) returns NOTHING — even strings from the previous build — producing a classic false FAIL in verification scripts. Verify against the .debug.dylib instead: `python3 -c "print(b'一键填入'.encode('utf-8') in open('<app>/X.debug.dylib','rb').read())"`.
- **User insists "I typed the IP" but the button guard says it's empty — screenshot the device, don't argue**: input binding can silently fail on device (iOS/Xcode beta); the empty field + `请先输入` warning is proof the value never reached the model — and if the host never reaches the model the request never fires (explains phantom "zero packets at the server" symptoms). Ground truth with `devicectl device capture screenshot`, then apply a defensive fix that works regardless of binding health: bind TextField/SecureField to local `@State` buffers (`hostInput`/`tokenInput`), sync to the shared `@Published` object via `.onChange(of:)` AND explicitly in the button action (`bridge.host = h; bridge.token = tokenInput`), render the diagnostic line from the local buffer (`当前地址: [\(hostInput)]`), and add a one-tap preset button (e.g. `一键填入热点 IP 172.20.10.5`) so the user never has to type. Full case: `references/device-debug-and-build-verification.md`.
- **Diagnose "iPhone can't reach Mac service" in this order** (see `references/lan-http-diagnostics.md`): (1) server alive locally `curl 127.0.0.1:PORT/api/...`; (2) `lsof -iTCP:PORT -sTCP:LISTEN` shows `*:PORT` (all interfaces), not `127.0.0.1`; (3) Mac's current IP matches what the app has (`ipconfig getifaddr en0` — note `172.20.10.x` means the Mac is tethered to the iPhone's Personal Hotspot, so phone↔Mac routing already exists); (4) **check the server's access log / log-file mtime — if no request arrived, the block is client-side (ATS, Local Network permission, or a localhost host value), not the server**; (5) ground truth with `sudo tcpdump -i en0 -nn 'tcp port PORT'` run in background while the user taps "test" — any SYN means the packet reached the Mac; (6) once the error code is surfaced, READ THE `URL:` LINE in the error — a `localhost` there is the whole story.
- **SwiftUI `.refreshable` 必须直接挂在 List/ScrollView 上,挂 Group/NavigationStack 上静默不生效**(2026-08-30 实测,WeChatExporterMonitor 用户报"下拉刷新时间不变"): `Group { ... }.refreshable { ... }` 且 Group 内是 ScrollView 时,下拉手势**根本不触发**回调——用户看到"更新于"时间和数据完全不变,但 30s 定时自动刷新(`.task { await store.autoRefreshStatus() }` 的 Task.sleep 循环)照常工作,所以"自动变、手拉不变"是 refreshable 挂错容器的特征症状。修复: 把 `.refreshable` 移到 `content(_:)` 里的 `ScrollView { ... }.refreshable { await store.loadAll() }`(iOS 16+ ScrollView 原生支持下拉);List 场景挂 Group 上通常能透传,ScrollView 场景必挂本体。验证: 静态断言 `.refreshable` 在 content() 函数内且位于 `ScrollView {` 之后、body 的 Group 上无 `.refreshable`;运行验证用截图对比"更新于"时间戳在 30s 间隔后变化(证明自动刷新链路通)。
- **`devicectl device install` 瞬态错误 1005/0x3ED 与 3002/0xBBA**(2026-08-30 实测): `Could not obtain access to one or more requested file system resources because CoreDevice was unable to create bookmark data` — 多为设备刚解锁/仍在同步时出现,非代码问题。对策: 等待 30-60s 后重试(期间确认 `devicectl list devices` 仍显示 available);若持续失败,让用户重插数据线或重启 iPhone。已锁屏则是 error 4016(见上条),要先解锁。
- macOS system python3 is 3.9.x — `str | None` annotations crash. For the companion Python server use a 3.11+ venv (`~/.local/bin/python3.11` on this Mac).
- `sudo xcode-select -s /Applications/Xcode-beta.app` to activate full Xcode; CommandLineTools alone cannot build watchOS apps.
- **App icon added but Dock/Finder still shows the generic icon — check LaunchServices, not the bundle**: after wiring an `.icns` (or Assets catalog) and rebuilding an app *in place*, the OS can keep showing the old generic icon because LaunchServices holds a STALE registration pointing at a **deleted build path** (e.g. an earlier `SYMROOT=...` product that was later cleaned while the real app lives at `<DerivedData>/Build/Products/Release/...`). Fix: `lsregister -u <stale-path>` then `lsregister -f <real-path>` (`/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister`), then `killall Dock` to force the icon-cache reload. Verify with `screencapture -x -R x,y,w,h` of the Dock region + vision_analyze (`qlmanage -t` icon preview can hang; the sandbox `file` command's libmagic may be broken — skip both). **Do NOT verify via the window title-bar icon**: AppKit shows that only when the window has `representedURL` set, so its absence tells you nothing about the Dock icon.
- **Porting AppKit view code to iOS**: `NSViewRepresentable` → `UIViewRepresentable` (`makeNSView`→`makeUIView`, `updateNSView`→`updateUIView`); a copy-paste port fails with `cannot find type 'NSViewRepresentable' in scope`.
- **Xcode 27 默认 Swift 6 模式: LLM 生成的 SwiftUI 应用代码务必显式 `SWIFT_VERSION: 5.9`**(project.yml 的 settings.base), 否则 strict concurrency / actor isolation 报错成堆且难修。生成型 macOS/iOS 应用通用配方: `SWIFT_VERSION 5.9` + `MACOSX_DEPLOYMENT_TARGET 13.0` + 零第三方依赖 + `CODE_SIGN_IDENTITY "-"`(adhoc 免证书本机构建), 一次编译通过率最高。
- **Swift 6 语言模式(规格强制 `SWIFT_VERSION: 6.0` 时)的三个高频报错与修法**(2026-09-05 实测,DeviceToolbox 从零搭 UI 层):
  - `extension OperatingSystemVersion: @retroactive Comparable` 只实现 `<` 没实现 `==` → error "extension outside of file declaring struct 'OperatingSystemVersion' prevents automatic synthesis of '==' for protocol 'Equatable'"。Swift 6 不再允许从声明类型之外的文件自动合成 `==`;修法:在该 extension 内显式补 `public static func ==`。
  - `@MainActor` class 的 `static let defaultHosts` 被 nonisolated 默认参数引用(`func f(hosts: [String] = Self.defaultHosts)`)→ Swift 6 报 error "main actor-isolated static property can not be referenced from a nonisolated context"。修法:标 `nonisolated static let`(值类型是 Sendable 即可)。
  - 只读锚点/第三方模型类型只遵循 `Equatable` 没遵循 `Hashable` 时,不能用 `NavigationLink(value:)` / `.navigationDestination(for:)`(报 "requires that 'X' conform to 'Hashable'")。修法:改用 destination-based `NavigationLink { Dest() } label: { ... }`。
  - 对非 throws 的 async 方法用 `try await` 只是 warning(不阻塞编译),但 `async let` 并发写法规避该情形即可——直接顺序 `await` 最省事。
- **`xcodegen` snapshots `sources: [dir]` at generate time** — after adding NEW files (`.swift`, resources, JS) to a target folder you MUST re-run `xcodegen generate`, or the build fails with `cannot find 'X' in scope` for the new types while the file sits right there on disk. The stale pbxproj simply never referenced it.
- **Xcode 27 beta CryptoKit P-256 raw 格式 = 64B(x||y,无 0x04 前缀)**:`P256.KeyAgreement.PublicKey.rawRepresentation` 返回 64 字节;`PublicKey(rawRepresentation:)` **只接受 64B,传 65B(SEC1 带 0x04)抛 incorrectParameterSize**。与 WebCrypto 相反(WebCrypto 要求 65B 带前缀)——跨端互操作时以两端实测为准,别照文档假设。私钥 raw 仍是 32B。
- **`Data.insert(_:at: 0)` 在 Swift 6.4 -O 编译下崩溃/产生错误数据**(beta 工具链 bug):`var d = x; d.insert(0x04, at: 0)` 曾导致 CryptoKit import 失败与 interpreter 崩溃。改用 `Data([0x04]) + d` 拼接,一次通过。
- **swiftc 多文件 CLI harness:顶层语句只能在名为 `main.swift` 的文件里**;入口文件叫别的名字(如 verify.swift)报 "statements are not allowed at the top level"。做法:`cp verify.swift /tmp/main.swift` 再编译。
- **SwiftUI `Section("标题") { } footer: { }`(标题+footer 组合初始化器)不存在** —— 编译器报 "missing argument label 'content:'" 级联错误。改为 `Section { } header: { Text("标题") } footer: { }`。
- **Swift: 换行后行首的运算符(`+`/`&&`/`||` 等)会被当作*前缀*运算符, 不是上一行的续行** — 例如 `row("版本", [...].joined(separator: " (build "))` 换行后另起一行接 `    + (cond ? "" : ")")` 会报 `Consecutive statements on a line must be separated by ';'` + `Expected expression`。Swift 没有"行首运算符续行"语法(和某些语言不同)。修法: 把整段表达式提成局部变量/计算属性, 或把运算符留在上一行行尾。
- **CryptoKit 类型(SymmetricKey 等)用在非 Crypto 文件时必须显式 `import CryptoKit`**:模型/VM 文件里持有 `SymmetricKey` 属性却只 import Foundation → "cannot find type 'SymmetricKey' in scope"。
- **WKWebView login sessions do NOT survive a hard process kill** (pkill/SIGKILL): WebKit flushes cookies/localStorage to disk on graceful termination, so a killed app boots back to the login page even though `websiteDataStore = .default()` is configured. Warn users to quit normally, and don't blame the code. Data inspection gotchas: WebsiteData lives deep (`~/Library/WebKit/<bundle-id>/WebsiteData/Default/<hash>/<hash>/LocalStorage/localstorage.sqlite3` — a `maxdepth 2` find misses it), localStorage values are UTF-16LE (`f\0a\0l\0s\0e\0`), and session cookies never appear as a BinaryCookies file. In-app API-capture pattern (login-state polling + XHR/fetch hook injected via WKUserScript): `references/wkwebview-session-and-api-hook.md`.
- **Embedding whisper.cpp into an app** (audio→text for listening-type tasks): the CLI does NOT auto-download models and its default `-m` is the cwd-relative `models/ggml-base.en.bin`, so it fails when launched from Finder/Dock; pass `-m ~/.cache/whisper-cpp/ggml-base.bin` explicitly, and it cannot decode AIFF (use `afconvert -f WAVE -d LEI16@16000 -c 1 in.aiff out.wav` first). Full recipe: `references/whisper-cpp-cli.md`.
- **USER PREFERENCE — automation/auto-answering companion apps: build native UI + direct API, NEVER a WebView shell.** This user explicitly rejected an embedded-page app ("为什么又是这种嵌入式的网页，我要的是我用天学网的原生app") when the real blocker was iOS sandbox (a third-party app cannot read/control another app's UI — no Android-style accessibility takeover). The correct shape: 100% native SwiftUI (login form, lists, controls) that calls the service's backend API directly; tasks completed via API show as done inside the official app too (same backend). Explain the sandbox limitation honestly, then deliver the native+API version. Only fall back to an embedded official login page if anti-bot (e.g. 阿里云盾 captcha) blocks pure-API login — and first try reversing the login API.
- **SPA front-end static API reversing — find a site's backend endpoints without a login** (class-level technique, worked TianXue/up366 example in `references/spa-api-reversing.md`): (1) home HTML lists webpack JS entries + often a `zuulapis.js`-style API-gateway domain list; (2) `runtime~index.*.js` embeds the webpack5 chunk map (`f(e)` returns `"js/"+chunkId+"."+hash+".js"`) — extract all id:hash pairs, batch-download every chunk; (3) a domain-config module (up366's `784f`) maps property letters → API domains via `var x=function(){return t("https")+":"+t("//xxx-api.up366.cn")}` + `n.d(e,"LETTER",(function(){return var}))`; (4) extract endpoints with the `VAR["LETTER"]+"/path"` pattern → letter→domain+path = full URL; (5) login params live in the login-page chunk — grep `mobile`/`verifyCode` request-body construction; (6) probe reachability with an empty-body curl → `param_missing` means the endpoint EXISTS (but NOT that it's captcha-free — see reference §6: switch to form-urlencoded to make the error name the required fields, e.g. up366's send_v2 needs `ut`/`picCode` slider token); (7) when web login is captcha-blocked, capture the official mobile app's real traffic with mitmproxy (reference §9) — never fight the slider headless.

- **用户要把第三方 iOS/GitHub 项目的功能"全部搬"到自家 app 时,先做三档拆解报告再动手**(2026-09-05 实测 3105 案例,完整方法在 `references/porting-third-party-app-triage.md`): ① 先查 LICENSE(逐行复制 → GPL 传染整个工程);② 区分能力地基(exploit/私有框架/沙盒逃逸 = 功能的真正来源)与上层 UI/逻辑——**无 exploit 时"浏览任意 app 容器"类功能在 iOS 上数学上不可能 1:1**,要先向用户摆明沙盒硬边界;③ 依赖指纹 grep(import 全景 + NSClassFromString/respondsToSelector/dlopen + MobileContainerManager/LSApplicationWorkspace + krw_/vnode_/sandbox_escape)把源码切成[可直接学/须重写/不可搬]三档并估工时;④ 警惕作者藏的**混淆归因/启动校验水印**(自异或字节解出作者 URL),复制会把作者校验逻辑带进自家 app;⑤ 干净移植靠磁盘规格(文件归属表+契约签名+双写禁令)并行委派, 见 `references/porting-third-party-app-triage.md` 末节与 large-codegen-delegation skill。
- **Metal Toolchain 缺失: 含 .metal shader 的工程全量构建报 `cannot execute tool 'metal' due to missing Metal Toolchain`**(2026-09-25 实测, DeviceToolbox 新建 DerivedData 全量重编触发): 本机 Toolchains 目录只有 XcodeDefault。修法零代理: `xcodebuild -downloadComponent MetalToolchain`(Apple CDN 直连, 国内可下载; 装完即用无需重启 Xcode), 验证 `xcrun --toolchain MetalToolchain metal --version` 输出 `Apple metal version ...` 即成。已有热缓存 DerivedData 的增量构建不碰 metal 重编, 所以老缓存目录能一直过——别误以为没事。
- **模拟器里 Apple 系统守护进程(如 PosterBoard 壁纸服务)崩溃循环: 反复弹崩溃报告对话框, 与你的 App 无关**(2026-09-25 实测): 信号 = 报告里 Process 是 `launchd_sim` 拉起的系统守护进程 + parent chain 在模拟器 coalition 下 + 间隔 10s 级密集重复 + 栈全在系统框架断言(SIGTRAP)。止血配方: 停监听循环 → `simctl shutdown` → `rm -rf` 数据卷 `.../Application Support/com.apple.PosterKit`(不够再清 `PRBPosterExtensionDataStore` SQLite 仓库 + Unity Poster 缓存)→ `simctl boot` → 验证 60s 无新报告 + `simctl spawn $SIM launchctl list` 里该进程退出码 0。详情: `references/simulator-system-daemon-crash-loop.md`。
- **USER PREFERENCE — "边写代码边看模拟器画面"要真自动, 拒绝手动三连**(2026-09-25 用户明确纠正: 给"改完手动 构建→安装→启动"方案时回"可是这样子弄的话就不能实时更新和显示画面了啊"): 此类需求默认交付**后台监听循环**——源码一落盘 2-4s 自动增量编译+安装+重启, Device Hub 窗口持续显示, 用户全程不手动刷。现成配方: `scripts/sim-live-watch.sh`(macOS 自带 find -newer 2s 轮询, 零依赖——fswatch/brew 都装不了也能跑; 失败不更新 marker、10s 后自愈重试) + `open -a DeviceHub.app` 常显 + `xcrun simctl io <UDID> screenshot` 喂 vision_analyze 自审。完整流程见 `references/simulator-live-watch.md`。向用户说清上限: 模拟器无官方热更新, 刷新粒度=增量构建时长(秒级), 非敲字毫秒级。

## 4. Signing & device deployment (free Apple ID, fully CLI)

- **⚠️ Ad Hoc(CODE_SIGN_IDENTITY "-")只适用于模拟器构建,真机构建直接报错**:`error: Ad Hoc code signing is not allowed with SDK 'iOS 27.0'`(2026-08-30 实测)。生成型 App 的通用配方 `CODE_SIGN_IDENTITY "-"`(§3)是模拟器验证用的;要装真机必须把 project.yml 改为 `CODE_SIGN_STYLE: Automatic` + `DEVELOPMENT_TEAM`(不要留 CODE_SIGN_IDENTITY),然后 `xcodegen generate` 重新生成 pbxproj,再 `xcodebuild -destination 'platform=iOS,id=<UDID>' -allowProvisioningUpdates build`。注意 xcodegen 重新 generate 会改 pbxproj 的 `ProvisioningStyle` 和 `CODE_SIGN_STYLE`,记得一并提交。
- **⚠️ FREE Apple ID CANNOT deploy watchOS apps to a real Apple Watch — paid Apple Developer Program ($99/yr) is mandatory.** Symptom: iOS app installs fine on the iPhone, but the Watch sync shows "无法验证 App 完整性" / "Unable to Verify App Integrity". Free-account profile fingerprint (inspect `<app>/embedded.mobileprovision` with `security cms -D -i <app>/embedded.mobileprovision`): ExpirationDate ~7 days out, `ProvisionedDevices` lists only the iPhone (1 entry), Name = "iOS Team Provisioning Profile", TeamName ends with "(Personal Team)", no `ProvisionsAllDevices`. Xcode provisions only the iPhone; the Watch rejects the binary because its signing covers no watch device. NOT a code bug, NOT fixable by re-signing, NOT solved by registering the watch UDID — Apple requires paid membership for watchOS device deployment. After the user enrolls: Xcode → Settings → Accounts (re-login same Apple ID) → rebuild with `-allowProvisioningUpdates` → `devicectl device install app` on the iPhone → iPhone auto-syncs the embedded Watch app to the paired Watch.
- **Team ID without GUI**: `defaults read com.apple.dt.Xcode IDEProvisioningTeamByIdentifier` → find `teamID` (this Mac: `4B7F8BR8R4`, "MH L (Personal Team)"). Put it in project.yml: `settings.base.DEVELOPMENT_TEAM: "4B7F8BR8R4"` + `CODE_SIGN_STYLE: Automatic`, then `xcodegen generate`.
- **⚠️ 钥匙串有证书 ≠ Xcode 已登录**: `security find-identity -v -p codesigning` 显示的 "Apple Development: <email>" 可能是**历史遗留**(过期 CSSMERR_TP_CERT_REVOKED / 吊销 / 来自别的 Apple ID),不能当账号已登录的证据。判断是否登录:① `defaults read com.apple.dt.Xcode IDEProvisioningTeamByIdentifier` 的 key(账号 UUID)在登录后**会变化**;② 登录成功的缓存文件在 `~/Library/Group Containers/group.com.apple.dt.Xcode.SecureSettingsContainer/`(Xcode 27 账号存储区,空 = 未登录);③ xcodebuild 报 `No Account for Team "X"` / `No profiles for '<bundle>'` = 未登录或 team 不匹配。登录必须用户亲手完成(Apple ID 密码 + 双重验证,agent 无法代劳);agent 只负责 `open -a /Applications/Xcode-beta.app` 打开 Xcode 并给出操作步骤,等用户确认后再构建。
- **⚠️ team ID 不匹配陷阱**(2026-08-18 实测):钥匙串证书上的 team(如 Q2WQZFFT4A)≠ 当前登录账号的 Personal Team(如 4B7F8BR8R4)。project.yml 的 `DEVELOPMENT_TEAM` 必须以 `defaults read com.apple.dt.Xcode IDEProvisioningTeamByIdentifier` 里的 `teamID` 为准,不能用证书里的 team,否则报 `No Account for Team`。登录完成后先核对,不一致就改 project.yml → `xcodegen generate` 重建 → 验证 `grep 'DEVELOPMENT_TEAM' <xcodeproj>/project.pbxproj` 只剩新值。
- 签名成功的日志特征(以此判断而非猜测):`Signing Identity: "Apple Development: <email> (...)"` + `Provisioning Profile: "iOS Team Provisioning Profile: <bundle>"` + `** BUILD SUCCEEDED **`;产物验证 `codesign -dv <App>.app` 显示 `TeamIdentifier=<teamID>`。
- Build for device: `xcodebuild -project X.xcodeproj -scheme X -destination 'platform=iOS,id=<UDID>' -allowProvisioningUpdates build` → expect `Signing Identity: "Apple Development: <email> (...)"` in the log.
- Install + launch headlessly (no Xcode GUI needed):
  ```bash
  xcrun devicectl device install app --device <UDID> <path/to/iOSApp.app>
  xcrun devicectl device process launch --device <UDID> <bundle-id>
  xcrun devicectl device info apps --device <UDID> | grep <name>   # confirm installed
  ```
- **First launch of a free-account app is blocked until the user trusts the developer on the device**: Settings → General → VPN & Device Management → "Apple Development: <email>" → Trust. Without this, `devicectl process launch` fails with "invalid code signature / not trusted by the user" (FBSOpenApplicationErrorDomain error 3).
- `xcrun devicectl list devices`: `unavailable` state usually means the iPhone is locked or hasn't been trusted on the Mac — ask the user to unlock and tap "Trust". The device can slip back to `unavailable` mid-task when the phone auto-locks, so re-check IMMEDIATELY before installing. While locked: `devicectl device install` fails with `CoreDeviceError error 4016` ("cannot fulfill the requested usage assertion requirements"), and `xcodebuild -destination 'platform=iOS,id=<UDID>'` produces a wall of confusing "platform doesn't match" errors for every simulator — it simply never resolved the device. Ask the user to unlock, then retry.

- **未签名 IPA(交付给用户自行签名旁加载: Sideloadly/AltStore/爱思)**(2026-09-05 实测 DeviceToolbox):不要走 archive(archive 流程要求签名),直接 build + 手拼 Payload 最快:
  ```bash
  # 1) 真机架构 Release 构建,关签名(旁加载包必须真机目标,模拟器产物装不上真机)
  xcodebuild -project X.xcodeproj -scheme X -destination 'generic/platform=iOS' \
    -configuration Release -derivedDataPath build/ipa-dd \
    CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY='' build
  # 2) 组装 Payload → zip
  APP=build/ipa-dd/Build/Products/Release-iphoneos/X.app
  rm -rf /tmp/x-ipa && mkdir -p /tmp/x-ipa/Payload && cp -R "$APP" /tmp/x-ipa/Payload/
  cd /tmp/x-ipa && zip -ry ~/Desktop/X-unsigned.ipa Payload > /dev/null
  ```
  验证:**`codesign -dv <out.ipa>` 输出 `code object is not signed at all` 即未签名铁证**(产物文件不带签名信息);`unzip -l` 确认 `Payload/X.app` 结构完整。不要用 `file` 命令验(本机 libmagic 5.48 与 sandbox 不兼容会刷屏 version-21 噪音且 exit 1,是工具噪音非失败)。
- **无头装机后用户抱怨"看不到 Xcode/模拟器界面"的应对**(2026-09-05 实测):agent 全程跑 xcodebuild/simctl 时用户屏幕本来就空。要用户"看见":① `open -a Xcode-beta`(或绝对路径 /Applications/Xcode-beta.app)拉 Xcode GUI 窗口(该 beta 无 Simulator.app,手机屏幕弹不出,见 §3 陷阱);② 用 `xcrun simctl io <UDID> screenshot ~/Desktop/x.png` 存桌面当可视证据(280KB 级 PNG,截图前可用 vision_analyze 自验 App 真在渲染),进程证据: `ps aux | grep '<App>.app/DeviceToolbox'` 会显示 CoreSimulator 容器路径;**App 在跑 ≠ 用户能看到窗口**——这是解释"为什么看不到"的关键。③ 用户口述的系统版本可能不存在: 先 `xcrun simctl list runtimes` 核对再承诺(用户说 iOS 26.1,机器只有 26.5/27.0 → 装到最近的 26.5 并明说,别默默装别的版本)。

## 5. Headless app-icon generation (no Photoshop/Pillow)

macOS system Python lacks Pillow, but every Mac has Swift + AppKit — draw the
icon with a Swift/CoreGraphics one-liner script (see `scripts/make_app_icon.swift`),
then downscale (NSImage renders @2x: a 1024 rect comes out 2048px — `sips -z 1024 1024`).

For a guaranteed headless-safe generator (no `NSImage.lockFocus`, which can render blank when no GUI session is attached), use the pure-CoreGraphics+CoreText variant `scripts/make_app_icon_coregraphics.swift` (CGBitmapContext gradient + `CTLineDraw` glyph → PNG; verified 2026-08-30). iOS single-size (Xcode 14+) `AppIcon.appiconset/Contents.json` needs only ONE image entry: `{"idiom":"universal","platform":"ios","size":"1024x1024"}` → the 1024px PNG.

Wire into xcodegen: `Assets.xcassets/AppIcon.appiconset/` in each target's source
dir + `Contents.json` (universal 1024x1024; platform ios vs watchos) +
`ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon` in that target's `settings.base`.
The catalog is auto-globbed by `sources: [ios]` — no explicit xcassets listing.
Verify the icon compiled into the product: `ls <app>/AppIcon*.png` + `Assets.car`.
Full recipe + the "empty Local Network list" diagnostic: `references/app-icons-and-local-network.md`.

- 若本机已装 Pillow(本 Mac system python3 实测 Pillow 11.3.0 可用),纯色 AppIcon 可一行生成:`python3 -c "from PIL import Image; Image.new('RGB',(1024,1024),(255,149,0)).save('AppIcon-1024.png','PNG')"`。**必须用 `RGB` 模式(无 alpha 通道)**——带 alpha 的 AppIcon 会触发 App Store/actool 校验失败;纯橙 #FF9500=(255,149,0)。
- **多彩/渐变正式 AppIcon 用 Pillow 参数化脚本生成**(2026-09-05 实测 DeviceToolbox: 纯橙占位 → 橙渐变白工具箱+诊断仪表): ① **超采样抗锯齿**: 画布放大 `SS=4`(4096px)画完再 `resize((1024,1024), Image.LANCZOS)`——Pillow 直接画 1024 锯齿明显;② 对角渐变逐像素 `t=(x+y)/(2*S)` 双色 lerp;③ 几何 API: 圆角矩形 `rounded_rectangle(radius=)`,提手弧 `arc(bbox, 180, 360, width=W)`(Pillow 角度 0°=3 点钟、y 向下,上半圈实测 180→360 正确),扇区 `pieslice(start,sweep)`,圆环 `ellipse(outline=, width=)`;④ **vision_analyze 迭代自检**(glm-4v): 每次出图先问"构图/溢出/几何缺陷",再决定改版——实例: 表盘 4 刻度+深色轴心让"仪表"被误读成"锁",v2 改橙色扫掠扇区+橙指针解决;⑤ 接入闭环: 备份原图→`cp` 覆盖 `AppIcon.appiconset/AppIcon-1024.png`(单图 1024 Contents.json 无需动)→重建→`simctl terminate` 后 `simctl io <UDID> screenshot` 拍 **springboard 桌面**确认图标上桌(app 前台时截的是 app 画面)→`simctl launch` 回 app;⑥ **改图标后必须重新 zip 打包桌面 ipa 覆盖旧产物**,否则交付物仍是旧图标(unzip -l 看 AppIcon60x60@2x.png 字节数变化可佐证新图入包);⑦ 生成脚本存 `docs/gen_appicon.py` 便于日后改配色/造型重跑。可改模板: `scripts/gen_appicon_pillow.py`。
- 生成后用 `xcrun actool Assets.xcassets --compile <outdir> --platform iphonesimulator --minimum-deployment-target 17.0 --app-icon AppIcon --output-partial-info-plist <plist>` 验证 Assets 能编译;注意 actool 的 `<outdir>` 必须先 `mkdir -p` 存在,否则报 "output directory ... does not exist"。
- `.strings` 语法校验:`plutil -lint <dir>/<lang>.lproj/Localizable.strings` → OK 即通过;`String(localized:)` 默认查 `Localizable` 表,developmentLanguage 设 zh-Hans 时中文为默认值。

## Verify

- `xcodebuild ... build` → `** BUILD SUCCEEDED **` for simulator (compile check, no signing).

## 7. 双 target watchOS app → 未签名 IPA（侧载到真表）

用户有 Apple Watch（如 Watch S 10）要装自研 watchOS App，但本机只有 Xcode-beta + 免费/企业证书时，交付 = 双 target 工程 + 未签名 IPA，用户侧载工具（全能签/Esign）重签。

**工程骨架（xcodegen，iOS 宿主 + 独立 watchOS App）**：
- iOS target `WatchHost`（最小 SwiftUI 宿主）+ `dependencies: [{target: WatchApp, embed: true}]` → xcodegen 出 "Embed Watch Content" 阶段，watch app 放 `<iOS.app>/Watch/`。
- watchOS target `WatchApp`（SwiftUI，`WKApplication: true` + `WKWatchAppIndependent: true`，独立运行不依赖宿主活着）。
- 双端 `SWIFT_VERSION: "5.9"`；两个 Info.plist 用 `GENERATE_INFOPLIST_FILE: "NO"` + `CFBundleIdentifier: $(PRODUCT_BUNDLE_IDENTIFIER)`。

**编译坑（2026-09-26 实测）**：`xcodebuild -scheme WatchHost -sdk watchsimulator -destination 'platform=watchOS Simulator'` 会报 "doesn't match WatchHost.app's supported platforms"（WatchHost 是 iOS target）。正解分两编：watch target `-scheme WatchApp -destination 'generic/platform=watchOS'`；宿主 `-scheme WatchHost -destination 'generic/platform=iOS'`。

**未签名 IPA 流水线**：
```bash
xcodebuild -project P.xcodeproj -scheme WatchApp -destination 'generic/platform=watchOS' \
  CODE_SIGNING_ALLOWED=NO -derivedDataPath build/sim build 2>&1 | grep -E "error:|BUILD"
xcodebuild -project P.xcodeproj -scheme WatchHost -configuration Release \
  -destination 'generic/platform=iOS' -derivedDataPath build/ipa-dd \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY='' build
APP=build/ipa-dd/Build/Products/Release-iphoneos/WatchHost.app
rm -rf /tmp/x-ipa && mkdir -p /tmp/x-ipa/Payload && cp -R "$APP" /tmp/x-ipa/Payload/
cd /tmp/x-ipa && zip -qry /tmp/X-unsigned.ipa Payload
```
校验：`ls $APP/Watch/` 含 `WatchApp.app`；`lipo -info $APP/WatchHost`=arm64；`codesign -dv $APP`=not signed at all；`plutil -p $APP/Watch/WatchApp.app/Info.plist` 核对 WKApplication/WKWatchAppIndependent。

**⚠️ 分发证书平台范围坑（2026-09-26 实测，用户证书截图）**：全能签/企业代签的 "iPhone Distribution" 证书若 Supported Platforms 只写 **"iOS, xrOS, visionOS" 而无 watchOS**，则签不了 watchOS 组件——双 target 侧载到 iPhone 后，Watch 端会"无法验证 App 完整性 / 装不上"。这是证书平台范围问题不是代码 bug。交付前先看证书"支持平台"栏：含 watchOS 才继续；不含则①换覆盖 watchOS 的证书，或②砍掉 watch 端只交纯 iOS app（诚实告知手表装不了）。xrOS = visionOS（Vision Pro 系统），别误读成 watchOS。

## 6. 批量把用户所有 iOS app 装进模拟器（2026-09-26 实测）

触发：「把我做的所有 iOS app 都装到虚拟 iPhone 上」。虚拟 iPhone = `simctl list devices` 里 state=Booted 的 iOS simulator。

1. **盘点**：`gh repo list <user>`（GitHub 上全部仓库）+ `find ~ -maxdepth 4 -name "*.xcodeproj"`（本地未 push 的工程）。缺的 clone 到 `~/Projects/<name>`。
2. **过滤 iOS 平台**（别盲目 build）：macOS 专属包 `head -5 Package.swift` 看 `platforms: [.macOS(.v13)]`（如 VoiceNotes）直接排除；纯 macOS xcodeproj（如 MediaConverter）同样排除。只有 iOS platform target 才进下一步。
3. **构建**：本机工具链在 Xcode-beta（无稳定 Xcode）时，xcrun 路径是 `/Applications/Xcode-beta.app/Contents/Developer/usr/bin/xcrun`，或 `export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer` 后再用普通 `xcrun`。simulator 目标 + `CODE_SIGNING_ALLOWED=NO`（免签、不烧 7 天签名字额）：
   ```bash
   xcodebuild -project X.xcodeproj -scheme X -sdk iphonesimulator \
     -destination 'platform=iOS Simulator,name=iPhone 17 Pro Max' \
     CODE_SIGNING_ALLOWED=NO -derivedDataPath /tmp/ios-sim-build/<proj> build
   ```
   多 app 时各自 `-derivedDataPath` 隔离目录可安全并行（terminal background=true 起 N 个）。
4. **安装 + 确定性验证**：
   ```bash
   xcrun simctl install <UDID> <DD>/Build/Products/Debug-iphonesimulator/X.app
   xcrun simctl listapps <UDID> | grep -i <name>   # 看 bundle id 行即装机成功
   ```
   注：`simctl install` 偶发瞬时 rc=2（模拟器刚 boot / 索引未稳），原样重试即成。
5. **预期管理**：exploit/漏洞链类 App（DeviceToolbox）在模拟器能装能启动、UI 可看，但真机模块走降级路径——向用户明说这是设计使然，不是装坏。
- For device: build with team → `devicectl install` → `devicectl launch` → check the app appears in `devicectl device info apps`.
- Watch app reachability still requires the iOS companion app installed & opened once (WCSession activation), then the Watch syncs within minutes.

## References

- `references/xcode27-watchos-sdk-quirks.md` — what the Xcode 27 beta watchOS SDK removed/changed and how to check a Swift interface for an API.
- `references/hermeswatch-architecture.md` — worked example: HermesWatch (watch control surface for Hermes Agent on a Mac): bridge API design, launchd hosting, E2E verification.
- `references/lan-http-diagnostics.md` — iPhone "could not connect to the server" for a LAN HTTP service: ATS `NSAllowsArbitraryLoads` fix, iOS 14+ Local Network permission, 5-step diagnostic ladder (server logs / tcpdump), `devicectl device info <subcmd> --device` syntax, rebuild+reinstall for Info.plist changes.
- `references/device-debug-and-build-verification.md` — devicectl screenshot syntax (Xcode 27: `device capture screenshot`), the Debug-build `.debug.dylib` verification trap (main binary is a Previews stub), and the TextField-input-lost diagnosis + defensive @State-buffer fix.
- `references/app-icons-and-local-network.md` — headless app-icon generation (Swift/CoreGraphics script, xcodegen wiring, 2048→1024 downscale) + the "app missing from Local Network list = request never fired (ATS)" diagnostic + full `devicectl uninstall` reset.
- `references/whisper-cpp-cli.md` — embedding whisper.cpp into an app: brew install whisper-cpp, model-is-NOT-autodownloaded trap + explicit `-m`, afconvert 16 kHz WAV requirement, hf-mirror model download, AIFF fails silently.
- `references/wkwebview-session-and-api-hook.md` — WKWebView session persistence (login lost on hard kill, deep WebsiteData paths, UTF-16LE localStorage) + the XHR/fetch hook + login-poll JS you inject via WKUserScript to capture a site's real API traffic in-app.
- `references/spa-api-reversing.md` — SPA 前端静态 API 逆向(不登录): webpack5 chunk 映射提取、域名配置模块字母映射、接口正则、登录参数挖掘、空 body 探针; 含天学网 up366 完整域名表/登录/任务/提交接口清单.
- `references/swift6-stub-self-verification.md` — Swift 6 语言模式陷阱 + 并行子代理/缺失服务层时的 stub 自验链(swiftc -parse → -typecheck with stubs → actool → plutil)+ 单 target iOS App 的 3-target project.yml 配方 + UITest 首次启动态稳定复现。
- `references/porting-third-party-app-triage.md` — 第三方 iOS 项目搬运评估: GPL 传染检查、三档拆解(可直接学/须重写/不可搬)、exploit 依赖指纹 grep、反搬运水印识别、干净移植磁盘规格模板。
- `references/simulator-live-watch.md` — "边写边看"实时循环: Device Hub 常显 + 后台源码监听自动 构建/安装/重启 + 截图 vision 自审, 零依赖配方与 2026-09-25 实测记录。
- `references/simulator-system-daemon-crash-loop.md` — 模拟器里 Apple 系统守护进程(PosterBoard/壁纸等)崩溃循环的诊断与止血: 认进程名→数报告→清数据卷壁纸缓存/PRBPosterExtensionDataStore→重启→验证零新报告 + launchctl 退出码 0。
- `scripts/make_app_icon.swift` — standalone Swift/AppKit icon generator (dark gradient + terminal glyph), `swift make_app_icon.swift out.png` then `sips -z 1024 1024`.
- `scripts/gen_appicon_pillow.py` — Pillow 渐变+几何 AppIcon 模板(超采样抗锯齿、arc/pieslice/rounded_rectangle 配方,§5 多彩图标一节配套).
- `scripts/sim-live-watch.sh` — 后台实时监听循环: 源码变动→增量 xcodebuild→simctl install+launch(用法: `sim-live-watch.sh <项目目录> <scheme> <app-bundle-id> <sim-UDID> [warm-DerivedData]`; 零依赖, macOS 自带 find 轮询; 详见 references/simulator-live-watch.md).
- `references/swiftui-compilation-traps-2026-11.md` — iOS SwiftUI 编译期陷阱速查(PHPhotoLibrary label 变了、Menu 类型推断超时、sheet() 作用域坑、JSON 转义翻车、xcodegen 必须 regenerate 等 10 条)。
