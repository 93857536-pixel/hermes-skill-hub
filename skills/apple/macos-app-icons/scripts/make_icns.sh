#!/bin/bash
# 用法: make_icns.sh <master.png> <output.icns>
# 由 1024 母版生成全尺寸 iconset 并打包 .icns,自动往返校验 10 个尺寸。
# 依赖: sips + iconutil(macOS 自带)。
set -euo pipefail

MASTER="${1:?需要 master.png 路径(建议 1024x1024)}"
OUT="${2:?需要输出 .icns 路径}"
[ -f "$MASTER" ] || { echo "错误: 找不到 $MASTER"; exit 1; }

TMP="$(mktemp -d)/AppIcon.iconset"
mkdir -p "$TMP"

sips -z 16   16   "$MASTER" --out "$TMP/icon_16x16.png"      >/dev/null
sips -z 32   32   "$MASTER" --out "$TMP/icon_16x16@2x.png"   >/dev/null
sips -z 32   32   "$MASTER" --out "$TMP/icon_32x32.png"      >/dev/null
sips -z 64   64   "$MASTER" --out "$TMP/icon_32x32@2x.png"   >/dev/null
sips -z 128  128  "$MASTER" --out "$TMP/icon_128x128.png"    >/dev/null
sips -z 256  256  "$MASTER" --out "$TMP/icon_128x128@2x.png" >/dev/null
sips -z 256  256  "$MASTER" --out "$TMP/icon_256x256.png"    >/dev/null
sips -z 512  512  "$MASTER" --out "$TMP/icon_256x256@2x.png" >/dev/null
sips -z 512  512  "$MASTER" --out "$TMP/icon_512x512.png"    >/dev/null
sips -z 1024 1024 "$MASTER" --out "$TMP/icon_512x512@2x.png" >/dev/null

iconutil -c icns "$TMP" -o "$OUT"

# 往返校验: 解包应得到 10 个尺寸文件
V="$(mktemp -d)/verify.iconset"
iconutil -c iconset "$OUT" -o "$V" 2>/dev/null
N=$(ls "$V" | wc -l | tr -d ' ')
if [ "$N" -eq 10 ]; then
  echo "OK: $OUT ($(du -h "$OUT" | cut -f1), 10 尺寸校验通过)"
else
  echo "FAIL: 校验只得到 $N 个尺寸"; exit 1
fi
