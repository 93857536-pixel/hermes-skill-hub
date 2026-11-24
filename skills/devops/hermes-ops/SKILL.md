---
name: hermes-ops
description: "Hermes 运维:备份/退出自动备份/权限。Use when backing up Hermes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hermes, backup, hooks, permissions, sudo, quark]
---

# Hermes 运维 (hermes-ops)

本机已验证的 Hermes 维护流程: 全量备份、夸克云备份、退出自动备份(hooks)、权限提升。2026-08 在 macOS 上完整跑通。

**触发时机**: 用户要求备份 Hermes / 配置"退出时自动做 X" / 提升 agent 权限。

## 1. 全量备份打包

包含(关键项): `config.yaml`(+重要 .bak)、`.env`(密钥)、`auth.json`(授权)、`SOUL.md`、`memories/`、`hindsight/`、`skills/`(含各 skill 授权,如 quark config.json 带 token)、`cron/`、`state.db`(会话库)、`sessions/`、`logs/`、`hooks/`。

排除(可重装/缓存): `hermes-agent/`(源码 2.5G)、`cache/`、`audio_cache/`、`bin/`、`lsp/`。

```bash
mkdir -p ~/hermes-backup-$(date +%Y%m%d-%H%M%S)
tar -czf ~/hermes-backup-$(date +%Y%m%d-%H%M%S)/hermes-full.tar.gz \
  -C ~ .hermes/config.yaml .hermes/config.yaml.bak.* .hermes/.env .hermes/auth.json \
  .hermes/SOUL.md .hermes/memories .hermes/hindsight .hermes/skills \
  .hermes/cron .hermes/state.db .hermes/state.db-shm .hermes/state.db-wal \
  .hermes/sessions .hermes/logs .hermes/hooks 2>/dev/null
# 验证: tar -tzf <包> | wc -l
```

**体积会随 state.db 膨胀,别用旧数字估**:2026-08 打包 ~21-24MB;2026-10 state.db 已 ~500MB、打包 ~248MB。打包前先 `du -sh ~/.hermes/state.db`。>100MB 时走 §6 分片 + ECS 中继路线,且**整包 tar.gz 不要 commit 进 git 历史**——仓历史里任何单文件 >100MB 都会被 GitHub pre-receive 直接拒绝(实测 248MB 整包在历史里=push rejected;清出整包后 4×80MB 分片顺利推上,分片只触发 LFS 建议警告不阻断;以后默认按 40MB 分片(全程零警告),详见 §6)。含 shm/wal 保证会话库完整(打包前最好停掉活跃 hermes 会话,否则接受快照近似)。备份含 API keys——仅存私人网盘/私有仓,提醒用户。

## 2. 上传到夸克网盘(quarkclouddrive CLI)

1. 前置: `bash <skill_dir>/scripts/install.sh` 检查环境(每次调用前)
2. **cwd 必须在 skill 目录**(CLI 相对路径读 config.json)
3. 公共参数: `--session-id "{timestamp}-{random}"`(同对话复用)、`--session-input "用户原始提问"`
4. 建分类文件夹(幂等,同名返回已有 FID): `create-folder --dir-path "备份" --parent-fid "0"`
5. 上传: `upload <tar> --parent-fid <FID>`
6. 成功判定: result 行 `code:0` + `fullPath`(如 `夸克网盘/备份`)
7. 坑位与能力边界: 见 `references/quark-cli-pitfalls.md`

## 3. 退出 Hermes 自动备份(shell hooks)

- **事件**: `on_session_end`(由 turn_finalizer 发出,payload 经 **stdin** JSON 传给脚本;stdout JSON 可选)
- 其他事件: `on_session_start`、`on_session_finalize`、`pre/post_tool_call`、`pre/post_llm_call`、`subagent_stop` 等
- **配置位置**: `~/.hermes/config.yaml` 的 `hooks:` 块
- **⚠️ `hermes config set` 不支持嵌套结构**(会把列表写成字符串导致 hook 不被识别)——hooks 列表必须用 venv python + yaml 写入:

```python
import yaml
p = '~/.hermes/config.yaml'  # 展开
with open(p) as f: cfg = yaml.safe_load(f)
cfg['hooks'] = {'on_session_end': [{'command': '/path/to/script.sh', 'timeout': 180}]}
with open(p, 'w') as f: yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
```

- **allowlist 授权**: `~/.hermes/shell-hooks-allowlist.json` 写入 `{"approvals": [{"event": "on_session_end", "command": "/path/script.sh"}]}`。未授权时 `hooks test` 能跑但真实事件不触发;`hermes hooks list` 显示 `✓ allowed` 才算就绪
- **timeout 要够**: 备份类脚本含上传,设 180s(默认值可能太短)
- **脚本要点**: 幂等、内部 log 错误并 exit 0(备份失败不拖垮会话结束)、本地保留最近 7 份自动清理
- 验证三步: `hermes hooks list`(识别+allowed)→ `hermes hooks test <event>`(exit code)→ 手动跑脚本本体确认真实行为

本机已部署: `~/bin/hermes-auto-backup.sh`(打包→上传夸克"备份"分类→本地留 7 份→日志 `~/Library/Logs/hermes-backup.log`)。

### 备份中断诊断与补传(2026-08 实测)

**日志特征**: 某次日志停在"打包完成: xxx.tar.gz"后**既无"上传成功"也无"上传失败"** = node 上传进程被会话结束/中断杀掉(不是上传失败)——网盘上没有该文件、进程列表里也没有残留。tar 打包成功只说明本地 OK,上传是独立步骤,可能被截断。

**诊断三步**:
1. `tail` 日志找"打包完成"后无结果的最后一条
2. `ps aux | grep -i quark` 确认无残留进程
3. 夸克侧 search 确认文件不在网盘(CLI: `node scripts/quark-drive.cjs search --keyword <时间戳>`)

**补传**: 直接复用脚本里的 `QUARK_BACKUP_FID`(备份分类 FID):
```bash
cd ~/.hermes/skills/quarkclouddrive
node scripts/quark-drive.cjs upload ~/hermes-backups/<file>.tar.gz \
  --parent-fid "<QUARK_BACKUP_FID>" --session-id "$(date +%s)-$(openssl rand -hex 3)"
# 成功: result 行 code:0 + fullPath"夸克网盘/备份";再 search 确认
```

**hook 触发过频观察**: 连续多个会话结束时,on_session_end hook 可能 1-2 分钟触发一次(每次 30M 打包上传),属正常但浪费;如用户不需要这么密,可在脚本头部加节流(距上次成功上传 <10 分钟则跳过,读日志最后时间戳判断)。

## 4. 权限提升

- **命令免审**: `approvals.mode: off` 跳过所有危险命令审批(等价 `--yolo`);`smart` 是默认中档(低风险自动放行)
- **sudo 免密**(已验证): 
  ```bash
  echo "<user> ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/<user>
  chmod 440 /etc/sudoers.d/<user>
  visudo -c -f /etc/sudoers.d/<user>   # 语法校验 parsed OK
  # 验证: sudo -n true
  ```
- **密钥脱敏** (`security.redact_secrets`): 设计上会话中途关闭不生效(防 LLM 自关),不推荐关

## 5. 验证清单

- 备份包: `tar -tzf` 确认条目数与关键文件
- 上传: result 行 `successCount` / `fullPath`
- hooks: `hermes hooks list` → `✓ allowed`
- sudo: `sudo -n true`

## 6. 备份到私有 GitHub 仓(ECS 中继)

适用于把 hermes-full.tar.gz 推到 example-user 私有仓(如 `hermes-backups`)。本机 git push 直连被 reset,必须走 ECS 中继(与 WeChatExporter 同款)。

**GitHub 文件体积限制(关键,先分片再推)**:
- 单文件 >100MB 硬拒(pre-receive hook declined,推不上去)——备份包 247MB 直接 push 必挂,别试
- 50~100MB 能推但触发 LFS warning(GH001,不阻断但脏)
- **规范分片: `split -b 40m -d hermes-full.tar.gz part-`(40MB 全程无警告),仓内放 part-00..NN + manifest.sha256 + README(恢复步骤)**
- 分片后仓内**不要**同时留 248MB 整包——bundle 历史里带它仍会被 100MB 拒

**Contents API 传大文件**: 80MB base64 payload 本机直传 GitHub 会 502/超时,不可靠;走 git 推送(ECS 中继)一次到位。小文件(<100KB)Contents API 直传没问题。

**ECS 中继流程**:
1. 本地 `git init` 干净历史(只含分片+manifest+README)→ `git bundle create refs/heads/main`
2. `scp bundle aliyun-ecs:C:/`
3. ECS 侧 `git -C C:\hb-repo config core.sshCommand` 指向**本仓专属部署密钥**(见下),`fetch bundle` + `update-ref` + `push -f origin main`
4. 本机 `gh api repos/<o>/<r>/git/trees/<sha>` 核验文件落地

**部署密钥坑(本轮实测)**: 部署密钥是**仓级**的——ECS 上 WeChatExporter 用的 `id_ed25519` 加到其他仓报 "key is already in use"(同公钥不能挂两仓)。给新仓推送:
```
ssh aliyun-ecs "C:\tools\git-portable\usr\bin\ssh-keygen -t ed25519 -f C:\tools\git-portable\.ssh\id_ed25519-<repo> -N \"\""
gh api -X POST repos/<o>/<r>/keys -f key="$(读 pub)" -f title=<repo>-ecs -f write=true
```
然后该仓 clone 的 git 用仓级 `core.sshCommand` 指新 key(不碰全局,不影响 WeChatExporter)。

**坑(逐条实测)**:
- bundle 参数里 tag 名与目录同名会 "ambiguous argument"(用 `refs/` 前缀或分开传)
- init 空仓上裸 `push origin main` 报 "current branch 'master' does not have any commits yet"——用显式 refspec `push -f origin refs/heads/main:refs/heads/main`
- jq 构造 Contents payload 时 base64 用 `--rawfile`(argv 传 100KB+ 字符串报 "Argument list too long");manifest 生成脚本里 `part-$p` 变量笔误会拼成 part-part-00
- scp ~250MB bundle 约 2-4 分钟,timeout 给足 400s+

**SSH 通道故障绕行(2026-10 实测)**: `aliyun-ecs`(Administrator)靠 ControlMaster 复用时一切正常,但复用连断开/被云盾限流后,新连接 publickey 可能被直接拒(诊断:`ssh -O exit aliyun-ecs` 断复用 + `ssh -v -o ControlMaster=no -o BatchMode=yes` 看 Offering/Auth 段;日志里 `no identity pubkey loaded` 别误读成密钥文件损坏——服务端只是拒了该 key)。绕行=**同机第二账号 devbox 别名**(本机已配,专属密钥,工作目录 C:\Users\devbox\project)。注意:
- `devbox` 无 `C:\` 根写权限(scp 到 C:\hb3.bundle 报 Permission denied)——中继 bundle/脚本放 `C:\Users\devbox\`,git 仓 init 也放家目录(如 `C:\Users\devbox\hb-repo2`)
- git 推送走仓级 `core.sshCommand` 部署密钥(ssh.github.com:443),与登录 ECS 用哪个账号无关——devbox 连上去照样推
- 本机直连 `git ls-remote`/fetch 偶尔通、push 被 reset——别指望,大东西都走 ECS

**仓命名/描述规范**(用户偏好): 私有备份仓 About 写清内容+平台+恢复方式,如 "Hermes Agent 备份(配置/记忆/技能/会话/状态库) | 私有 | 本机 macOS 生成 | tar.gz 分片 | git"。

**详细配方与脚本**: `references/github-backup-ecs-relay.md`(含 .bat 模板)。

## 参考

- `references/quark-cli-pitfalls.md` — 夸克 CLI 的坑与能力边界(execute_code -104、search 限制、无 delete/rename)
- `references/github-backup-ecs-relay.md` — 私有 GitHub 仓备份完整配方(分片/bundle/ECS 中继/deploy key 坑, 2026-10)
