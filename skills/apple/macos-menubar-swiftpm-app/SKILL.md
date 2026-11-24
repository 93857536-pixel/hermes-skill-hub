---
name: macos-menubar-swiftpm-app
description: Use when 从零构建 macOS 菜单栏/工具类应用(SwiftPM+SwiftUI):骨架打包调试演示GIF。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [macos, swiftpm, swiftui, menubar, packaging, gif, gui-automation]
    related_skills: [macos-appkit-development, macos-app-icons]
---

# macOS 菜单栏应用构建 (SwiftPM + SwiftUI)

## 触发条件
- 构建 macOS 菜单栏 / 状态栏工具类应用（录音、转写、OCR、剪贴板等小工具）
- 用 SwiftPM（`swift build`）而非 xcodegen/Xcode 工程
- 需要手写 Info.plist 打包 .app、调试、GUI 自动化验证、演示 GIF

## 工程骨架（VoiceNotes 实战验证）
```
Package.swift            # swift-tools-version 5.9, platforms [.macOS(.v13)], executableTarget
Sources/<App>/
  main.swift             # NSApplication 手动启动（无 nib）
  AppDelegate.swift      # NSStatusItem + 菜单 + NSWindow(NSHostingView) + AppState 单例
  AppState.swift         # ObservableObject 共享状态（含 Note/Segment 等 Codable 模型）
  <Feature>.swift        # 业务模块（录音/转写/存储/导出…）
build_app.sh             # swift build -c release + 手拼 .app bundle
scripts/                 # 图标、截图、GIF、下载等辅助脚本
```

### main.swift（无 nib 启动）
```swift
import AppKit
let app = NSApplication.shared
let appDelegate = AppDelegate()   // 全局强引用，防释放
app.delegate = appDelegate
app.setActivationPolicy(.accessory) // 菜单栏应用（配合 Info.plist LSUIElement）
app.run()
```

### AppDelegate 要点
- `NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)` + `button.image = NSImage(systemSymbolName: "waveform", ...)`（注意必须写全 `NSStatusItem.variableLength`，写 `.variableLength` 会报 `type 'CGFloat' has no member 'variableLength'`）
- 菜单项 target 指向 self；动态标题（如 录音/停止）在 `objectWillChange.sink` 里刷新
- 主窗口懒创建：`NSWindow(contentRect:styleMask:[.titled,.closable,.miniaturizable,.resizable], backing:.buffered, defer:false)` + `NSHostingView(rootView: MainView().environmentObject(appState))`
- `applicationShouldTerminateAfterLastWindowClosed -> false`（关窗不退出）

### build_app.sh 打包（手拼 .app）
- 复制二进制到 `Contents/MacOS/<App>`，图标到 `Contents/Resources/AppIcon.icns`
- Info.plist 关键键：`LSUIElement=true`（菜单栏，无 Dock 图标）、`NSMicrophoneUsageDescription`（录音权限文案）、`CFBundleIconFile=AppIcon`、`LSMinimumSystemVersion=13.0`、`LSApplicationCategoryType`
- `xattr -cr .app && codesign --force --deep --sign - .app`（ad-hoc 签名，未签名首次打开需右键→打开）

### 调试开关（强烈建议内置，不污染默认行为）
- 环境变量 `VOICENOTES_OPEN_ON_LAUNCH=1` → 启动即开主窗口（GUI 自动化/录屏必需）
- CLI 参数 `--transcribe <file>` → 启动后自动执行核心任务（演示 + 无 GUI 调试）
```swift
if ProcessInfo.processInfo.environment["X_OPEN_ON_LAUNCH"] == "1" { showMainWindow() }
if let i = CommandLine.arguments.firstIndex(of: "--transcribe"), i+1 < CommandLine.arguments.count {
    DispatchQueue.main.asyncAfter(deadline: .now()+0.8) { appState.transcribe(URL(fileURLWithPath: CommandLine.arguments[i+1])) }
}
```

## 同步上下文调 async API（macOS 13+ SDK 常见）
URLSession.data(for:)、AVURLAsset.loadTracks 等是 async；在 DispatchQueue.global 同步代码里用 semaphore 包装：
```swift
let sem = DispatchSemaphore(value: 0)
var result: T?
asset.loadTracks(withMediaType: .audio) { tracks, _ in result = tracks?.first; sem.signal() }
sem.wait()
```
⚠️ 直接用 `URLSession.shared.data(for:)` 在非 async 函数里编译报 "async call in a function that does not support concurrency"。

## 电源/睡眠控制（合盖保活类菜单栏工具）

要让 Mac「合盖也不睡」给后台任务续命，机制只有一条可用路径：

| 手段 | 能否挡合盖睡眠 | 说明 |
|---|---|---|
| `caffeinate -d/-i/-s` | ❌ | 只影响空闲/显示睡眠，clamshell 仍睡 |
| IOPMAssertion（PreventUserIdleSystemSleep 等） | ❌ | 同上，合盖是硬件触发 |
| `sudo pmset -a disablesleep 1` | ✅ | 唯一的机器级开关，需 root |

要点：
- 用 `sudo -n`（非交互）调用；NOPASSWD 环境不弹密码框，没配就快速失败，别让 GUI 卡在密码框。
- **退出/崩溃必须复位 `disablesleep 0`**：放在 `applicationWillTerminate`，否则留下「永不睡眠」的坑。启动时再做一次对账（忙→补 1，闲→清 0）。
- 状态读取走只读命令，无需 root：
  - 合盖：`ioreg -rc IOService | grep -m1 AppleClamshellState` → `Yes` = **已合盖**（可用 `pmset -g log | grep -i clamshell` 看到 "Clamshell Sleep" 佐证）
  - 键鼠空闲：`ioreg -c IOHIDSystem | grep -m1 HIDIdleTime` → 纳秒
- 自动熄屏：先 `disablesleep 0` 再 `sudo pmset sleepnow`（否则被自己的开关 veto）。
- ⚠️ 别用 `CGEventSource.secondsSinceLastEventType` 算空闲：Swift 里 `matchState` 没有 `.idle`，`.combinedSessionState` 是 `CGEventSourceStateID` 的 case 而非 eventSource，签名对不上白折腾。`HIDIdleTime` 又准又简单。

### 「用户还在不在」的判定
`userPresent = 最近 N 秒有 HID 输入 || 盖子开着`。只判 `!lidClosed && idle<60` 会把「合盖 + 外接键盘」误判成没人，在用户正用电脑时强制睡眠。

### 可测试性（这类守护工具必做）
- 阈值全部走 config + 环境变量覆盖（`X_HOME/_GRACE/_POLL/_ACTIVITY/_DRYRUN=1`），加 `--selftest <秒>` 无头跑状态机并逐 tick 打印快照。
- `DRYRUN=1` 只记录「将要执行的 pmset」不真执行，才能完整验证 忙→宽限→自动熄屏 时序而不把机器真睡过去。
- 「上次活动时间」从**磁盘产物 mtime**（数据库/日志）推导，而不是内存里的 `lastBusyAt`——app 重启/崩溃后宽限计时才不错乱。

## 验证与演示管线（无 ffmpeg 环境）
1. `swift build -c release` → `bash build_app.sh` → 直接跑 `Contents/MacOS/<App>`（注入环境变量）而非 open
2. 冒烟：`pgrep -f <App>` + 查 `~/Library/Logs/DiagnosticReports/` 无崩溃
3. GUI 截图（三步）：`osascript` 拿窗口位置尺寸（逻辑坐标）→ `screencapture -x` 全屏（Retina 2x）→ PIL 按 2x 缩放裁剪窗口区域。脚本见 references/voicenotes-case.md 的 snap.py 模式
4. 演示 GIF：PIL 把 4-5 张关键帧 resize + 底部半透明黑条 + 白字标题 → `save(save_all=True, duration=2200, loop=0)`；中文字体用 `/System/Library/Fonts/PingFang.ttc`

## 坑速查
- `osascript -e 'tell application "X" to activate'` 对**未运行**的应用会按 bundle ID 启动一个**无参数新实例**（环境变量丢失）——杀掉旧实例前别 activate；GUI 操作一律指向你启动的那个 PID
- CGWindowID（screencapture -l 用）会因窗口重绘/activate 失效，报 "window_not_found" → 重新枚举再截图
- SwiftUI 的 Text 不在 AX 树里（cua-driver ax 模式看不到状态文本）→ 验证状态用视觉截图而非 AX
- FileHandle 的 truncate/write/seek/synchronize 在 macOS 15 SDK 标 throws：去掉 `try` 报 "call can throw"，加上又可能报 "no calls to throwing functions" 警告——**统一加 try**，警告可忽略
- 菜单栏 app 无窗口时 `capture(app='X')` 失败（cua-driver 按窗口捕获），先开窗再截
- **子进程管道死锁（最坑，症状是「主线程正常但后台逻辑全静默」）**：`Process` 里先 `waitUntilExit()` 再 `readDataToEndOfFile()`，子进程输出超过管道缓冲（~64KB；`ioreg -rc IOService` 约 95KB）时双方互等，tick 永不返回、日志一条不写。**必须先读 pipe 再 wait**，并尽量用 `| grep -m1 <关键字>` 把输出压小。
- 登录自启别用 `SMAppService`（ad-hoc 签名不稳）：直接写 `~/Library/LaunchAgents/<label>.plist`（`RunAtLoad` + `KeepAlive.SuccessfulExit=false`），下次登录自动加载。从 hermes gateway 进程内执行 `launchctl bootstrap` 会被安全策略拦（"unsafe from inside the gateway process"），但 plist 落到目录里就已生效。
- `screencapture -x` 在合盖/无显示输出时返回 "could not create image from display"——不是权限问题，别去折腾录屏授权。
- `swift build` 产物在 `.build/release/`（不是 `build/release/`）；打包脚本放工程根目录时 `cd "$(dirname "$0")"` 即可，别多写一层 `/..`。

## 发布准备（用户偏好：一次到位）
- 图标：`scripts/icon_drawer.swift`（AppKit 离屏绘制 1024 母版，蓝青渐变+squircle+主体图形）+ `scripts/make_icns.sh`（sips 10 尺寸 + iconutil + 往返校验）——详见 macos-app-icons skill
- 演示 GIF 置顶 README（第一屏 3 秒看懂）
- README 竞品对比表 + 中文说明；AGENTS.md 发布流程（版本号三处同步 → 编译 → tag → push → 验证 Actions）
- 用户会明确要求"图标 + GIF 到位后再推 GitHub"——先本地交付演示，再问是否推送

## 支持文件
- references/voicenotes-case.md — VoiceNotes 实战案例：whisper.cpp 集成坑（JSON 双格式/父目录）、音频处理、GLM API 封装、截图/GIF 脚本全文、项目结构
- references/hermeskeeper-case.md — HermesKeeper 实战：hermes 忙闲信号（state.db mtime / active_agents / pid 存活）、合盖保活状态机、pmset 控制与退出复位、dry-run 自测模式
