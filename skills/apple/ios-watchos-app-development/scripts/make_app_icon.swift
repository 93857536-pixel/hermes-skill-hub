// HermesWatch 图标生成器: 深色渐变背景 + 终端提示符 ">_"
// 用法: swift make_app_icon.swift <输出.png>
// 生成 1024x1024 源图标 (注意: NSImage lockFocus 实际输出 2048x2048 @2x, 需 sips 缩放)
import AppKit
import CoreGraphics

let size = 1024.0
let image = NSImage(size: NSSize(width: size, height: size))
image.lockFocus()

let ctx = NSGraphicsContext.current!.cgContext

// 圆角矩形裁剪 (iOS 风格, 半径约 22%)
let rect = CGRect(x: 0, y: 0, width: size, height: size)
let radius = size * 0.2237
let path = CGPath(roundedRect: rect, cornerWidth: radius, cornerHeight: radius, transform: nil)
ctx.addPath(path)
ctx.clip()

// 对角渐变: 深蓝紫 -> 电光蓝
let colors = [
    NSColor(calibratedRed: 0.07, green: 0.09, blue: 0.22, alpha: 1.0).cgColor,
    NSColor(calibratedRed: 0.16, green: 0.25, blue: 0.55, alpha: 1.0).cgColor,
    NSColor(calibratedRed: 0.20, green: 0.60, blue: 0.90, alpha: 1.0).cgColor,
] as CFArray
let grad = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: colors, locations: [0.0, 0.55, 1.0])!
ctx.drawLinearGradient(grad, start: CGPoint(x: 0, y: size), end: CGPoint(x: size, y: 0), options: [])

// 细线装饰: 底部网格线
ctx.setStrokeColor(NSColor.white.withAlphaComponent(0.12).cgColor)
ctx.setLineWidth(2)
for i in 1...4 {
    let y = size * (0.12 + Double(i) * 0.08)
    ctx.move(to: CGPoint(x: size * 0.12, y: y))
    ctx.addLine(to: CGPoint(x: size * 0.88, y: y))
    ctx.strokePath()
}

// 中央终端提示符 ">_"
let text = ">_" as NSString
let font = NSFont.monospacedSystemFont(ofSize: 380, weight: .bold)
let attrs: [NSAttributedString.Key: Any] = [
    .font: font,
    .foregroundColor: NSColor.white,
]
let tsize = text.size(withAttributes: attrs)
let tpoint = NSPoint(x: (size - tsize.width) / 2, y: (size - tsize.height) / 2 - 20)
text.draw(at: tpoint, withAttributes: attrs)

// 下划线 (终端光标)
let cursorRect = CGRect(x: tpoint.x + tsize.width + 18, y: tpoint.y + 14, width: 60, height: 14)
NSColor(calibratedRed: 0.30, green: 0.90, blue: 0.95, alpha: 1.0).setFill()
NSBezierPath(roundedRect: cursorRect, xRadius: 7, yRadius: 7).fill()

image.unlockFocus()

// 保存 PNG
guard let tiff = image.tiffRepresentation,
      let rep = NSBitmapImageRep(data: tiff),
      let png = rep.representation(using: .png, properties: [:]) else {
    fatalError("生成 PNG 失败")
}
let outPath = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "AppIcon.png"
try! png.write(to: URL(fileURLWithPath: outPath))
print("已生成: \(outPath)")
