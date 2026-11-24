# iOS SwiftUI 编译期常见陷阱(2026-11 实测累积)

## 1. PHPhotoLibrary.requestAuthorization 参数标签变了

旧 API:`requestAuthorization(forAccessLevel:)`  
新 API(Swift/PIN/27 SDK):`requestAuthorization(for:)`  

错写为 `forAccessLevel:` → 编译器报错 `incorrect argument label`。  
修复例:AttachmentMediaView.swift 里已修过。

## 2. SwiftUI Menu 表达式过深导致类型推断超时

当 Menu body 有过多内联 Button + Label 嵌套时,Xcode 报
`the compiler is unable to type-check this expression in reasonable time; try breaking up the expression into distinct sub-expressions`。

解法:简化 label 为一行 simple view,或把 body 提成局部 var / private func。  
实战结论:把 Menu 改成 `Menu("附件") { ... }` 文字 label 最稳,避免 icon-only label 带多层修饰。

## 3. sheet() 修饰符作用域与 @State 不在同一 struct

MeTab.swift 有外层 `MeTab` struct 内含 `AccountDetail` 子视图。在 AccountDetail 上加
`.sheet(isPresented: $showKeyExport)` 但 `@State` 是 MeTab 的属性 →
`cannot find '$showKeyExport' in scope`。

解法:所有 `.sheet()` 必须加在声明对应 `@State` 的 View struct 上;
嵌套结构要么在顶层 struct 统一挂 sheet,要么把 state 也提升到子视图内部。

## 4. 递归 await 传递错误变量名(SELF-RECURSION BUG)

ViewModel.send(text, quoteMsgId:) 的 409 seq 冲突自愈分支:

```swift
// ❌ 错 —— plainText 是本地的拼接结果,下一轮会再次查 quoteTextMap
if lastSeq < targetSeq - 1 { await send(plainText, quoteMsgId: quoteMsgId) }

// ✅ 对 —— 传原始 trimmed,函数体内重新做 quoteId 查找
if lastSeq < targetSeq - 1 { await send(trimmed, quoteMsgId: quoteMsgId) }
```

规律:**递归调用时永远传原始输入**,不要在 self-recursive 路径上传已被转换过的中间值。

## 5. xcodegen sources 不会自动收录新文件

每次向 sources 目录新增 `.swift` / `.xcassets` / 资源文件后,**必须**重跑
`xcodegen generate`,否则 pbxproj 仍引用旧列表,构建报
`cannot find 'X' in scope`(文件明明在磁盘上)。

诊断:出现 "in scope" 错误时先 `grep -r "filename.swift" project.pbxproj` 看是否已注册。

## 6. JSON 字符串构造:escape 层数容易翻车

通过 write_file / patch 写入含 JSON 模板的 Swift 代码时,容易多出转义层:

```swift
// ❌ 错(双反斜杠,Swift 字符串字面量变成 "{\"q\":"...)
let s = "{\\\"q\\\":\\\"\\(val)\\\"}"

// ✅ 对
let s = "{\"q\":\"\\(val)\"}"
```

规律:Swift 字符串里 `\\` = 一个反斜杠字符;要得到 JSON 里的 `\"` 需要一个 `\` 在源码里写作 `\"`。  
write_file / execute_code 自身的 Python 引号层还要再套一层,最容易乱。  
**写完立刻 grep 相关行确认实际字节**。

## 7. VideoDocument / fileExporter 需要自定义 conforming type

iOS `.fileExporter` 要求 document 参数 conform `FileDocument` protocol。系统没有内置 `VideoDocument`。

如果想选视频/文件并拿到 URL:
- 视频:用 `PhotosPicker(selection:matching:.videos)` 或 `.fileImporter`
- 通用文件:用 `.fileImporter(allowedContentTypes:[.item])`(通配),拿到 URL 后自己判断 mime

不要凭空发明不存在的类型塞进 sheet(fileExporter:)。

## 8. SwiftUI Section(\"标题\") { } footer: { } 组合初始化器不存在

SwiftUI 的 `Section` 没有 \"标题+内容+footer\" 三合一简写初始化器。
正确写法:

```swift
Section {
    // content
} header: {
    Text("标题")
} footer: {
    Text("脚注")
}
```

少写 `content:` 或 `header:` label 都会触发级联 error。

## 9. PHPhotoLibrary.accessLevel vs authorizationStatus

新增权限声明(NSCameraUsageDescription 等)后,代码里调 `PHPhotoLibrary.requestAuthorization(...)`
也要跟 SDK 版本对齐——不同 Swift/PIN 版本 label 不一样。

## 10. CryptoKit P-256 rawRepresentation 格式坑

参考 `xcode27-watchos-sdk-quirks.md`:CryptoKit `rawRepresentation` 返回 **64B x||y**(无 SEC1 0x04 前缀),
`P256.KeyAgreement.PublicKey(rawRepresentation:)` **只接受 64B**,传 65B(SEC1 带 0x04)抛 incorrectParameterSize。
与 WebCrypto(JOSE/SEC1 65B)完全不同端。**绝对不要**在没有明确跨端桥接意图时手动 add/remove 0x04。

## 11. 类型检查超时:整段 ForEach / List body 太深(不只是 Menu)

`LazyVStack { let q = ...; let f = q.isEmpty ? a : a.filter {...}; ForEach(f) { MessageBubbleView(14 个参数) }; if !q.isEmpty && f.isEmpty { Text(...) } }`
→ `the compiler is unable to type-check this expression in reasonable time`。

解法(2026-11 实测有效):把**整个 ForEach 块搬进 `@ViewBuilder` 计算属性**,body 里只留一行

```swift
ScrollView { messageListView.padding(...) }   // body 只剩调用
```

注意 `let` 声明可以放在 `@ViewBuilder` 计算属性内部(在 ForEach 之前),不必挪进 body。

## 12. `@ViewBuilder` 计算属性只能有一个分支时必须兜底

`some View` 计算属性里写 `if 条件 { Section {...} }`(无 else)→ 类型推断失败;
写 `if { Section } else { EmptyView() }` 但**漏了 `@ViewBuilder`** → `branches have mismatching types 'Section<...>' and 'EmptyView'`。

`@ViewBuilder` 里用 `guard ... else { return }` 也不行 → `non-void function should return a value` +
`function declares an opaque return type, but has no return statements`。

**唯一稳的写法**:包一层 `Group { if 条件 { ... } }`(不要 else,也不要 guard)。

## 13. `ToolbarItem` 不能放进返回 `some View` 的计算属性

```swift
.toolbar { toolbarContent }        // ❌ return type of property 'toolbarContent' requires that 'some ToolbarContent' conform to 'View'
```

`ToolbarItem` 不是 `View`。**`.toolbar { }` 内部直接写 `if/else + ToolbarItem` 是合法的**,只有把它抽成计算属性才会炸。要复用就抽「按钮内部视图」,不要抽 ToolbarItem 本身。

## 14. `foregroundStyle(cond ? .accentColor : .secondary)` 报 ShapeStyle 无 accentColor

`type 'ShapeStyle' has no member 'accentColor'`——`.accentColor` 是 `Color` 的静态属性,不是 `ShapeStyle` 成员。
两侧都显式限定:`Color.accentColor : Color.secondary`,或改用 `.foregroundColor(...)`(接受 `Color?` 语义)。
这是 §2 那条 `foregroundStyle(cond ? .secondary : .red)` 的同类坑,凡是三元里混 `Color` 与层级样式就炸。

## 15. ⚠️ 编译通过 ≠ UI 正确:`Section(content:footer:)` 少 header 会静默丢标题

重构 Section 初始化器时只写了 `Section(content: { ... }, footer: { ... })` —— **编译零报错**,但那一组在界面上变成**没有标题的分组**,用户看不出「密钥管理」入口是什么。本会话真实踩到。

三条纪律:
1. 用 `Section(content:header:footer:)` 时,**header 和 footer 都要显式给**(只有 content+footer 是合法但语义残缺的重载);
2. 编译驱动的大改之后,必须**再看一眼渲染结果/截图**,不能只以 `BUILD SUCCEEDED` 收工(§8 的初始化器改造最容易在这一步悄悄丢内容);
3. 想验证某个标题/文案到底在不在,别 grep 二进制(见 ios-unsigned-ipa-delivery 的 UI 验收节),直接跑模拟器截图。

## 16. 类型检查错误会「移动」:修完一处,下一次构建在另一行/另一文件报

同一批改动引入多处深层表达式时,编译器每次只报第一个超时点。修好 ChatView 的 `messageListView`,下一轮报 MeTab 的 `accountDetailRows`,再下一轮报 toolbar,再下一轮报 `Section` 分支类型 —— 共 6 轮才绿。**把「迭代到 BUILD SUCCEEDED」当正常流程**,不要以为第一处报错就是全部问题。

## 17. 别用正则删 Swift 代码块

`re.sub(r'/// xxx.*?private var y: some View \{[^}]*\}', '', src, flags=re.DOTALL)` 会**在第一个 `}` 就截断**(视图代码里嵌套大括号极多),删掉半个 block 留下孤立 `}` → `Extraneous '}' at top level` + `Expected 'func' keyword in instance method declaration` + 一堆连带语法错。

处置:改 Swift 源码只用 **patch 精确串替换**(带完整块首尾上下文),或 execute_code 里 `content.replace(old_block, new_block)` 且先把 `old_block` 完整贴出来、`assert old_block in content`。删完立刻构建验证,别靠肉眼。
