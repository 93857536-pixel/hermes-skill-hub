#!/bin/bash
# sim-live-watch.sh — 实时监听 iOS 源码, 自动增量编译+安装+重启模拟器里的 App
# 用法: sim-live-watch.sh <PROJECT_DIR> <SCHEME> <APP_BUNDLE_ID> <SIM_UDID> [EXTERNAL_DD]
# 原理: macOS 自带 find -newer 轮询(2s), 无需 fswatch/brew
# 产物(建议 gitignore): <PROJECT>/.live-review-dd/ .live-review-marker .live-review-events.log .live-review-build.log
set -u
PROJECT="$1"; SCHEME="$2"; BID="$3"; SIM="$4"; DD="${5:-$PROJECT/.live-review-dd}"
MARKER="$PROJECT/.live-review-marker"
BUILDLOG="$PROJECT/.live-review-build.log"
EVENTS="$PROJECT/.live-review-events.log"
touch "$MARKER"

# 初始基线构建
echo "[watch] initial build starting..."
xcodebuild -project "$PROJECT/$SCHEME.xcodeproj" -scheme "$SCHEME" \
  -destination "platform=iOS Simulator,id=$SIM" -configuration Debug \
  -derivedDataPath "$DD" build > "$BUILDLOG" 2>&1
echo "[watch] initial build exit=$?" >> "$BUILDLOG"

while :; do
  CHANGED=$(find "$PROJECT/Sources" -type f -newer "$MARKER" 2>/dev/null)
  if [ -n "$CHANGED" ]; then
    N=$(echo "$CHANGED" | wc -l | tr -d ' ')
    echo "[$(date '+%H:%M:%S')] $N file(s) changed -> building" >> "$EVENTS"
    if xcodebuild -project "$PROJECT/$SCHEME.xcodeproj" -scheme "$SCHEME" \
      -destination "platform=iOS Simulator,id=$SIM" -configuration Debug \
      -derivedDataPath "$DD" build > "$BUILDLOG" 2>&1; then
      APP="$DD/Build/Products/Debug-iphonesimulator/$SCHEME.app"
      xcrun simctl terminate "$SIM" "$BID" 2>/dev/null
      xcrun simctl install "$SIM" "$APP" >> "$BUILDLOG" 2>&1
      xcrun simctl launch "$SIM" "$BID" >> "$BUILDLOG" 2>&1
      touch "$MARKER"
      echo "[$(date '+%H:%M:%S')] build+install+launch OK" >> "$EVENTS"
    else
      echo "[$(date '+%H:%M:%S')] BUILD FAILED (see $BUILDLOG)" >> "$EVENTS"
      # 失败不更新 marker, 修好后自动重试; sleep 拉长避免空转
      sleep 10
    fi
  fi
  sleep 2
done
