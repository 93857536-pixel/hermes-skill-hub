# Hermes 备份 → 私有 GitHub 仓(ECS 中继)完整配方

2026-10-23 配通: 仓创建、部署密钥 `aliyun-ecs-hb` 挂上、bundle 传到 ECS、refs 在 C:\hb-repo 更新到备份 commit、推送脚本就绪。**最终 push 落地须以 ECS 侧 `git ls-remote origin` 显示新 commit 为准**(当次会话结束时后台推送尚未确认,下次接手先跑验证)。

## 前置状态
- ECS(`aliyun-ecs`)全局 git: `core.sshCommand=C:/tools/git-portable/usr/bin/ssh.exe -p 443 ... -i C:/tools/git-portable/.ssh/id_ed25519` + `url.ssh://git@ssh.github.com:443/.insteadof=https://github.com/`
- **该 id_ed25519 是 WeChatExporter 仓的部署密钥**(title `aliyun-ecs-fixer`)——deploy key 一钥一仓,对其他任何仓都会 "Repository not found"。
- hermes-backups 专属部署密钥 `aliyun-ecs-hb`: `C:\tools\git-portable\.ssh\id_ed25519-hb`(write=true, 2026-10-23 加)。

## 本机步骤
```bash
# 1. 打包(SKILL §1) → ~/hermes-backup-<ts>/hermes-full.tar.gz
# 2. 分片 + manifest
cd ~/hermes-backup-<ts>
split -b 80m -d hermes-full.tar.gz part-
for p in part-*; do shasum -a 256 "$p" | sed "s|$p|hermes-backup-$TS/$p|"; done > manifest.sha256
# 3. 写 README(恢复说明: cat part-* > tar.gz, 校验, tar -xzf 到 ~/.hermes 备份目录)
git init; git add -A; git commit -m "backup: ..."; git tag <ts>
# 4. 远端已有旧 commit 时(如 Contents API 传过的 manifest):
git remote add origin https://github.com/example-user/hermes-backups.git
git fetch origin main
git merge origin/main --allow-unrelated-histories --no-edit
git tag -f <ts> main   # tag 名与目录同名时必须 -- 或 refs/ 前缀, 防 "ambiguous argument"
git bundle create /tmp/hb.bundle refs/heads/main refs/tags/<ts>
git bundle verify /tmp/hb.bundle
scp /tmp/hb.bundle aliyun-ecs:C:/hb.bundle   # 255MB ≈ 3min
```

## ECS 侧脚本(C:\hb-push3.bat 模式)
```bat
git init C:\hb-repo
git -C C:\hb-repo config core.sshCommand "C:/tools/git-portable/usr/bin/ssh.exe -p 443 -o StrictHostKeyChecking=accept-new -i C:/tools/git-portable/.ssh/id_ed25519-hb"
git -C C:\hb-repo remote set-url origin ssh://git@ssh.github.com:443/example-user/hermes-backups.git
git -C C:\hb-repo fetch C:\hb.bundle refs/heads/main
git -C C:\hb-repo update-ref refs/heads/main FETCH_HEAD
git -C C:\hb-repo push -f origin refs/heads/main:refs/heads/main   ← 显式 refspec!
git -C C:\hb-repo ls-remote origin   ← 验证
```
255MB 走 443 口 SSH 较慢,建议 ssh 会话后台 + notify_on_complete。

## 坑清单
1. **Contents API 大文件**: ~80MB payload → 502 / 本机侧 timeout(不可靠)。小文件 OK。jq 传 base64 必须 `--rawfile`(argv 上限 "Argument list too long")。
2. **deploy key 作用域**: 新仓推送前先 `gh api repos/<o>/<r>/keys` 看密钥; 缺则 `gh api -X POST .../keys -f key="$PUB" -f write=true`("key is already in use" = 该公钥已是别的仓的 deploy key)。
3. **init 空仓 push**: `git push origin main` 报 "current branch 'master' does not have any commits yet" → 用 `refs/heads/main:refs/heads/main` 显式 refspec。
4. **本机直推 GitHub 不可靠**: ls-remote/fetch 偶尔通, push 常被 reset → 大东西一律 ECS 中继。
5. **Windows .bat 里避免 `&`/引号嵌套**: 同 aliyun-ecs skill 的多层转义坑, 脚本 scp 上去单独执行。
6. **bash 循环 double-prefix**: `for p in part-*; do shasum part-$p` 里 `$p` 已是 `part-00`, 再拼 `part-$p` 得 `part-part-00` 全部 miss。写 `shasum "$p"`, 生成后立刻 `head manifest.sha256` 肉眼校验非空。
