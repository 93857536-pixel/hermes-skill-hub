---
name: macos-app-icons
description: "给 macOS app 生成/更换应用图标:绘制→icns→工程接入→构建验证。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [macos, app-icon, icns, xcodegen, appkit, xcodebuild]
---

# macOS App 图标 (macos-app-icons)

触发: 任何 macOS app 需要加/换图标(AppKit/SwiftUI/xcodegen 或 Xcode 工程; **Tauri 项目同适用**, 见 `references/tauri-iconset-pitfalls.md`)。若用户提到"之前做的 app"且当前会话无上下文,先用 session_search 定位项目、技术栈与构建方式。**iOS app 要加/换图标(1024 PNG + Assets.xcassets 单图,Pillow 或 Swift 绘制)也适用本技能,产物差异与验证见 `references/ios-appicon-pillow-workflow.md`。**

## 完整流程(已在 TianXueBot 实战验证,见 references/tianxuebot-case.md)

1. **定位项目与技术栈**
   - 看 project.yml(xcodegen) / *.xcodeproj / Package.swift
   - xcodegen 项目:`project.yml` 是唯一真源,Info.plist 也由它生成
   - 查运行中的 app 来自哪个构建路径:`ps aux | grep <AppName>.app` → 决定重建目标,避免重建错目录

2. **生成 1024 母版图标**
   - 用 `templates/icon_drawer.swift`(Swift/AppKit 离屏绘制: NSBitmapImageRep + NSBezierPath + NSGradient),改图形段即可
   - 要点: 1024×1024、squircle 圆角 ~230pt、主体居中留边距、避免小字号文字(16px 不可读)
   - 母版存项目 `icon/` 目录留档(以后改设计直接改,不丢源)
   - 用 vision_analyze 自检构图/瑕疵再继续

3. **打包 .icns**
   - `bash scripts/make_icns.sh <master.png> <out.icns>`:sips 缩 10 尺寸 → iconutil 打包 → 往返校验
   - ⚠️ 校验别用 `file` 命令:部分沙盒环境 libmagic 版本不匹配会刷 17 万字符垃圾输出,用 iconutil 解包往返校验

4. **接入工程(xcodegen)**
   - .icns 放进 sources 目录下的 Resources 文件夹(会被当资源拷入 bundle)
   - ⚠️ `CFBundleIconFile: AppIcon` 必须加在 **project.yml 的 info.properties** 里 —— 直接改物理 Info.plist 会在下次 `xcodegen generate` 时被重写覆盖
   - ⚠️ 新文件放进 sources 目录后必须重新 `xcodegen generate`,yellow 文件夹组不会自动包含新文件,否则构建里没有该资源
   - **SwiftPM + 手写 build_app.sh 场景**(VoiceNotes 实测): 工程无 xcodegen,Info.plist 由 build_app.sh 内联生成 —— 在脚本里 `cp icon/AppIcon.icns "$APP_DIR/Contents/Resources/AppIcon.icns"` + Info.plist 模板加 `<key>CFBundleIconFile</key><string>AppIcon</string>`,验证用 `/usr/libexec/PlistBuddy -c "Print :CFBundleIconFile" <app>/Contents/Info.plist`

5. **构建**
   - 先 `xcodebuild -project P.xcodeproj -list` 确认 scheme 与 configuration
   - 匹配运行中 app 的构建路径: 若产物在 `<dir>/Build/Products/Release/`,说明原构建用的是 `-derivedDataPath <dir>`(该模式下 **必须配 -scheme**,用 -target 会报 "flag -scheme ... is required")
   - 常用: `xcodebuild -project P.xcodeproj -scheme S -configuration Release -derivedDataPath build_rel build`

6. **验证产物**
   - `ls <app>/Contents/Resources/AppIcon.icns`
   - `/usr/libexec/PlistBuddy -c "Print :CFBundleIconFile" <app>/Contents/Info.plist` → AppIcon
   - `codesign -dv <app>` 确认签名正常(adhoc 也可)

7. **重启生效**
   - 退出用 `osascript -e 'tell application "X" to quit'`(优雅),kill 仅作兜底
   - ⚠️ **内嵌 WKWebView 登录的 app: 强杀进程会丢未落盘的 WebKit 数据**(cookies/localStorage)→ 登录态丢失,重启后回到登录页。必须优雅退出;重启后核对页面是登录页还是已登录页
   - 从与运行中一致的构建路径重启(`open <app路径>`)

## 坑速查
- `iconutil -c iconset -o <path>` 输出路径必须以 `.iconset` 结尾,否则报 "The file extension must equal iconset"
- xcodegen 项目改 Info.plist 永远改 project.yml,不改物理文件
- `-derivedDataPath` 与 `-target` 不兼容,必须用 `-scheme`
- 覆盖运行中 .app 前确认构建路径与运行路径一致
- **字形阴影别用 CIGaussianBlur + draw(at:from:)**: 模糊后 extent 每侧扩 ~3×radius, from-rect 按原尺寸取会错位, 阴影跑到错误一侧(视觉上像"右上角白色污点")。用双层绘制: 先画下移半透明副本(fraction ~0.28), 再画本体, 简单可靠
- **`NSImage(size:) { }` 编译不过**: 当前签名是 `init(size:flipped:drawingHandler:)`, 必须 `NSImage(size: NSSize(...), flipped: false) { _ in ...; return true }`; `CIContext()` 当前 SDK 返回非可选, 不能 guard let
- **无 PIL 时生成多尺寸 .ico**: 手写 ICO 容器内嵌 PNG(ICONDIR + ICONDIRENTRY + PNG blob, Vista+ 支持), 见 references/programmatic-icon-pitfalls.md
- **vision_analyze 可能 400(aux 视觉模型临时拒绝 image_url)**: 兜底用确定性校验——PNG IHDR 读尺寸、iconutil 往返解包数文件、ICO 头读条目数; 布局在渲染前先按坐标算好(三角右缘 < 柱左缘、柱右缘 < 环内缘), 不依赖看图
- Swift/AppKit 角度约定: `appendArc` 0°=右、逆时针为正; 循环箭头环 = 两段弧留缺口 + 弧终点沿切线方向画箭头; 圆角三角 = 粗线描边 + `lineJoinStyle/.lineCapStyle = .round`

## 支持文件
- `templates/icon_drawer.swift` — 1024 母版绘制模板(改图形段即可用)
- `scripts/make_icns.sh` — master.png → .icns 一键打包 + 10 尺寸校验
- `references/tianxuebot-case.md` — TianXueBot 实战记录(路径/命令/登录态教训)
- `references/ios-appicon-pillow-workflow.md` — iOS AppIcon 变体: Pillow 超采样管线、vision 自检迭代(误读→改语义)、模拟器 springboard 无头截图验证、ipa 内图标校验
- `references/programmatic-icon-pitfalls.md` — 无 PIL 图标管线: ICO 手写容器、阴影双层绘制、弧/箭头几何、确定性校验兜底
