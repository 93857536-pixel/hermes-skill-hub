---
name: swift-coretext-offline-pdf
description: Use when 离线生成 PDF 或 EPUB(Swift/CoreText/自实现 ZIP)时。
version: 1.0.0
metadata:
  hermes:
    tags: [swift, pdf, coretext, cgpdfcontext, epub, zip, macos]
    related_skills: [swift-zip-archive]
---

# Swift CoreText 离线 PDF / EPUB 生成（macOS）

零第三方依赖、离线生成 A4 PDF（中文用系统 PingFang SC）或 EPUB（stored-ZIP，见 swift-zip-archive skill 的 CRC/布局细节）。
实战来源：WeChatExporter v2.16.0 EBookExporter（chat.json → EPUB + PDF 双产物，Windows 对位打印版 HTML）。

## 1. 生成 PDF：CGPDFContext 写文件（别碰 WKWebView/NSPrintJob）

WKWebView 打印到文件在 Swift 6 + 并发下不可靠（主线程 RunLoop 泵、CUPS 异步落盘、闭包推断失败）。
直接 CGContext + CoreText 排版：确定性、可 smoke test、离线。

```swift
// Swift 桥接签名（实测）：
let consumer = CGDataConsumer(url: outURL as CFURL)            // .init(url:) 要 CFURL 非 URL，返回 optional
var mediaBox = CGRect(x: 0, y: 0, width: 595, height: 842)     // A4 pt
let ctx = CGContext(consumer: consumer, mediaBox: &mediaBox, nil)  // 第 3 参写 nil 不加 label
ctx.beginPDFPage(nil)
// 翻转为左上原点（CoreText 习惯 y 向下）：
ctx.textMatrix = CGAffineTransform.identity   // 不能写裸 .identity（报 cannot infer contextual base）
ctx.translateBy(x: 0, y: 842)
ctx.scaleBy(x: 1, y: -1)
...
ctx.endPDFPage()
ctx.closePDF()
// 文件已由 consumer 直接写盘，最后 FileManager.fileExists 校验即可
```

## 2. 字体与属性（最常踩的坑）

- `CTFontCreateWithName(_ as CFString, size, nil)` 返回**非 optional**，不要 guard let；缺失自动回落系统默认。更稳：`NSFont(name: "PingFang SC", size: 10.5) ?? NSFont.systemFont(ofSize:)`（标题用 PingFangSC-Semibold/Medium）。
- **`NSAttributedString` 没有 `.attributedStringValue` 成员**。两条路：
  - `let cfAttr = attr as CFAttributedString`（条件 cast 恒成立，直接可用）；
  - 或 `CFAttributedStringCreate(nil, text as CFString, [CFAttributedStringKey.font: f, CFAttributedStringKey.foregroundColor: cgColor] as [CFString: Any])`。
  - `kCTFontKey`/`kCTForegroundColorKey` 常量**不可见**，一律写 `CFAttributedStringKey.font/.foregroundColor`。
- `CGColor` 没有 `init(gray:alpha:)`，用 `CGColor(red:g:b:alpha:)` 或 `NSColor(...).cgColor`。
- `CTLineCreateWithCFRange` 在部分构建目标不可见 → 统一用 `CTLineCreateWithAttributedString`。

## 3. 自动折行（长消息/中文无空格）

CTFramesetter 路径（比 CTLineCreateWithCFRange 循环更稳）：

```swift
func wrappedLines(_ text: String, width: CGFloat, font: NSFont, color: NSColor) -> [CTLine] {
    let attr = NSAttributedString(string: text, attributes: [.font: font, .foregroundColor: color])
    let cfAttr = attr as CFAttributedString
    let fs = CTFramesetterCreateWithAttributedString(cfAttr)
    let path = CGPath(rect: CGRect(x: 0, y: 0, width: width, height: 100_000), transform: nil) // 注意 transform: 标签
    let frame = CTFramesetterCreateFrame(fs, CFRange(location: 0, length: 0), path, nil)
    return CTFrameGetLines(frame) as! [CTLine]
}
```
逐行 `ctx.textPosition = CGPoint(x: margin, y: y); CTLineDraw(line, ctx); y += 行高`（行高用 `CTLineGetTypographicBounds(line,nil,nil,nil)`）；每行前检查 `y + 行高 > pageH - margin` 则 `endPDFPage()+beginPage()` 换页。

## 4. EPUB 打包要点（ZIP 字节细节见 swift-zip-archive skill）

- 条目顺序：`mimetype`（首条目、method 0 stored、**extra field 必须为空**）→ META-INF/container.xml → OEBPS/*。
- OEBPS 3.0：content.opf（manifest 含 nav.xhtml properties="nav" + toc.ncx + chapter1.xhtml + style.css）、ncx navMap、`<br/>` 替换 `\n`、`&<>"` 全 XML 转义。
- 字节追加用 `Data.appendLE(UInt16/UInt32)`（小端），别用 `withUnsafeMutableBytes { }` 多行 storeBytes（闭包推断易报 contextual base 错）。
- 校验：python `zipfile` 查 `infolist()[0].compress_type == 0 and extra == b""` + `testzip()` + minidom 解析各 XML。

## 5. 双端对位（Windows 没有 CoreText）

Windows 文档版**别碰 WPF XPS**：.NET 8 的 `System.Windows.Xps.Packaging.XpsDocument` 是新式流式 API（`new XpsDocument(path, FileAccess.ReadWrite)`、`AddFixedDocumentSequence()`、`FixedDocument.Pages` 是 PageContentCollection、`FixedPage` 没有 `.Content` 属性），旧文档全失效；且 `TextBlock.Measure` 在无显示环境不可靠。
稳妥做法：Windows 生成**打印版 HTML**（`@page{size:A4;margin:14mm}` + 白底 + 语义化 `.msg/.who/.ts`），浏览器 Ctrl+P / 另存 PDF。纯 BCL（System.Text.Json + BinaryWriter）即可，mac 交叉编译 0 警告 0 错。
C# 陷阱：`out var` 在 `&&` 链式条件里可能 CS0165（变量未赋值）→ 先声明 `JsonElement m1 = default` 再 `TryGetProperty("message", out m1)`。时间戳 `create_time/timestamp` 毫秒/秒自适应：`> 10_000_000_000L` 除 1000。

## 6. 验证清单

- `swift build --disable-sandbox` / `dotnet build -p:EnableWindowsTargeting=true` 0 错
- smoke test：造 4 条 chat.json（空 text、长消息、跨月、带 \n）→ 双产物生成
- EPUB：python zipfile + minidom 全过；PDF：`%PDF` 头、`/Type /Page` 计数、`%%EOF` 结尾
- C# 纯 BCL 部分可在 macOS `dotnet new console` 直接跑（WPF 依赖的跳过）
