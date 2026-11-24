# 产物内嵌版本/内容核验 + 中继推送补充（2026-10-05 实测）

## 1. 🔴 tag 必须打在「含版本号改动」的提交上

**翻车现场（WeChatExporter v2.20.0）**：功能代码 commit 了，但 `build_app.sh` / `*.csproj` /
`CHANGELOG.md` 的版本号改动**忘在暂存区没提交**。tag 打在了那个不含版本号的提交上 → CI 构建出的
macOS 包 `Info.plist` 里 `CFBundleShortVersionString` 仍是**旧版 2.19.3**，Release 却顶着 v2.20.0 的名字。

**规则**：
- 打 tag 前 `git status` 必须干净；版本号文件确认已 commit（`git show <tag>:build_app.sh | grep APP_VERSION`）。
- 打完后**下载产物核验内嵌版本**——这是唯一能测出「构建错了 commit」的手段，API 层
  `state=uploaded` / digest 全对也测不出来。

**核验配方（macOS 包）**：
```bash
curl --noproxy '*' -sL -o mac.zip "https://github.com/<o>/<r>/releases/download/<tag>/<file>.zip"
unzip -q mac.zip
lipo -archs App.app/Contents/MacOS/App                              # 期望 x86_64 arm64
/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" App.app/Contents/Info.plist   # 期望新版本号
strings App.app/Contents/MacOS/App | grep -c -i "<新功能符号>"       # 期望 > 0（如 cloudbackup）
```
**核验配方（Windows 包）**：解压后看 `.exe`/`.dll` 是否存在 + 体积合理；符号/中文串搜索见
`scripts/verify-release-artifact-member.py`（UTF-16LE 堆）。

**修正流程**：补提交版本号 → `git push origin main` → 删旧 tag（本地 `git tag -d` + 远端
`git push origin :refs/tags/<tag>`）→ 重打 tag 强推 → 触发重建 → 重新核验产物版本号。
用 `softprops/action-gh-release` 时同名 Release 会被新构建覆盖资产。

## 2. 一把 deploy key 只能挂一个仓库

中继机（ECS）已有一把 key 挂在仓库 A 上时，直接把它再 POST 到仓库 B 会被拒
（`Validation Failed` / `key is already in use`）。**每个仓库新生成一把钥**：

```bash
ssh relay "C:\tools\git-portable\usr\bin\ssh-keygen.exe -t ed25519 -f C:\tools\git-portable\.ssh\id_ed25519-<repo> -N \"\" -q"
# 读公钥 → 挂到目标仓库
gh api -X POST repos/<o>/<r>/keys -f title=<name> -f key="ssh-ed25519 AAAA... comment" -f read_only=false
```
（`read_only=false` 才能 push；`gh api repos/<o>/<r>/keys` 列出已有 key 会告诉你 key 被哪个仓占了。）

## 3. 中继机 push 走 ssh:443 必须设 core.sshCommand

```bash
git config core.sshCommand "C:/tools/git-portable/usr/bin/ssh.exe -p 443 -i C:/tools/git-portable/.ssh/id_ed25519-<repo> -o IdentitiesOnly=yes -o StrictHostKeyChecking=no"
```
- 用**环境变量 `GIT_SSH_COMMAND`** 或 cmd 内联 `set X=Y & git push` → 报
  `ssh variant 'simple' does not support setting port`（环境变量没生效，走了内置 simple ssh）。
- 正确做法：把 `git config core.sshCommand ...` + `git remote add/set-url` + `git push` **写进一个 `.bat`**，
  scp 到服务器再 `cmd /c "C:\path\x.bat"` 执行。内联在 ssh 单行里 unreliable。

## 4. 中继推送到「只放产物不含源码」的仓库时

若远端 main 曾被刻意重构成单个「README-only」提交（如 某聊天App 2026-09-27 去源码化），
而本地是完整源码历史且**无共同祖先**——**不要**直接把本地历史强推上去（会撤销用户的意图）。
稳妥选择 = 从该单提交拉一个分支、只更新 README/文档、`git push origin <branch>:main` 做
**fast-forward**（零风险，不泄露源码）。源码历史留本地/私有仓。

## 5. 校验远端 main 的真实历史深度

浅 fetch（`--depth=1`）会让 `git log origin/main` 只显示 1 个提交，误判「远端只有一个孤提交」。
用 GitHub API 交叉确认：`curl --noproxy '*' https://api.github.com/repos/<o>/<r>/commits?per_page=5`
——它返回的条数才是远端 main 的真实提交数。
