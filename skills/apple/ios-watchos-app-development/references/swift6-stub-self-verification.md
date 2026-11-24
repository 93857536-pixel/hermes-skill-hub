# Swift 6 模式 + 并行子代理 stub 自验(从零搭 iOS App UI 层)

来源:2026-09-05 DeviceToolbox(纯 SwiftUI,零第三方依赖,SWIFT_VERSION 6.0,iOS 17.0,xcodegen)。场景:并行子代理 A 写 `Sources/Services/`,B 写 UI 层;Services 尚未落盘时 B 仍要验证自己的 UI 层类型正确。

## 1. 单 target iOS App 的 project.yml(3 targets:app + unit-test + ui-test)

```yaml
name: DeviceToolbox
options:
  bundleIdPrefix: com.yourname
  developmentLanguage: zh-Hans        # 中文默认,英文跟随系统
  deploymentTarget: { iOS: "17.0" }
settings:
  base:
    SWIFT_VERSION: "6.0"
    CODE_SIGN_STYLE: Automatic
    DEVELOPMENT_TEAM: 4B7F8BR8R4
targets:
  DeviceToolbox:
    type: application
    platform: iOS
    deploymentTarget: "17.0"
    sources: [Sources]
    resources:
      - path: Sources/Resources        # Assets.xcassets + *.lproj + json 全进 app
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.yourname.DeviceToolbox
        ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon
        ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME: AccentColor
        TARGETED_DEVICE_FAMILY: "1"
    info:
      path: Sources/Resources/Info.plist
      properties:
        CFBundleDisplayName: DeviceToolbox
        UILaunchScreen: {}
        NSCameraUsageDescription: 用于检测相机能力 / Used to check camera
        NSMicrophoneUsageDescription: ...
        NSLocationWhenInUseUsageDescription: ...
        NSPhotoLibraryUsageDescription: ...
        NSBluetoothAlwaysUsageDescription: ...
        NSFaceIDUsageDescription: ...
  DeviceToolboxTests:
    type: bundle.unit-test
    platform: iOS
    deploymentTarget: "17.0"
    sources: [Tests/DeviceToolboxTests]
    dependencies: [{ target: DeviceToolbox }]
  DeviceToolboxUITests:
    type: bundle.ui-testing
    platform: iOS
    deploymentTarget: "17.0"
    sources: [Tests/DeviceToolboxUITests]
    dependencies: [{ target: DeviceToolbox }]
schemes:
  DeviceToolbox:
    build: { targets: { DeviceToolbox: all, DeviceToolboxTests: [test], DeviceToolboxUITests: [test] } }
    test: { config: Debug, targets: [DeviceToolboxTests, DeviceToolboxUITests] }
```

要点:
- `info.path` 指定位置后,xcodegen `generate` 会直接在该路径产出 Info.plist;`resources: Sources/Resources` 会递归打包整个资源目录,而 xcodegen 会自动排除被引用的 Info.plist。
- 契约要求"中英双语 usage description"就直接写 `中文 / English` 混合短句进 plist(InfoPlist.strings 本地化是可选进阶,不必强求)。
- `DEVELOPMENT_TEAM` 从 `defaults read com.apple.dt.Xcode IDEProvisioningTeamByIdentifier` 拿 teamID,别用证书里的 team(见主 SKILL §4)。

## 2. 并行子代理 + 缺失服务层的 stub 自验链

当 `Sources/Services/` 尚未落盘(协作方在写),完整 `xcodebuild` 会报成片 "cannot find 'XxxService' in scope"。**不要替对方补写**;用自己的代码 + 临时 stub 证明 UI 层类型正确:

1. **语法级**:对每个 `.swift` 跑 `xcrun swiftc -parse <file>`(只查语法,不解析 import,零失败即过)。
2. **类型级(核心)**:在 `build/stubs/` 下写一份 `ServicesStub.swift`(签名与契约严格一致,只返回 dummy 值),再用 `swiftc -typecheck` 把 Core+Models+stub+全部 UI 文件一起编译:
   ```bash
   SDK=$(xcrun --sdk iphonesimulator --show-sdk-path)
   xcrun swiftc -typecheck -sdk "$SDK" -target arm64-apple-ios17.0-simulator -parse-as-library \
     Sources/Core/*.swift Sources/Models/*.swift build/stubs/*.swift \
     Sources/DeviceToolboxApp.swift Sources/ViewModels/*.swift Sources/Views/**/*.swift
   ```
   `EXIT=0 且无输出` = 自己这层类型全对。**stub 放 `build/` 下,绝不放 `Sources/Services/`**——不进 xcodegen 编译、不污染协作方领地。
3. **资源级**:`xcrun actool`(Assets)、`plutil -lint`(strings)、`plutil -p`(查 Info.plist 权限/LaunchScreen)。

若还缺一个锚点(只读、禁止修改)文件的 Swift 6 bug 阻塞 typecheck,可 `cp` 该文件到 `build/stubs/` 打补丁后用副本替代原文件参与 typecheck,原文件不碰。

## 3. Swift 6 语言模式陷阱(详见主 SKILL §3)

- `@retroactive Comparable` 需显式 `==`(否则 "prevents automatic synthesis of '=='")。
- `@MainActor` class 的 `static let` 被默认参数引用 → `nonisolated static let`。
- 锚点类型不遵循 `Hashable` → 不能用 `NavigationLink(value:)`,用 destination-based。
- 非 throws async 方法别套 `try await`(只产生 warning);顺序 `await` 优于 `async let` 并发写法(更省事且避开 MainActor 隔离告警)。

## 4. UITest 首次启动态的稳定复现

App 入口读 `ProcessInfo.processInfo.arguments`,含 `-resetDisclaimer` 时先清 UserDefaults 键,再构造 `@StateObject`;UITest `launchArguments = ["-resetDisclaimer"]` 即可稳定复现"首次启动"流程。给被断言的按钮显式 `.accessibilityIdentifier("disclaimer.accept")`(别依赖本地化 label,测试语言不固定时 identifier 最稳)。

## 5. 兄弟域真正落盘后的"契约对账" + 共享目录并发坑

stub 自验只证明"你的代码 vs **你假定的**契约"类型一致;兄弟域**真正落盘后签名常与假定不符**,必须读对方真实文件对账(2026-09-05 DeviceToolbox 实测差异):

- **服务层是 `enum` + `static` 方法,不是可实例化 struct** → 删掉 `private let workspace = WorkspaceService()`,直接 `WorkspaceService.listDirectory(at:)`。方法名也与假定不同:`list`→`listDirectory`、`createFolder`→`makeDirectory(named:in:)`、`rename`→`renameItem(at:to:)`、无批量 delete 只有单条 `deleteItem(at:)`(自己循环)、批量 copy/move 统一走 `transferItems(_:into:mode:conflictPolicy:)`(返回 `FileBatchResult`,含 `failures` 清单可提示"部分失败")。
- 常量命名对不上:`SandboxRoots.temporary`(不是 `.tmp`)、`.imported` 已存在(别手动拼 `Documents/Imported`)。
- 导入走便捷入口 `ImportService.importIntoImportedFiles(_:)`(免传目录)。
- **本地化 key 与兄弟域约定对齐**:兄弟域用 `Kind.temporary.rawValue == "temporary"` → key 是 `files.root.temporary`,别另造 `files.root.tmp`,否则集成期出现同义双 key。

**共享目录并发坑**:并行子代理共同写同一个父目录(如 `Sources/FileWorkspace/`,A 写服务层、C 写 `ViewModels/`+`Views/` 子目录)时,兄弟代理重命名/清理**自己的**文件可能连带 `rm` 掉你的子目录——本会话实测 C 的 5 个文件被 A 整体清空一次。铁律"禁写同一文件"防不住"清空父目录"。对策:写完立即 `find`/`ls` 验证落盘;构建前再确认一次;被删就重写(内容在上下文里),并在汇报里明示该并发冲突。

## 6. SwiftUI 同一 view 叠多个弹窗 → `.background` 锚点分散

一个视图同时需要多个 `.alert`/`.sheet`/`.confirmationDialog`/`.fullScreenCover` 时,全挂在同一个节点上**只有最后一个生效**(SwiftUI 经典坑,本会话 DeviceToolbox 文件工作台 UI 层实测:重命名/新建文件夹 alert + 删除 confirmationDialog + 错误 alert + 目录选择器 sheet + QuickLook fullScreenCover)。

修法:每个弹窗用一个独立 `.background { Color.clear.<modifier> }` 锚点,强制分散到不同 view 节点:
```swift
content
  .sheet(isPresented: $showPicker) { ... }                                  // 节点1
  .background { Color.clear.fullScreenCover(item: $preview) { ... } }        // 节点2
  .background { Color.clear.alert("重命名", isPresented: $rename) { TextField(...); Button(...) } }  // 节点3
  .background { Color.clear.confirmationDialog("删除", isPresented: $del) { ... } }  // 节点4
  .background { Color.clear.alert("错误", isPresented: $err) { ... } }       // 节点5
```
- 同类 modifier(两个 alert)必撞;不同类(一个 sheet + 一个 fullScreenCover + 一个 alert)偶尔能共存,但统一锚点最稳。
- iOS 16+ 的 `.alert(_:isPresented:actions:message:)` 支持在 actions 里放 `TextField`(重命名/新建文件夹的输入框)。
- 多个同类文本输入弹窗可合并成单一 `TextPrompt` 枚举(带关联值 `case rename(FileEntry)` / `case newFolder`)驱动一个 alert,减少弹窗数。

## 7. 域 B 已落盘时写补丁+仓库 UI 层(域 C2,2026-09-05 实测)

域拆分后期:服务层(域 B)已全量落盘且构建通过,UI 层(域 C2)直接读源码对签名,一次通过(仅 1 处编译错)。

- **契约以源码为准**:精读域 B 公开签名——`PatchProject`/`PatchRule`/`PatchAction`(replaceFile|deleteFile|addFolder)、`ProjectStore.list/load/save/delete`、`PatchPackageCodec.encodePackage/decodePackage/import3105Package/detectFormat`、`PatchTransaction.apply/restore/isApplied/latestReceipt` + `defaultAppliedRoot(projectName:)/defaultJournalRoot()`、`RepositoryStore.listSources/addSource/fetchIndex/download`、`RepositoryImportService.importPackage`。对齐后零差异。
- **`ProjectStore.delete(id:)` 声明为 `throws` 但条目缺失时静默 `return`** → 调用处仍需 `try`(本会话唯一编译错误:`call can throw but is not marked with 'try'`)。
- **Swift 6:`View` 协议本身是 `@MainActor`** → View struct 的方法可直接改 `@State`,不必给每个 view 方法标 `@MainActor`;ObservableObject VM 显式 `@MainActor final class` + `@Published`(import Combine);服务层 `struct ... : Sendable` + `enum` 错误(带中英文案)。VM 里同步磁盘/加密调用(小数据/非私密包,KDF 只在私密包发生)可直接跑 MainActor,不必 `Task.detached`。
- **tab 根视图不持有自己的 NavigationStack**,用 `.navigationDestination(for: Route.self)` + `NavigationLink(value:)`(由 MainTabView 外层 NavigationStack 包裹,避免嵌套双导航栏)。代价:无 NavigationPath 时程序化 push 做不了——"新建草稿后自动跳编辑器"这类需求只能放弃,改为新项出现在列表顶部 + 用户点入。
- **自绘沙盒目录树选择器(选目标路径)**:根固定 `Documents/Patches/Applied/<name>/`(`onAppear` 先 `createDirectory(withIntermediateDirectories:true)` 确保存在,否则空目录没得逛);目录可进入、文件可点选(checkmark 高亮)、"完成"= `选中文件 ?? 当前目录`;调用方把返回 URL 相对应用根换算成相对路径填回 TextField(最终以文本为准,走 `PatchPathValidator` 校验)。addFolder 这类"选一个还不存在的东西"主要靠手动输入相对路径,树选择器辅助有限。
- **私密包导入/下载统一"可选密码"弹窗**(`.fileImporter` → alert 带 `SecureField`,留空 = 非私密):服务层在解码前无法区分"需密码"vs"损坏"(`decodePackage` 把两者都映射成 `invalidPasswordOrCorruptedPackage`),所以不按错误类型二次询问,统一提示一次,一次交互覆盖两种情况。
- **跨域只读复用**:目标树选择器直接复用域 A 的 `WorkspaceService.listDirectory`、`FileEntry`、`SandboxRoots`、自由函数 `filesErrorMessage`——已落盘的类型/函数只读引用不算双写违规(§8 双写禁令只禁"写兄弟文件",不禁"读").
- **编辑已应用项目**:改规则后再 `apply` 会触发域 B `projectAlreadyApplied`(需先回滚);UI 不拦截,错误如实呈现。私密项目编辑器:`load(id, password: nil)` 失败且 `entry.isPrivate` → 显示密码解锁页重载(而不是把失败当普通错误)。

