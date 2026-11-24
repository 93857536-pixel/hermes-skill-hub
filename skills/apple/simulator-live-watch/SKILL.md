---
name: simulator-live-watch
description: "Use when 写 iOS 代码需模拟器画面实时刷新: 监听循环自动编译安装重启 + 截图vision自审。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [ios, simulator, xcode, device-hub, live-watch, xcodebuild, simctl]
    related_skills: [ios-watchos-app-development]
---

# 实时监听 iOS 模拟器画面 (sim-live-watch)

## When to Use

用户说"写代码时我要实时看到模拟器画面跟着变"/"盯着 iPhone 看你改"、要求 iOS UI 改动即时可见、或我开发 iOS 项目需要频繁截图自审界面时。
前提：macOS + Xcode + 模拟器 runtime；Xcode 27 beta 本机画面窗口 = Device Hub（无 Simulator.app）。

用户诉求："你写代码的时候, 我电脑上的模拟器 iPhone 画面要**随着我刚改的代码自动实时刷新**, 我盯着看"。
iOS 模拟器没有官方热更新, 但用「源码监听循环 + 自动增量编译 + 自动安装重启」能做到**秒级自动刷新**（实测循环反应 ~4 秒）。
Xcode 27 beta 本机没有独立 Simulator.app, 画面窗口由 **Device Hub** 承载, 需要常开。

## 1. 前提

- 本机 Xcode（beta 或非 beta）+ iOS 模拟器 runtime 已装（`xcrun simctl list runtimes` 核对；用户口述的 iOS 版本可能不存在, 装到最近的并明说）
- macOS（fswatch 不需要——脚本用自带 `find -newer` 轮询, 零第三方依赖, 不依赖 brew/代理）

## 2. 全流程（顺序执行）

1. **开模拟器**：
   ```bash
   UDID=<从 simctl list devices 选, 如 iPhone 17 Pro Max>
   xcrun simctl boot $UDID && xcrun simctl bootstatus $UDID -b
   ```
2. **开 Device Hub 窗口**（用户肉眼实时看的画面）：
   ```bash
   open -a /Applications/Xcode-beta.app/Contents/Applications/DeviceHub.app   # bundle: com.apple.dt.Devices
   ```
3. **启动监听循环**（后台常驻, 用 terminal background=true；脚本在本 skill 的 `scripts/sim-live-watch.sh`, 用户机上也有一份 `~/bin/sim-live-watch.sh`）：
   ```bash
   ~/bin/sim-live-watch.sh <PROJECT_DIR> <SCHEME> <APP_BUNDLE_ID> <SIM_UDID>
   # 可选第 5 参: 外部 DerivedData 路径(传热缓存可跳过全量重编)
   ```
   脚本行为：初始全量构建 → 每 2s 轮询 `<PROJECT>/Sources` 下文件 mtime → 有变化自动 xcodebuild 增量编译 → `simctl terminate/install/launch` → 写 `.live-review-events.log`。
4. **等初始构建完成**：`tail .live-review-build.log` 看到 `** BUILD SUCCEEDED **`，再手动补一次 `simctl install + launch`（初始构建阶段 App 还没装进模拟器）：
   ```bash
   xcrun simctl install $UDID <DD>/Build/Products/Debug-iphonesimulator/<SCHEME>.app
   xcrun simctl launch $UDID <BID>
   xcrun simctl io $UDID screenshot /tmp/base.png   # 基线画面
   ```
5. **正常开发**：之后每次 `patch`/`write_file` 保存源码, 循环 2-4 秒内自动编译+安装+重启, Device Hub 窗口自动变新界面。**不需要用户手动刷新。**
6. **AI 自审**（我这边, 免用户口头报界面）：
   ```bash
   xcrun simctl io $UDID screenshot /tmp/step-N.png
   ```
   → `vision_analyze` 对比改动前后（看导航标题/卡片/Tab 等关键元素是否变成预期值）。
7. **收尾**：完成后 `process kill` 监听循环；把 `.live-review-dd/ .live-review-marker .live-review-events.log .live-review-build.log` 加进项目 `.gitignore`（4 行, 归入"# 日志/临时"段）, 避免 git status 污染。

## 3. 验证判据

- 事件日志 `tail .live-review-events.log` 最新一行 = `build+install+launch OK`
- 改一处可见字符串（如导航大标题）→ 等 30s 内 → `simctl io screenshot` + vision 确认标题已变 → 改回 → 再确认已还原
- 聚焦验证脚本 6 项全过：`bash -n 脚本`、`git check-ignore` 4 个产物、源文件 `git diff --quiet HEAD`、无演示残留 grep、`pgrep -f sim-live-watch`、事件日志末行 OK

## 4. 踩坑（本会话实测）

- **`cannot execute tool 'metal' due to missing Metal Toolchain`**：新 DerivedData 全量重编才触发（增量命中缓存不触发）。修：`xcodebuild -downloadComponent MetalToolchain`（Apple CDN 直连可下, 不需要代理；下完 `xcrun --toolchain MetalToolchain metal --version` 确认）。
- **新 DD 目录 = 全量重编 = 慢且易撞 Metal 缺失**：项目里若有现成的热缓存模拟器 DD（如 `build/dd-*`）可作第 5 参传入, 但注意缓存过旧时代码全量重编不可避免, Metal 修好前白搭。
- **监听范围只有 `<PROJECT>/Sources`**：改 Info.plist/project.yml/测试文件不触发循环——那些改动后要手动跑一次构建或 touch 一个 Sources 下文件。
- **构建失败自愈**：失败不更新 marker, 循环 10s 后自动重试, 修好代码即恢复, 无需重启循环。
- **`simctl terminate` 对没跑的 bundle id 无害**（2>/dev/null 吞掉）。
- **秒级不是毫秒级**：构建几十秒封顶, 增量通常 3-8s；向用户说明这是"改完自动刷", 不是敲字即刷的热更新。
- Device Hub 窗口里选错设备（如停在 iPad）看的是别的模拟器——循环装的是指定 UDID, 记得在 Device Hub 侧栏选中那个设备。

## 4.5 无 XCUITest 的「截图巡检」路线(本机 XCUITest 必挂时用)

⚠️ 本机(2026-10-06 实测)**XCUITest 跑不起来**:`xcodebuild test` 报
`DTServiceHubClient failed to bless service hub for simulator`,结果 `** TEST BUILD SUCCEEDED **` 但 `Testing failed / BUILD INTERRUPTED`(erase 设备、`sudo killall -9 com.apple.CoreSimulator.CoreSimulatorService`、重启模拟器都无效;本机无 Simulator.app 只能 Device Hub)。**别在这个坑里耗超过 10 分钟**,换下面的路线——它对"验证某个界面真的长这样"完全够用。

1. `xcodebuild build -destination 'platform=iOS Simulator,id=<UDID>' -derivedDataPath /tmp/dd` (Debug)
2. `xcrun simctl boot <UDID>; xcrun simctl bootstatus <UDID> -b`(等启动完成,否则 screenshot 报 `Timeout waiting for screen surfaces`)
3. `xcrun simctl install <UDID> <DD>/Build/Products/Debug-iphonesimulator/<App>.app`
4. **临时启动参数钩子**把 App 直接带到目标界面/登录态(发布前必须删干净,删后 `grep -rn "lmhShot" ios/` 必须为 0):
   - `AppState.init`:读 `-lmhShotJwt <token>` 等,直接置 `authToken/userId/...`(免走登录,省掉收验证码)
   - `RootView`:`init() { _selectedTab = State(initialValue: <从 launch args 解析>) }`(SwiftUI 里 init 直接落在目标 Tab 的唯一写法)
   - 弹层类界面:`.task { if ProcessInfo.processInfo.arguments.contains("-lmhShotX") { showX = true } }`
   - 需要"已输入+已搜索"的界面(如搜索结果):`if let i = args.firstIndex(of:"-lmhShotQuery"), i+1 < args.count { query = args[i+1]; await search() }`
5. `xcrun simctl launch <UDID> <BID> <args...>` → `sleep 9` → `xcrun simctl io <UDID> screenshot /tmp/shots/xx.png`
   - 换屏必须 `simctl terminate` 再 launch(否则 launch 只把旧进程拉到前台、参数被忽略);脚本里逐屏循环最稳
6. **判读不要依赖 aux 视觉模型**:agnes-cn 是 1 次/分钟限流,批量调用必 429。改用系统 **Vision 框架离线 OCR**(`VNRecognizeTextRequest` + `recognitionLanguages=["zh-Hans","en-US"]`,`swiftc -O` 编一次反复用),输出按 y 排序的 `[x,y] 文本`,足以核对标题/按钮/文案是否出现或消失。
7. **判断"图片到底显示没显示/显示的是哪张"用像素探针**:CGContext 把目标矩形画进 buffer,打印 mean RGB、目标色像素占比、颜色桶数。例:上传的橙色图 `orangeish≈60%`(55 色桶),兜底纯色渐变 `blueish` 高、橙 0%、色桶 ≈1 → 能明确区分"真图"vs"占位底色"。
8. ⚠️ 本机 `file` 命令被 libmagic 版本不匹配污染(`magic.mgc is version 21`),验图片类型别用 `file`,用 `sips -g pixelWidth -g pixelHeight`。

## 5. 交付/沟通规范

- 启动时口头报备：模拟器 UDID、监听目录、窗口（Device Hub）位置、循环 pid/session_id
- 演示用改动（如临时改导航标题）必须**改回并截图验证还原**, 不留工作区脏改动
- `.gitignore` 那 4 行本地提交即可, 不擅自推 GitHub
