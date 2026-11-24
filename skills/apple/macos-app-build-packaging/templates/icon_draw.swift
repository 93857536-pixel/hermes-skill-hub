import AppKit

// macOS App 图标母版绘制模板 (已实测产出视觉验收通过的图标)
// 用法: swift /tmp/icon_draw.swift -> 输出 1024x1024 PNG
// 改造型: 调整第 3/4 节的坐标与颜色即可
// 输出目录按需修改(outDir)
let S: CGFloat = 1024

let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: Int(S), pixelsHigh: Int(S),
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
    colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
rep.size = NSSize(width: S, height: S)

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
let ctx = NSGraphicsContext.current!.cgContext
ctx.setAllowsAntialiasing(true)

// ---------- 1. 背景: 圆角方块 + 渐变 (Big Sur 风格半径 ~22.5%) ----------
let bgRect = NSRect(x: 0, y: 0, width: S, height: S)
let bgPath = NSBezierPath(roundedRect: bgRect, xRadius: 230, yRadius: 230)
let c1 = NSColor(calibratedRed: 0.16, green: 0.35, blue: 0.98, alpha: 1.0)
let c2 = NSColor(calibratedRed: 0.48, green: 0.24, blue: 0.93, alpha: 1.0)
let grad = NSGradient(colors: [c1, c2])!
grad.draw(in: bgPath, angle: -58)

// ---------- 2. 左上柔和高光 ----------
let glow = NSGradient(colors: [
    NSColor(calibratedWhite: 1.0, alpha: 0.16),
    NSColor(calibratedWhite: 1.0, alpha: 0.0)
])!
let glowPath = NSBezierPath(ovalIn: NSRect(x: 60, y: 560, width: 560, height: 560))
glow.draw(in: glowPath, relativeCenterPosition: NSPoint(x: 0, y: 0))

// ---------- 3. 主体图形示例: 学士帽 (白色) ----------
let accent = NSColor(calibratedRed: 0.98, green: 0.72, blue: 0.15, alpha: 1.0) // 金色
NSColor.white.setFill()

let board = NSBezierPath()  // 帽顶菱形板
board.move(to: NSPoint(x: 512, y: 505))
board.line(to: NSPoint(x: 742, y: 425))
board.line(to: NSPoint(x: 512, y: 345))
board.line(to: NSPoint(x: 282, y: 425))
board.close()
board.fill()

let skull = NSBezierPath()  // 帽身(下沿微弧)
skull.move(to: NSPoint(x: 356, y: 421))
skull.line(to: NSPoint(x: 668, y: 421))
skull.line(to: NSPoint(x: 594, y: 330))
skull.curve(to: NSPoint(x: 430, y: 330),
            controlPoint1: NSPoint(x: 556, y: 300),
            controlPoint2: NSPoint(x: 468, y: 300))
skull.close()
skull.fill()

accent.setFill()
let button = NSBezierPath(ovalIn: NSRect(x: 512 - 14, y: 505 - 14, width: 28, height: 28))
button.fill()

let tassel = NSBezierPath()  // 流苏
tassel.lineWidth = 11
tassel.lineCapStyle = .round
tassel.move(to: NSPoint(x: 512, y: 512))
tassel.curve(to: NSPoint(x: 668, y: 462),
             controlPoint1: NSPoint(x: 556, y: 522),
             controlPoint2: NSPoint(x: 602, y: 472))
tassel.line(to: NSPoint(x: 690, y: 392))
accent.setStroke()
tassel.stroke()
let tip = NSBezierPath()
tip.move(to: NSPoint(x: 690, y: 404))
tip.line(to: NSPoint(x: 704, y: 388))
tip.line(to: NSPoint(x: 690, y: 372))
tip.line(to: NSPoint(x: 676, y: 388))
tip.close()
tip.fill()

// ---------- 4. 副图形示例: 闪电 (金色, 带投影) ----------
func boltPath(ox: CGFloat, oy: CGFloat) -> NSBezierPath {
    let p = NSBezierPath()
    p.move(to: NSPoint(x: 512 + 30 + ox, y: 322 + oy))
    p.line(to: NSPoint(x: 512 - 52 + ox, y: 227 + oy))
    p.line(to: NSPoint(x: 512 - 8 + ox, y: 227 + oy))
    p.line(to: NSPoint(x: 512 - 38 + ox, y: 132 + oy))
    p.line(to: NSPoint(x: 512 + 58 + ox, y: 259 + oy))
    p.line(to: NSPoint(x: 512 + 12 + ox, y: 259 + oy))
    p.close()
    return p
}
NSColor(calibratedRed: 0.80, green: 0.35, blue: 0.05, alpha: 0.45).setFill()
boltPath(ox: 0, oy: 9).fill()
accent.setFill()
boltPath(ox: 0, oy: 0).fill()

NSGraphicsContext.restoreGraphicsState()

// ---------- 输出 PNG ----------
let data = rep.representation(using: .png, properties: [:])!
let outURL = URL(fileURLWithPath: "/tmp/AppIcon.png")  // 按需改输出路径
try! data.write(to: outURL)
print("OK -> \(outURL.path) (\(data.count) bytes)")
