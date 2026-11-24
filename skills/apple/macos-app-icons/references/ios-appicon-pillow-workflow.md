# iOS AppIcon 程序化生成(Pillow 管线)— DeviceToolbox 2026-09-05 实战

触发: 给 iOS app 换掉纯色/占位图标,用程序化绘制出正式图标(无设计稿、无第三方绘图工具时)。与 macOS 的 icns 流程是姊妹篇,差异见下。

## iOS vs macOS 图标产物差异

| 维度 | iOS (本文件) | macOS (主 SKILL.md) |
|---|---|---|
| 母版 | 1024×1024 **PNG 单图**,无透明,全幅填满(系统裁圆角) | 1024 png → iconset → icns 十尺寸 |
| 接入 | `Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png`(Contents.json 已是 single-size 模式,通常无需改) | Resources + `CFBundleIconFile` |
| xcodegen | sources glob 含 .xcassets 即可,替换 png 后**不必** generate(资源内容变更),直接 xcodebuild | 新文件必须 generate |
| GUI 验证 | 无 Simulator.app 时: `simctl io booted screenshot` 拍 springboard/桌面 | open app / Finder |

## Pillow 绘制管线(本次用,与 Swift/AppKit 模板二选一)

- python3 自带 Pillow(本机 11.x 可用);`SIZE=1024; SS=4; canvas=1024*SS` 超采样绘制再 `resize((1024,1024), Image.LANCZOS)` —— 矢量感图形(圆/弧/圆角矩形)不超采样会出明显锯齿
- 对角渐变背景: 逐像素 `t=(x+y)/(2*S)` 线性插值两色;纯线性渐变 Pillow 无内置
- 关键绘制 API: `rounded_rectangle`(箱体/卡片)、`arc(bbox, start, end, fill, width=W)`(粗弧=提手)、`pieslice`(扇形=仪表读数)、`ellipse(outline=, width=)`(环形)、`line(..., width=)`(指针)
- Pillow 角度是屏幕坐标(0°=3 点钟,顺时针);先画再让 vision 看图判断方向对不对,别纯推理
- 圆角矩形/弧形件的外露边、深浅层次用同色系深浅两档橙即可,避免多色杂

## vision 自检迭代(必做,两轮收敛)

1. 首版画完 → `vision_analyze` 问三个问题: ①主体误读成什么(本次: 白箱体+中央表盘+4 刻度点被读成"锁具")②几何缺陷 ③像不像目标语义
2. 按误读改: 去掉"锁芯感"元素(4 个对称刻度点→ 换橙色扫掠扇区+白指针),加语义元素(两侧搭扣→ 工具箱特征),扁平极简**不加小刻度/数字**(小尺寸 60px 必糊)
3. v2 复检通过即收(glm-4v-flash 描述能力有限,能确认"无几何缺陷+构图成立"就够; 别为加细节反复迭代)

## 验证三连(全部真实执行)

1. 工程图已换: `sips -g pixelWidth -g pixelHeight AppIcon-1024.png` → 1024×1024
2. 模拟器桌面实拍: 重装 `simctl install` 后先 `simctl terminate` app(退出前台),再 `simctl io <udid> screenshot` —— 拍到的就是 springboard,能看到图标+名字真实渲染;vision 看图确认图形与设计一致
3. ipa 内图标: `unzip -l App.ipa | grep AppIcon60x60@2x`,与旧包比字节数变化(替换生效证据)

## 存档

生成脚本存项目 `docs/gen_appicon.py`(参数化配色/几何),日后改版改脚本重跑即可,30 秒出图+接入。原占位图先 cp 到 /tmp 备份再覆盖。

## 坑

- `open -a Simulator` 找不到 app 时: Xcode-beta 的路径 `/Applications/Xcode-beta.app/Contents/Developer/Applications/Simulator.app` 也可能不存在(Xcode 27 beta 无独立 Simulator GUI, 全盘 mdfind com.apple.iphonesimulator 为空)→ 放弃 GUI, 用 simctl 无头截图验证
- 图标名在 springboard 显示蓝字=刚安装待同步;显示名文案由 CFBundleDisplayName/Info.plist 控制,与图标文件无关
- file 命令 libmagic 版本不匹配会刷屏(>17 万字符)—— 校验一律用 sips/unzip/codesign,别用 file
