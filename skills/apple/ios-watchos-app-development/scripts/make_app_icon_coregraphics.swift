import CoreGraphics
import CoreText
import ImageIO
import Foundation

// Headless-safe app icon generator (pure CoreGraphics + CoreText, no AppKit /
// NSImage.lockFocus — lockFocus can render blank when no GUI session is attached).
//
// Usage: swift make_app_icon_coregraphics.swift [out.png]
// Default output: AppIcon.png (1024x1024, dark gradient + centered glyph).
//
// Verified 2026-08-30 (WeChatExporterMonitor iOS app icon).
let W = 1024
let H = 1024
let cs = CGColorSpaceCreateDeviceRGB()
let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8,
                    bytesPerRow: 0, space: cs,
                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!

// vertical gradient background (dark navy)
let colors = [
    CGColor(red: 0.07, green: 0.09, blue: 0.15, alpha: 1),
    CGColor(red: 0.15, green: 0.30, blue: 0.52, alpha: 1),
] as CFArray
let grad = CGGradient(colorsSpace: cs, colors: colors, locations: [0, 1])!
ctx.drawLinearGradient(grad, start: CGPoint(x: 0, y: 0),
                       end: CGPoint(x: CGFloat(W), y: CGFloat(H)), options: [])

// centered glyph text (edit label / font / size to taste)
let label = "WX"
let font = CTFontCreateWithName("Helvetica-Bold" as CFString, 340, nil)
let attr = [
    kCTFontAttributeName: font,
    kCTForegroundColorAttributeName: CGColor(red: 1, green: 1, blue: 1, alpha: 1),
] as CFDictionary
let str = CFAttributedStringCreate(nil, label as CFString, attr)!
let line = CTLineCreateWithAttributedString(str)
let bounds = CTLineGetImageBounds(line, ctx)
ctx.textPosition = CGPoint(
    x: (CGFloat(W) - bounds.width) / 2 - bounds.minX,
    y: (CGFloat(H) - bounds.height) / 2 - bounds.minY
)
CTLineDraw(line, ctx)

let img = ctx.makeImage()!
let out = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "AppIcon.png"
let url = URL(fileURLWithPath: out) as CFURL
let dest = CGImageDestinationCreateWithURL(url, "public.png" as CFString, 1, nil)!
CGImageDestinationAddImage(dest, img, nil)
CGImageDestinationFinalize(dest)
print("wrote", url)
