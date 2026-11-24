---
name: cloud-backup-tarballs
version: 1.0.0
description: "把多项目目录备份到夸克/阿里云盘。文件数>5000时先打tar.gz再上传,别逐文件传。"
tags: [backup, quark-drive, aliyun, tusdk]
---

# Cloud Backup Tarballs

把本地目录备份到云盘的标准工作流。**核心约束：文件数 >~5000 时必须先打压缩包**，否则 CLI 逐文件秒传判定会慢到几十分钟只传 1%（实测 13402 文件 54min 仅 1%）。

## When to Use

- 用户要求"把某目录/多个项目备份到夸克网盘/阿里云盘"
- 目标目录含 `.git`、`node_modules`、`target/`、`.build/` 等大文件数目录

## Workflow

### 1. 评估规模

```bash
find <dir> -type f | wc -l
du -sh <dir>
```

- 文件数 ≤ 5000 → 直接走 CLI `upload` 命令
- 文件数 > 5000 → **必须先打包成 tar.gz**

### 2. 确定排除规则

| 语言/框架 | 常见构建产物 | .git |
|-----------|-------------|------|
| Rust/Tauri | `target/`、`.build/` | **保留** |
| Node/React | `node_modules/`、`dist/` | **保留** |
| iOS/Swift | `Build/`、`DerivedData/` | **保留** |
| Android/Gradle | `.gradle/`、`app/build/` | **保留** |

**默认保留 `.git`**：用户要可恢复的完整备份；源码仓库本身小且能随时 `git fetch` 重建，但 `.git` 里的历史 commit 不可再生（GitHub 可能删 commit）。

### 3. 打压缩包（每个项目一个）

```bash
SRC_DIR=<source-dir>
PREFIX=<backup-prefix>
OUTDIR="/tmp/${PREFIX}-packs"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$OUTDIR/$PREFIX-$TIMESTAMP"

EXCLUDES=(target .build node_modules Build .gradle DerivedData __pycache__ ".DS_Store")

for d in "$SRC_DIR"/*/; do
    name=$(basename "$d")
    out="$OUTDIR/$PREFIX-$TIMESTAMP/${name}.tar.gz"
    exclude_args=()
    for ex in "${EXCLUDES[@]}"; do
        exclude_args+=("--exclude=$ex")
    done
    echo "--- packaging $name ..."
    tar czf "$out" "${exclude_args[@]}" -C "$d" .
done
echo "Done: $(ls "$OUTDIR/$PREFIX-$TIMESTAMP/"*.tar.gz | wc -l) archives"
du -sh "$OUTDIR/$PREFIX-$TIMESTAMP"
```

**验证源码完整性**：

```bash
for f in "$OUTDIR/$PREFIX-$TIMESTAMP/"*.tar.gz; do
    n=$(tar -tzf "$f" | grep -cE "\.(swift|rs|ts|tsx|js|py|go|java|cs|kt)$")
    sz=$(ls -lh "$f" | awk '{print $5}')
    echo "$(basename $f): 源码 $n 个, $sz"
done
```

### 4. 上传压缩包

**夸克网盘**（session-input 必须传用户原始提问）：

```bash
cd ~/.hermes/skills/quarkclouddrive
SESSION_ID="<unix_timestamp>-<6-char-random>"
node scripts/quark-drive.cjs upload /tmp/<prefix>-packs/<timestamp-dir> \
  --session-input "<用户原始提问原文>" \
  --session-id "$SESSION_ID"
```

- 后台跑 + `notify_on_complete: true` 监听
- 返回 `"successCount": N` = 成功上传的压缩包数
- 断点续传支持：中断后重跑同一命令即 resume
- CLI 用 `upload list --state <state>` 查进度

**⚠️ iLink 坑**：CLI 的 `"Sent"` 只是入队回执，不代表真投递；必须 grep gateway.log 看是否有 `"Delivering ... MEDIA attachment"` 行才算成功。≥5MB 文件走 iLink 不稳，大文件优先走 GitHub Release 附件或网盘。限流滚动 30s：**只发一次**，连环重试会顶起冷却计时器。

### 5. 验证 & 清理

```bash
# 搜索确认落地
node scripts/quark-drive.cjs search --keyword "<project>-backup.tar.gz" \
  --session-input "..." --session-id "<same>" 2>&1 | grep -o '"fileName":"[^"]*"'

# 清理本地临时包
rm -rf /tmp/<prefix>-packs
```

## Pitfalls

1. **不要用 rsync/递归上传**：CLI 对大量小文件的哈希+秒传判定约 10x 于实际传输时间，总耗时远超直接传包。
2. **不要默认排除 `.git`**：除非用户明确说"只要源码别带 git"。`.git` 占大头但不可再生；target/.build 一编译就回来。
3. **不要假设"Sent"=成功**：CLI 和微信网关都是异步的，务必看日志里的 Delivering 行。
4. **分块大小**：tar.gz 超过 2GB 时 CLI 会自动切成 shard，但仍应显示 successCount 匹配压缩包数量。