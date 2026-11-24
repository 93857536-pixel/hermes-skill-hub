# Tauri CI 红灯原始报错转录(对号入座)

来自 hermes-agent-migrator v0.2.0 (2026-09, GitHub Actions windows/ubuntu
runner) 的真实日志摘录。

## 1. Windows: tauri-build 缺 icon.ico

```
error: failed to run custom build command for `hermes-agent-migrator-gui v0.2.0`
  package.metadata does not exist
  `icons/icon.ico` not found; required for generating a Windows Resource file
  during tauri-build
```
- 出现在 **cargo clippy** 里也一样: GUI crate 的 build.rs 在 Windows 上必跑
  tauri-build, 所以「core 测试 job」用 `--workspace` 时, Windows 上也会挂在
  这里(不止打包)。
- 修法: 补 icons/icon.ico + bundle.icon 数组加一项; core job 不再拉 GUI crate。

## 2. ubuntu: GUI crate 缺 glib-2.0/GTK 系统库

```
The system library `glib-2.0` required by crate `glib-sys` was not found.
The file `glib-2.0.pc` needs to be installed and the PKG_CONFIG_PATH
environment variable must contain its parent directory.
The PKG_CONFIG_PATH environment variable is not set.
warning: build failed, waiting for other jobs to finish...
error: Process completed with exit code 101.
```
- 根因: `cargo clippy --workspace` 把 hermes-agent-migrator-gui (Tauri) 在
  ubuntu 上编译, 而 ubuntu runner 没装 gtk3/webkit2gtk。
- 修法: core job 收窄 `cargo clippy/test -p migrator-core -p hermes-migrator-cli`;
  GUI 构建只在 windows/macos runner(它们系统栈齐全)做。
- 别走「ubuntu 上 apt 装一堆 libgtk 然后 cargo tauri build」路线: 又慢又脆
  (rpm/deb bundling 易碎), 除非产品确实要交付 Linux 包。

## 3. Release 重跑非幂等

- windows build job 挂了 → Publish job 被跳过(`-` 状态, 非失败); 修完重推
  后, `gh release create <同tag>` 报已存在 422, Publish 又挂。
- 修法: 见 SKILL.md 第 3 节幂等片段(空产物守卫 + view/delete + create)。

## 4. 本地与远程 lineage 分叉(经 API 推过的仓)

- 症状: `git log --oneline origin/main..HEAD` 与 `HEAD..origin/main` 都非空,
  提交主题相似但 SHA 不同(历史上有经 Git Data API 直接建 commit 的记录),
  `git push` 报 `fetch first` / unrelated histories; `git merge --ff-only
  origin/main` 报 `fatal: refusing to merge unrelated histories`。
- 修法(别 force-push): `git checkout -B main-cisync origin/main &&
  git cherry-pick <本地新提交> && git push origin main-cisync:main`,
  然后本地 main `git reset --hard origin/main` 对齐。
- 国内网络下 fetch/push 用 `GIT_CURL_COMMAND="curl --resolve
  github.com:443:140.82.112.3"`(env 级 curl 解析), 普通 `git fetch` 可能
  直接超时 180s+。

## 5. 本地验证脚本的假阳性

- 本机没装 pyyaml: `python3 -c "import yaml"` 抛 ModuleNotFoundError →
  脚本把 workflow 误判为「invalid YAML」。 用 `ruby -ryaml`(macOS 自带)
  复核: 两个 workflow 实际都有效。 教训: 校验工具缺失 ≠ 被校验物无效,
  先区分「工具缺」和「内容错」再下结论。
