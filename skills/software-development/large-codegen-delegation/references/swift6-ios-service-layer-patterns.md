# Swift 6 严格并发下 iOS 服务层写法 + 自检阶梯

> 来源:DeviceToolbox 委派的「服务层子代理 A」实战(10 个 `Sources/Services/*.swift` + 兼容库 JSON + 2 个单元测试,零第三方依赖,只 Apple 公开 API)。SWIFT_VERSION 6.0 / iOS 17.0 / Swift 6.4 工具链。

## 1. 自检阶梯(服务层子代理如何自证代码正确)

整工程 build 常被并行方(UI 层未落盘)或锚点错误阻断。服务层子代理可用逐级升档的本地校验,不必等整合:

1. **语法级**:每个新 `.swift` 文件 `xcrun swiftc -parse <file>`(只查语法,不查类型/符号)。
2. **类型级(核心)**:把你负责的文件 + 锚点文件一起 typecheck,让锚点类型(CapabilityStatus 等)进作用域:
   ```bash
   SDK=$(xcrun --sdk iphonesimulator --show-sdk-path)
   xcrun swiftc -typecheck -swift-version 6 -sdk "$SDK" \
     -target arm64-apple-ios17.0-simulator \
     Sources/Core/*.swift Sources/Models/*.swift Sources/Services/*.swift
   ```
   EXIT=0 + 零警告即通过。注意 **`-swift-version 6` 必须显式加**(默认是 Swift 5 模式,会漏掉严格并发错误)。
3. **测试文件**:`xcodebuild test` 常因测试 target 缺 Info.plist 直接 code-sign 失败(见 §4),编译都到不了。改用「最小模块 + XCTest 框架」手动 typecheck:
   ```bash
   # 造一个只含锚点+你的文件的模块(@testable 需要 -enable-testing)
   xcrun swiftc -emit-module -enable-testing -module-name DeviceToolbox \
     -swift-version 6 -sdk "$SDK" -target arm64-apple-ios17.0-simulator \
     Sources/Core/*.swift Sources/Models/*.swift Sources/Services/*.swift \
     -emit-module-path /tmp/x/DeviceToolbox.swiftmodule -o /tmp/x/dummy.o
   # XCTest 的 swiftmodule 与 framework 不在 SDK 根,而在 platform 下
   PLAT=/Applications/Xcode-beta.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer
   xcrun swiftc -typecheck -swift-version 6 -sdk "$SDK" -target arm64-apple-ios17.0-simulator \
     -I /tmp/x -I "$PLAT/usr/lib" -F "$PLAT/Library/Frameworks" \
     Tests/DeviceToolboxTests/*.swift
   ```
   XCTest.swiftmodule 位于 `<platform>/Developer/usr/lib/XCTest.swiftmodule`,framework 在 `<platform>/Developer/Library/Frameworks/XCTest.framework`。
4. **整工程**:`xcodegen generate`(新文件才进工程)→ `xcodebuild ... -derivedDataPath <fresh> build`。

## 2. Swift 6 严格并发坑(每个都曾真实报错/警告)

- **`@retroactive` 扩展仍需显式 `==`**:对导入类型(如 Foundation 的 `OperatingSystemVersion`)加 `Comparable` 一致,Swift 6 **禁止跨模块自动合成 `==`**。必须同文件里显式写 `public static func ==` 再写 `<`。只写 `<` → `error: extension outside of file declaring struct ... prevents automatic synthesis of '==' for protocol 'Equatable'`。
- **非 Sendable 类型的 `static let`**:`static let bundled: SomeClass` 在 Swift 6 直接报 concurrency-safety 错。把类改成 `final class SomeClass: Sendable`(全部 `let` 存储属性且 Sendable)即可,不改公开签名。
- **`@MainActor` 类型 + 后台队列**:要在 NWPathMonitor 等后台回调里调用的静态方法,标 `nonisolated`;escaping 闭包只捕获 Sendable(别捕获可变局部 `var` 再改)。
- **NWPathMonitor 一次性采样**:在 `pathUpdateHandler` 里就把 `NWPath` 映射成 Sendable 基础类型(`status`/`interfaceNames`/bool),别把 NWPath 经 continuation 跨 actor。用 `NSLock` + 置 nil 的一次性 continuation 采样器防「多次 resume」崩溃;采样后立即 `cancel`。
- **getaddrinfo + inet_ntop**:包 `Task.detached` 里避免阻塞;取 `sin_addr`/`sin6_addr` 指针时先 `var copy = sa.pointee` 再 `&copy.sin_addr`(不能对 `pointee` 子字段直接取 `&`)。
- **弃用警告清零**:`CLLocationManager.authorizationStatus()`(类方法,iOS14 弃用)→ `CLLocationManager().authorizationStatus`;`CNAuthorizationStatus` 多一个 `.limited` 分支;`String(cString: [CChar])` → `buffer.withUnsafeBufferPointer { String(cString: $0.baseAddress!) }`。
- **只读权限状态**:通知授权只有异步 API,同步方法里返回 `.notDetermined` 兜底并在注释里写明(绝不 request)。

## 3. 签名对齐:读「已写完的消费方」而不只读契约文档

并行 UI 层已经按契约 §2 写完并 typecheck 过,它里面的 ViewModel/View 就是你签名的事实校验源。写服务前先 `search_files` 出所有 `XxxService()` / `PingResult` / `AppPermission` 等引用点,逐条核对:async vs sync、参数标签(`ping(host:)`)、默认参数、枚举 case 名(`faceID` 大写 ID)。契约文档一句话("签名不可改")之外,消费方调用点是更硬的约束 —— 偏离一个方法名/参数类型 = 全项目编译失败。

## 4. xcodegen 测试 target 必须补 `GENERATE_INFOPLIST_FILE`

`project.yml` 的 unit-test / ui-test target 若未设 `GENERATE_INFOPLIST_FILE: YES`(或 `INFOPLIST_FILE`),`xcodebuild test` 在 code-sign 阶段直接失败:

```
error: Cannot code sign because the target does not have an Info.plist file and one is not being
generated automatically. ... GENERATE_INFOPLIST_FILE ... YES (recommended). (in target 'XxxTests')
```

这与代码无关,报错发生在编译之前。测试 target 归属写 project.yml 的一方时,服务层子代理如实记入 build-notes.md 即可,不自修。
