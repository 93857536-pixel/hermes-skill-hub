// macOS App 图标 1024 母版绘制模板
// 用法: swift icon_drawer.swift   (改下方"主体图形"段即可)
// 输出: 当前目录 AppIcon.png
// 之后: bash scripts/make_icns.sh AppIcon.png AppIcon.icns
// 环境: 需 Xcode/CommandLineTools 的 swift(/usr/bin/swift)
import AppKit

let S: CGFloat = 1024
let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: Int(S), pixelsHigh: Int(S),
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
    colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
rep.size = NSSize(width: S, height: S)

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)

// ===== 背景: squircle + 渐变(Big Sur 风格圆角 ~22%) =====
let bg = NSBezierPath(roundedRect: NSRect(x: 0, y: 0, width: S, height: S),
                      xRadius: 230, yRadius: 230)
let grad = NSGradient(colors: [
    NSColor(calibratedRed: 0.16, green: 0.35, blue: 0.98, alpha: 1), // 主色1
    NSColor(calibratedRed: 0.48, green: 0.24, blue: 0.93, alpha: 1)  // 主色2
])!
grad.draw(in: bg, angle: -58)

// 可选: 左上柔光
let glow = NSGradient(colors: [
    NSColor(calibratedWhite: 1.0, alpha: 0.16),
    NSColor(calibratedWhite: 1.0, alpha: 0.0)])!
glow.draw(in: NSBezierPath(ovalIn: NSRect(x: 60, y: 560, width: 560, height: 560)),
          relativeCenterPosition: NSPoint(x: 0, y: 0))

// ===== 主体图形: 在此绘制(白色学士帽 + 金色闪电是 TianXueBot 案例) =====
// 常用 API:
//   多边形填充: let p = NSBezierPath(); p.move(to:); p.line(to:); p.close(); color.setFill(); p.fill()
//   描边:      p.lineWidth = 11; p.lineCapStyle = .round; color.setStroke(); p.stroke()
//   曲线:      p.curve(to: NSPoint, controlPoint1: NSPoint, controlPoint2: NSPoint)
//   阴影感:    先画偏移 (0, +9) 的半透明深色副本,再画本体
// 示例: 中心白色圆
NSColor.white.setFill()
NSBezierPath(ovalIn: NSRect(x: 312, y: 312, width: 400, height: 400)).fill()

NSGraphicsContext.restoreGraphicsState()

let data = rep.representation(using: .png, properties: [:])!
try! data.write(to: URL(fileURLWithPath: "AppIcon.png"))
print("OK -> AppIcon.png")
