#!/usr/bin/env python3
"""Pillow 生成 iOS AppIcon 模板 (DeviceToolbox 实测, 2026-09-05)
用法: 改几何/配色后 python3 gen_appicon_pillow.py -> /tmp/dt_icon_1024.png
关键要点:
- 超采样 SS=4 抗锯齿, 最后 resize 1024 LANCZOS
- RGB 无 alpha (actool/App Store 校验要求)
- 出图后用 vision_analyze 自检构图再接入工程
接入: cp 覆盖 <proj>/Sources/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png
      (单图 1024 的 Contents.json 无需改) -> 重建 -> simctl 验证
"""
from PIL import Image, ImageDraw
import math

SS = 4            # 超采样倍数
S = 1024 * SS     # 工作画布
OUT = 1024

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

# 品牌对角渐变: 左上亮 -> 右下深 (DeviceToolbox 橙 #FFB340 -> #FF5E00)
C_TOP = (255, 179, 64)
C_BOT = (255, 94, 0)
img = Image.new("RGB", (S, S))
px = img.load()
for y in range(S):
    for x in range(S):
        t = (x + y) / (2 * S)
        px[x, y] = lerp(C_TOP, C_BOT, t)

d = ImageDraw.Draw(img)
WHITE = (255, 255, 255)
ORANGE_D = (255, 94, 0)
ORANGE_L = (255, 179, 64)
CX = S // 2

# 提手弧: Pillow 角度 0°=3 点钟方向, y 向下; 上半圈 180->360 实测正确
HANDLE_R, HANDLE_W = 190 * SS, 78 * SS
box_top = 500 * SS
bbox = (CX - HANDLE_R, box_top - HANDLE_R, CX + HANDLE_R, box_top + HANDLE_R)
d.arc(bbox, start=180, end=360, fill=WHITE, width=HANDLE_W)

# 箱体
body = (226 * SS, 496 * SS, 798 * SS, 806 * SS)
d.rounded_rectangle(body, radius=64 * SS, fill=WHITE)

# 扇区仪表 (pieslice) + 指针 + 轴心
dial_c = (CX, 650 * SS)
dial_r = 104 * SS
d.ellipse((dial_c[0]-dial_r, dial_c[1]-dial_r, dial_c[0]+dial_r, dial_c[1]+dial_r), fill=WHITE)
d.ellipse((dial_c[0]-dial_r, dial_c[1]-dial_r, dial_c[0]+dial_r, dial_c[1]+dial_r),
          outline=ORANGE_D, width=16 * SS)
start_deg, sweep = -135, 252
d.pieslice((dial_c[0]-dial_r+24*SS, dial_c[1]-dial_r+24*SS,
            dial_c[0]+dial_r-24*SS, dial_c[1]+dial_r-24*SS),
           start=start_deg, end=start_deg + sweep, fill=ORANGE_L)
end_deg = math.radians(start_deg + sweep)
pl = dial_r - 40 * SS
p2 = (dial_c[0] + pl * math.cos(end_deg), dial_c[1] + pl * math.sin(end_deg))
d.line([dial_c, p2], fill=WHITE, width=26 * SS)

out = img.resize((OUT, OUT), Image.LANCZOS)
out.save("/tmp/dt_icon_1024.png")
print("saved /tmp/dt_icon_1024.png")
