---
name: dual-native-app-development
description: "Dual-native apps (macOS+Windows) via spec-driven subagents."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [macos, windows, winui, swiftui, subagent, xcodegen, ffmpeg, parallel]
    related_skills: [smart-model-delegation, macos-app-icons, macos-appkit-development, subagent-driven-development]
---

# 双端原生应用并行开发 (dual-native-app-development)

**用途**: 同时交付 macOS(SwiftUI/AppKit)与 Windows(WinUI 3/.NET)两套**原生**桌面应用(禁用 Electron/Flutter/Qt)。已在 MediaConverter(视频/音频转换器,FFmpeg 引擎)实战验证:macOS 端真实编译+19 测试通过,Windows 端静态审查交付。

**触发**: 用户要求开发"同时支持 macOS 和 Windows 的原生桌面应用",或任何需要双端并行产出完整可编译工程的任务。

## 0. 核心架构:Core/ 共享契约

```text
MediaConverter/
├── Core/          # 双端共用的转换规则/格式定义/参数 (JSON + 契约文档)
│   └── README.md  # 行为契约(FFmpeg 参数拼装规则)——两端必须逐条一致实现
├── macOS/         # Swift 5.9 + SwiftUI + AppKit, xcodegen 工程
└── Windows/       # C# .NET 8 + WinUI 3 + Windows App SDK
```

- Core JSON 用**扁平文件名**打进两端 bundle(`formats.json` 直接放 Resources 根,不要放子目录,避免两端加载路径分叉)。
- 契约文档必须写死:格式兼容矩阵、质量→CRF/码率表、硬件编码变体、进程/进度解析协议、输出防重名规则。

## 1. 工作流总览(本次实战顺序)

1. **先写 Core/** + 契约文档(主代理亲写,确定性内容不派发)
2. **图标先行**:Swift/AppKit 离屏绘制生成全套资产(见 §4),构建前必须就位
3. **写两份规格文件** `scripts/spec-<platform>.md` 落盘(见 §2)
4. **并行派发 2 个子代理**(deepseek-v4-pro,见 §3):A=macOS(可自行编译迭代),B=Windows(纯静态审查,本机无 Windows/.NET)
5. 子代理工作期间主代理写根级文档(README/BUILD/PACKAGING/LICENSE/.gitignore)+ 测试媒体生成脚本
6. **子代理回传后主代理必须复验**(§5)——子代理自报不可信,尤其迭代预算耗尽时
7. 提交入库(注意 .gitignore 要先于首次 git add 存在,否则 .venv 之类被误提交)

## 2. 规格文件(spec)写法要点

把 spec 写成文件放 `scripts/` 并 git 跟踪(可复现、可复用),delegate 时只传路径+铁律,context 保持小:

- **铁律节**:只读写自己的目录;禁改共享资产;允许/禁止执行什么命令;报错必须原文;最终中文汇报
- **目录结构**:逐文件列出(每个文件一行),不要留白
- **工程配置**:project.yml 关键 settings 直接给值(SWIFT_VERSION 5.9 避免 Swift6 严格并发报错;CODE_SIGN_IDENTITY "-" adhoc 免证书;ASSETCATALOG_COMPILER_APPICON_NAME)
- **逐文件功能规格**:每个文件 3-5 行职责+关键 API 约束,复杂逻辑(参数拼装/进度解析)给协议细节
- **验证节**:给出必须执行的规范命令(构建/测试/冒烟),限定迭代轮数(如≤6)
- **报告节**:规定汇报格式(文件清单/BUILD 结果/测试结果/遗留问题)

## 3. 并行派发

```bash
# 按 smart-model-delegation 决策表: 复杂代码生成 → deepseek-v4-pro
hermes config set delegation.provider deepseek
hermes config set delegation.model deepseek-v4-pro
# delegate_task(tasks=[macOS任务, Windows任务])  ← 并行批量
hermes config unset delegation.provider   # 必须立即恢复
hermes config unset delegation.model
```

- macOS 子代理**授权它自己跑 xcodebuild 修错**(省主代理一轮轮编译);Windows 子代理**明令禁止尝试构建**(无 dotnet,浪费时间)。
- 都配 `-derivedDataPath build` 避免污染 ~/Library/Developer/DerivedData。

## 4. 图标:Swift/AppKit 离屏绘制(无 Pillow 也能画)

本机 pip 源不可达时,用 `swift script.swift` + AppKit 离屏绘制(模板见 macos-app-icons/templates/icon_drawer.swift):

- `NSBitmapImageRep` + `NSGraphicsContext` + `NSBezierPath` + `NSGradient` 画 1024 母版(圆角 ~230/1024 squircle)
- **角度坑**:AppKit 0°=+x 逆时针(y-up);NSGradient angle 135° 才是"左上蓝→右下紫"
- 字形投影别用 CIGaussianBlur+from-rect(坐标错位会画到错误一侧),直接画偏移半透明副本
- icns:`iconutil -c iconset` 从 1024 母版自动出 10 尺寸 → `iconutil -c icns`(校验用反向解包数文件,`file` 命令在沙盒可能损坏刷屏)
- .ico 无 PIL 时手写:ICONDIR 头 + 每尺寸 ICONDIRENTRY(256 存 0x00)+ PNG 数据块,Swift 里拼字节
- 视觉自检用 vision_analyze;辅助视觉通道故障时(400 image_url),靠坐标数学自证无重叠

## 5. 主代理复验清单(子代理回传后必做)

1. **读 transcript 尾**:`tail ~/.hermes/cache/delegation/live/<id>/task-N.log` —— 找 `exit_reason=max_iterations`(迭代预算耗尽=工作被截断,必查)
2. **build-notes.md 可能为空**:子代理预算耗尽时根本来不及写,主代理补写
3. **重跑规范命令**:`xcodegen generate` → `xcodebuild build` → `xcodebuild test`(grep 过滤:BSD grep 不支持 lookahead,用 `grep -E "error:|BUILD"`)
4. **冒烟测试**:App 内置 `--smoke-test`(环境自检 JSON)+ `--smoke-convert <in> <out>`(完整转码管线)两个 CLI 标志,让无 GUI 也能端到端验证
5. **bundle 结构**:`/usr/libexec/PlistBuddy -c "Print :CFBundleDocumentTypes"`、Assets.car/AppIcon.icns 在位、`codesign -dv`
6. **Xcode 27 Debug 产物坑**:主二进制是 Previews stub,真实代码在 `<App>.debug.dylib`(验证字符串要 grep dylib)
7. Windows 端抽查:csproj 五要素(TargetFramework/UseWinUI/WindowsPackageType/SelfContained/AppxManifest)、XAML 事件处理器与后台代码一一对应、P/Invoke 声明

## 6. 坑速查(本次实战全部踩过)

- **子代理迭代预算耗尽**:macOS 端 50 轮用完时还差"最后修复+最终验证",遗留 3 处编译错误;主代理接手修(全是有可选数组未解包:`.videoCodecs.contains` → 用 `safeVideoCodecs` 计算属性)
- **Codable 可选字段泄漏到 UI**:`Text(fmt.label)` 遇 `String?` 编译错 → `Text(fmt.label ?? fmt.id)`;写 spec 时就约定"UI 不直接用可选字段"
- **xcodegen**:新增源文件后必须重跑 `xcodegen generate`,否则 `cannot find 'X' in scope`
- **Xcode 27 beta**:Debug 构建产物是 stub+dylib 双文件
- **本机无 Windows**:Windows 端交付=完整源码+静态审查,汇报必须诚实标注"未编译";把"需在 Windows 上验证的检查点"写进 build-notes
- **无 ffmpeg 也能验证**:单元测试覆盖参数拼装/进度解析,冒烟测试验证"not found"负路径;真实转码留给用户装好引擎后跑(fetch 脚本已备)
- **网络受限环境**:直连外网被墙时查 `scutil --proxy`(系统代理)+ `lsof -nP -iTCP:<port>`(代理进程);CLI 工具需 `export HTTPS_PROXY=http://127.0.0.1:1082` 才走通;pip/brew 装包同样受阻 → 能 Swift 画的就别依赖 Python 库
- **git 仓库**:首次 `git add -A` 前 .gitignore 必须已存在,否则 .venv 等 500+ 文件被误提交,事后要 `git rm -r --cached`

## 7. 验证

- macOS:`xcodebuild build` → **BUILD SUCCEEDED**;`xcodebuild test` → 全绿(本次 19/19);`--smoke-test` JSON 自检;`--smoke-convert` 真实转码(有引擎时)
- Windows:静态审查清单(引用完整性/x:Bind 对应/线程封送)写入 build-notes.md
- 双端一致性:Core JSON 交叉校验脚本(格式×编码器兼容矩阵引用完整、默认值正确)
