#!/usr/bin/env bash
# download-release-asset.sh — github.com 直连抖动时,经 API 资产端点全量下载并核验
# 用法: bash download-release-asset.sh <owner/repo> <tag> <asset_name> <local_build_path>
# 原理: repos/.../releases/assets/<id> 端点 + Accept: application/octet-stream → 302 到
#       release-assets.githubusercontent.com 拿完整二进制(不经过 github.com 网页/HTTPS 直连)。
# 教训(2026-10 实测): 不带 Accept 头时该端点静默返回 ~1.7KB JSON 元数据,HTTP 仍 200——
#       必须用 size + sha256 与本地构建比对,HTTP 200 不算数。
set -eu
OWNER_REPO="${1:?owner/repo}"; TAG="${2:?tag}"; ASSET="${3:?asset name}"; LOCAL="${4:?local build path}"

ASSET_URL=$(gh api "repos/$OWNER_REPO/releases/tags/$TAG" --jq '.assets[] | select(.name=="'"$ASSET"'") | .url' | tr -d '"' | head -1)
echo "asset url: $ASSET_URL"

curl -fsSL -H "Accept: application/octet-stream" -o /tmp/.asset_check.bin "$ASSET_URL"
RSZ=$(stat -f %z /tmp/.asset_check.bin); LSH=$(shasum -a 256 "$LOCAL" | cut -d' ' -f1); RSH=$(shasum -a 256 /tmp/.asset_check.bin | cut -d' ' -f1)
LSZ=$(stat -f %z "$LOCAL")

echo "local:  ${LSZ}B  $LSH"
echo "remote: ${RSZ}B  $RSH"
if [ "$LSZ" = "$RSZ" ] && [ "$LSH" = "$RSH" ]; then
  echo "VERIFIED: remote asset == local build"
else
  echo "MISMATCH: remote asset differs from local build"
  exit 1
fi
rm -f /tmp/.asset_check.bin
