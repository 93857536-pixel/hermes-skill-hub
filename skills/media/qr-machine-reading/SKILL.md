---
name: qr-machine-reading
description: "Use when 需要机器读二维码(截图/网页/照片): uv venv + opencv-headless 解码配方。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [qr, opencv, screencapture, headless, alipay, agent-payment]
    related_skills: [alipay-payment-skill, ios-watchos-app-development]
---

# 屏幕/图片二维码机读 (QR Machine Reading)

从截屏、网页或照片里把二维码内容读成字符串/链接。典型场景: 扫码付款流程里把「扫码付」二维码解码喂给支付 CLI、抓取网页里展示的跳转链接、照片里的 URL 码。

## When to Use

- 需要程序化读出画面上的二维码内容（不靠人眼看）
- 扫码支付/收银台流程: 解码商户二维码后判断码型（真支付宝 vs 银行聚合，见 alipay-payment-skill 的对照表）
- 网页展示 QR、照片里的 URL/短链

## 0. 路线选择（先读）

| 路线 | 适用 | 备注 |
|---|---|---|
| **opencv-python-headless (uv venv)** ✅ 默认 | 本机解码, 无系统污染 | 2026-09-25 验证; 纯 wheel 下载, 不碰系统 Python (PEP 668) |
| zbarimg (brew) | 轻量 CLI | 需 brew, 代理死时不可装 |
| Swift + Vision framework | 原生 | **Xcode 27 beta SDK 下不可靠** (见 §4 pitfall), 稳定 SDK 上可用 |
| qreader / yolo-qr | 小码/模糊场景 | 未在本机验证, 属 ML 检测后备 |

## 1. 解码器一次性准备 (uv venv + opencv-headless)

```bash
UV=~/.hermes/bin/uv   # 本机 uv 路径; 没有则 python3 -m venv + pip 同效
$UV venv /tmp/qrvenv --python 3.11
$UV pip install --python /tmp/qrvenv/bin/python opencv-python-headless
/tmp/qrvenv/bin/python -c "import cv2; cv2.QRCodeDetector(); print('detector ready', cv2.__version__)"
```

- opencv-python-headless = 无 GUI 依赖版本, 无头 Mac 也能跑
- 用完可 `rm -rf /tmp/qrvenv`; 需要常驻就建在 ~/.venv 下

## 2. 目标画面 → PNG

```bash
# a) 指定窗口 (最干净, 不会抓到别人的终端):
WID=$(osascript -e 'tell application "Safari" to id of window 1')
screencapture -l "$WID" -o /tmp/win.png

# b) 全屏 (Retina 2x, 逻辑坐标×2):
screencapture -x /tmp/full.png          # -x 免提示音

# c) 用户给的照片/网页截图: 直接用
```

- 模拟器画面: `xcrun simctl io <UDID> screenshot /tmp/sim.png` (配合 ios-watchos-app-development)
- 网页里的码: 浏览器 computer_use 截目标区域更稳

## 3. 解码 (OpenCV QRCodeDetector)

```python
import cv2
img = cv2.imread('/tmp/win.png')
det = cv2.QRCodeDetector()
for scale in (1, 2, 3):   # 小码逐级放大重试
    im = img if scale == 1 else cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    ok, data, pts = det.detectAndDecode(im)   # cv2>=4 一律三元组
    if ok:
        print('QR:', data)
        break
```

要点:
- **先裁感兴趣区域再解**比全图解快且准 (QR 占全图 <5% 时全图直解常失败; 裁 Retina 图时逻辑坐标×2)
- 放大 2-3x + INTER_CUBIC 对小码/压缩图成功率显著提升
- `libpng warning: iCCP: extra compressed data` 是 png 元数据噪音, 忽略
- 多个码: 用 detect 的 points 分组逐个裁剪再解

## 4. 踩坑 (2026-09-25 实测)

- **Xcode 27 beta SDK 下 Swift+Vision 编译失败**: `import Vision` 能过但 `VNDetectQRCodeRequest` 等符号解析为空 (swiftmodule 暴露异常); 换 `-sdk macosx`、显式 `-F/-framework` 均无效, 最小复现 `import Vision; VNDetectQRCodeRequest()` 也炸。属 beta SDK 环境问题 (非永久结论, 稳定版 Xcode 大概率正常) — 当下直接走 opencv 路线, 别在 Vision 上耗时间。
- **screencapture 全屏会抓到错误窗口** (前台是终端时, 浏览器里的对话框被遮住) — 永远优先 `screencapture -l <wid>` 窗口级截取。
- **Retina 2x 坐标换算**: 逻辑坐标 (x,y) → 像素 (2x, 2y)。裁剪框忘乘 2 是最常见误。
- **解码成功 ≠ 码类型对**: 支付宝生态里 `qr.95516.com` 是银行聚合扫码码 (302 跳招行 multiPay/银联), 真支付宝码是 `qr.alipay.com` / cashier 链接。AI 代付只认真支付宝载荷 — 解出来先判码型再决定喂给谁。
- **cv2 5.x 三元组**: 老教程里 `s, d = det.detect(img)` 二元解包在 OpenCV 5.0 会报错, 用三元组。

## 5. 验证

- 已知内容测试码: `qrcode` (pip, 生成库, 与 headless 解码器同 venv 共存) 生成含固定字符串的测试图, 解码比对
- 现场验证: 解出的字符串与画面人眼可见的前缀/域名一致
