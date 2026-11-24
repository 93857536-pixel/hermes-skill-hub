# 程序化图标管线:无 PIL 环境的坑与解法(2026-08 MediaConverter 实战)

背景:机器直连网络受限,pip/brew 均不可用 → 图标绘制走 Swift/AppKit 离屏
(NSBitmapImageRep),全程零第三方依赖。完整可运行示例:
`~/Projects/MediaConverter/scripts/make_icon.swift`(渐变圆角底 + 双弧箭头环 + 圆角播放三角 + 波形柱;一次产出 macOS icns/appiconset + Windows ico/打包 Logo)。

## 1. 阴影:别用 CIGaussianBlur + draw(at:from:)
CIGaussianBlur 输出 extent 每侧扩 ~3×radius(radius=10 → 图变 ~1084×1084,原点 -30,-30)。
再 `draw(at:from: NSRect(0,0,1024,1024))` 会取错区域 → 阴影偏移到错误一侧,视觉上像
"右上角白色模糊污点"(实测被视觉模型两次误报为异物)。可靠写法:字形画进独立 NSImage,主画布画两次:

```swift
glyph.draw(at: NSPoint(x: 0, y: -16), from: NSRect(x:0,y:0,width:S,height:S), operation: .sourceOver, fraction: 0.28) // 投影
glyph.draw(at: .zero,          from: NSRect(x:0,y:0,width:S,height:S), operation: .sourceOver, fraction: 1.0)  // 本体
```

## 2. 当前 SDK 编译坑
- `NSImage(size:) { }` 是错的:签名是 `init(size:flipped:drawingHandler:)` → `NSImage(size: NSSize(...), flipped: false) { _ in ...; return true }`
- `CIContext()` 返回**非可选**,不能 `guard let ctx = CIContext()`

## 3. 无 PIL 生成多尺寸 .ico(内嵌 PNG,Vista+ 支持)
手写容器:ICONDIR(6B: reserved/type/count) + 每尺寸 ICONDIRENTRY(16B) + 各尺寸 PNG blob。
entry 关键字段:width/height(256 写 0x00)、planes=1、bitcount=32、size=PNG 长度、offset 从 6+16N 起累加。
Swift 实现要点:小端字节手拼 `Data.append(contentsOf:)`;验证:读前 6B,`count = UInt16(head[4..6])`。

## 4. 循环箭头环几何(AppKit 角度约定)
- `NSBezierPath.appendArc(withCenter:radius:startAngle:endAngle:clockwise:)`:0°=+x,逆时针为正(y-up)
- 两段弧留缺口(左/右各 ~64° 缺口,上/下为完整弧),箭头画在每段弧**终点**,方向 = 逆时针切线:
  `t = (endAngle+90)°`;apex = 圆心 + ringR·(cosθ, sinθ);base = apex − tang·L;两翼 = base ± perp·L·0.55
- 圆角播放三角:三顶点闭合 path + `lineWidth`(≈56)粗描边 + `.round` join/cap —— 比手算圆角多边形简单
- 波形柱:`roundedRect` radius = 宽/2 → 圆头胶囊
- **布局先算坐标再渲染**:三角右缘 < 第一根柱左缘(留 ≥20px),柱右缘 < 环内缘(ringR − stroke/2),否则重叠/越界(本会话初版即踩:柱落在三角包围盒内被吞掉,视觉模型报"只见两根柱")

## 5. vision 校验不可用时的确定性兜底
vision_analyze 可能 400(aux 视觉模型临时拒绝 image_url,报 `unknown variant 'image_url'`)。改用程序化校验(全部离线可跑):
- PNG 尺寸:读 IHDR bytes 16..24,大端 `>II`(纯 Python 即可,无需 PIL)
- icns 有效性:`iconutil -c iconset AppIcon.icns -o /tmp/x.iconset` 后数文件,应为 10
- ico 条目数:读前 6B `struct.unpack("<H", head[4:6])`
- 沙盒 `file` 命令 libmagic 版本不匹配会刷 17 万字垃圾(已知坑),别用它校验

## 6. 与工程联动
- xcodegen 项目:Assets.xcassets 放进 sources 目录自动收;`ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon` 于 project.yml settings.base;新文件落盘后必须重跑 `xcodegen generate`
- Windows 打包 Logo(Square44/150/310 + Wide310x150)从方形母版缩放,wide 版取中心横带裁剪即可
