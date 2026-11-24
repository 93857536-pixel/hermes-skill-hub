---
name: macos-app-build-packaging
description: "Use when building/packaging macOS desktop apps."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [macos, appkit, xcodegen, xcodebuild, icns, icon, whisper, webkit]
---

# macOS 桌面 App 构建与打包

针对 macOS AppKit/SwiftUI 桌面应用（TianXueBot、WeChatExporter）的构建、打包、资源接入。触发场景：加 app 图标、改工程配置、重建、集成本地 CLI（whisper 等）、WebView 登录持久化问题。

## App 图标生成与接入（完整流程）

1. **绘制 1024×1024 母版**：用 Swift/AppKit 脚本绘制（NSBitmapImageRep + NSBezierPath + NSGradient）。矢量绘制最可靠（Swift 必然可用，无 PIL/rsvg 依赖）。已知良好脚本：`templates/icon_draw.swift`（学士帽+闪电风格，改坐标即可换造型）。
2. **视觉自检**：`vision_analyze` 检查构图/瑕疵，再进入打包，别省这一步。
3. **生成 iconset**：sips 缩放出 10 个尺寸（16/32/64/128/256/512 及 @2x 到 1024）到 `/tmp/AppIcon.iconset/`。
4. **打包 icns**：`iconutil -c icns /tmp/AppIcon.iconset -o <项目>/Resources/AppIcon.icns`。
   - **坑**：iconutil 的 `-o` 输出路径必须以 `.iconset` 结尾用于反向解包（`-c iconset` 时）；正向 `-c icns` 无此限制。
5. **工程接入**（xcodegen 项目）：project.yml 的 `info.properties` 加 `CFBundleIconFile: AppIcon` → `xcodegen generate`。
   - **坑**：Info.plist 由 xcodegen 从 info.properties 生成——改 Info.plist 必须同步改 project.yml，否则 generate 时被覆盖。
   - 验证：PlistBuddy 读 Info.plist 的 CFBundleIconFile + grep pbxproj 确认资源引用。
6. **重建并验证 bundle**：产物 `Contents/Resources/AppIcon.icns` 存在 + `PlistBuddy -c "Print :CFBundleIconFile"` 有值 + `codesign -dv` 签名正常。
7. **生效**：Dock/访达图标需重启 app 才刷新；重启前先确认登录态风险（见下）。

## xcodegen 项目构建要点

- **project.yml 是唯一事实来源**；`info.path` 指向的 Info.plist 会被 generate 重写。
- 构建方式决定产物路径（重建前先 `ps aux` 确认运行中 app 的实际路径，用同一方式构建才能原地更新）：
  - `xcodebuild -target X -configuration Release SYMROOT=build_rel` → `build_rel/Release/X.app`
  - `xcodebuild -scheme X -configuration Release -derivedDataPath build_rel` → `build_rel/Build/Products/Release/X.app`
- **坑**：`-derivedDataPath` 必须配 `-scheme`（`-target` + derivedDataPath 直接报错）。
- 无共享 scheme 时 `xcodebuild -list` 可确认 Xcode 自动生成的 scheme 名。
- 增量构建很快（Swift 预编译模块缓存），别怕重建。
- **Resources 子目录被展平**：xcodegen 将 `Sources/` 下的 Resources 文件夹内容直接复制到 bundle root，不保留子目录结构。如果代码用 `Bundle.main.url(forResource:subdirectory:)` 查找子目录，需改为直接从根目录查找（去掉 `subdirectory` 参数）。验证：`find <app>/Contents/Resources/ -name "*.json"` 看实际路径。
- **UserDefaults suiteName 陷阱**：`UserDefaults(suiteName:)` 使用与 `PRODUCT_BUNDLE_IDENTIFIER` 相同的字符串会打印警告 "does not make sense" 并返回 nil。改用 `group.<bundleID>` 或 `?? .standard` 兜底。

## 制作 DMG(Release 交付标准,用户硬要求)

用户发布软件时要求**可安装包(dmg/exe),不是 zip/源码/中间产物**。dmg 制作:

```bash
hdiutil create -volname "App Name" -srcfolder "<path>/App.app" \
  -ov -format UDZO "AppName-macOS-v1.0.0.dmg"
```

- 路径含空格必须加引号;`-srcfolder` 指向 .app 即可,自动把 app 放进 dmg 根。
- **验证必须挂载实测**: `hdiutil attach xxx.dmg -nobrowse` → `ls "/Volumes/App Name/"` 确认
  .app 在里面 → `hdiutil detach "/Volumes/App Name"`。只信 ls 输出,不信 create 的 return。
- 旧版 hdiutil 有 deprecated 警告(提示用 diskutil image create),不影响功能,忽略。
- 发布流程: `gh release upload <tag> xxx.dmg --clobber`(带代理 HTTPS_PROXY);用户要求
  删除旧 zip 资产时用 `gh release delete-asset <tag> <name>`。
- **避免把 zip 当交付物**: 用户会明确质疑"为什么不是打包好的"。dmg 才是 mac 可安装包;
  旧 zip 资产上传后若已有 dmg,主动清理。

## SwiftUI 设置面板对齐(Grid 替代 HStack+手工 frame)

设置页表单"标签+控件"对齐反复出问题的根因: 用 `HStack { Text(标签).frame(width:) + 控件 }`
手工对齐,标签宽度不同(中文 3 字 vs 6 字)导致控件起点漂移。**正确做法是 Grid 自动对齐**:

```swift
Grid(alignment: .trailing, horizontalSpacing: 12, verticalSpacing: 10) {
    GridRow { Text("默认输出格式:"); Picker(...).labelsHidden() }
    GridRow { Text("硬件加速:"); Toggle("", isOn: $x).labelsHidden() }
}
```

- Grid 自动算列宽,标签列右对齐、控件列左对齐,像素级一致;Toggle/Stepper/Picker
  全部放 GridRow 内,空标签用 `Text("")` 占位保持控件列对齐。
- 验证对齐: AX 树读各控件 x 坐标应完全一致(osascript position),或截图 + vision_analyze
  目测;不要用模糊的视觉描述当唯一证据,AX 坐标才是硬证据。

## WKWebView 登录态持久化陷阱

- 代码里 `websiteDataStore = .default()` 是持久化配置，**但不保证落盘**：进程被 kill（SIGKILL/超时终止）时 WebKit 来不及 flush，登录态直接丢。
- 检查是否落盘：`find ~/Library/WebKit/<bundle-id>/WebsiteData/ -name "*.localstorage" -o -name "Cookies*"`。LocalStorage 目录空 = 未落盘，重启必丢登录。
- **重启 app 前必须问用户**（登录可能要重来）；优先 `osascript -e 'tell application "X" to quit'` 优雅退出，再 kill 兜底。
- 若多次验证数据就是不落盘（如 up366 这类站），把它当已知限制告知用户，勿过度修复（别去搞私有 API flush）。

## 内嵌本地 CLI（whisper-cpp 等）

- `brew install whisper-cpp` 后模型不随包下载，必须手动下载到 `~/.cache/whisper-cpp/`（国内用 hf-mirror.com）。
- whisper-cli 1.9.x 默认模型路径是 CWD 相对 `models/ggml-base.en.bin`——app 调用必须显式 `-m` 绝对路径。
- whisper.cpp 对 mp3/m4a 压缩格式解码不可靠，先 afconvert 转 16kHz WAV。
- 全部坑与验证流程：`references/whisper-cpp-integration.md`。

## 环境提示

- Homebrew 装包：USTC 镜像三件套环境变量（见 memory）。
- 模型/大文件下载优先 hf-mirror.com。
- 系统 python3 是 3.9.6（无 X|None 语法），写校验脚本用 ~/.local/bin/python3.11 或纯基础语法。

## 常见 Swift 编译陷阱

- **NSImage/NSWorkspace 需要 `import AppKit`**：即使 SwiftUI 项目，用到这些 AppKit API 时必须显式 import。
- **signal() 需 @convention(c) 顶层函数**：`signal(SIGSEGV) { _ in ... }` 报错 "C function pointer cannot be formed from a closure that captures context"。用文件级 `private func handler(_: Int32) { ... }` 解决。
- **@Published didSet 在 init 中的陷阱**：`init()` 内直接给 `@Published` 属性赋值并立即读取可能触发 "self used before all stored properties are initialized"。先赋给局部变量，最后再赋值给 `self.xxx`。
- **Codable struct 与异构 JSON**：同一 JSON 数组包含不同形状的对象（如视频格式有 `videoCodecs` 而音频格式没有）时，非基础类型的字段全部设为 optional（`[String]?`），再用计算属性 `.safeVideoCodecs` 提供非可选访问。
