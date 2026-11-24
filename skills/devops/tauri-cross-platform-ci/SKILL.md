---
name: tauri-cross-platform-ci
description: "Fix Tauri cross-platform CI/Release on GitHub Actions."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [tauri, rust, ci, github-actions, release, icons, cargo]
    related_skills: [github-release-publishing, github-repo-management, macos-app-build-packaging, winui-dotnet-development]
---

# Tauri 跨平台 CI/Release 排障与落地

## When to Use

- Tauri (Rust + 前端) 桌面应用的 GitHub Actions CI 跑红(ubuntu 缺 GTK/webkit 系统库、
  Windows 缺 icon.ico), 需要定位与修复时
- 给 Tauri 应用配自动 Release workflow(多平台打包 + 发 GitHub Release), 要**幂等**(重跑不炸)
- 仓库之前经 GitHub Data API 推过、本地 git 与远程 main 分叉(unrelated histories), 需安全落新改动
- 要在 CI 长跑期间后台看护 + 本地先拿绿证据时

适用范围: Tauri v2 (Rust core + 前端 bundle) 桌面应用, 在 GitHub Actions 上做
多平台 CI + 自动 Release。 本技能只收录**反复会踩的坑**与**被验证过的修法**,
一次性细节看 `references/`。

## 三类最高频红灯(先查这三个)

Tauri 跨平台 CI 的红 90% 是下面三件, 按序排查:

### 1. 缺平台图标 → tauri-build 硬失败(Windows 最典型)

`tauri-build` 在 **Windows** 上需要 `icons/icon.ico` 生成 `.exe` 资源文件;
**macOS** 打包需要 `.icns`。 缺任一个都会 `failed to run custom build command ...
`icons/icon.ico` not found; required for generating a Windows Resource file`。

- 检查 `gui/src-tauri/tauri.conf.json` 的 `bundle.icon` 数组, 三件套齐全:
  `icons/icon.png`, `icons/icon.ico`, `icons/icon.icns`(按目标平台至少带对应项)。
- 图标生成法, 两条路按环境选:
  - **有 cargo/tauri CLI 时首选(最快)**: `cargo tauri icon <母版.png>`(或 `npx @tauri-apps/cli icon`)一条命令重生成整套: icon.png/ico/icns + 各尺寸 + ios/android mipmap。icons/ 目录会从 3 文件变几十个(**预期行为**), `git add -A gui/src-tauri/icons/` 整目录入库。详见 macos-app-icons 技能 `references/tauri-iconset-pitfalls.md`。
  - 无 CLI 时手搓: `.ico` = 多档 16/24/32/48/64/128/256 (PIL `Image.save(..., sizes=[...])`), `.icns` = sips 逐档 → 目录命名必须 `.iconset` 结尾 → `iconutil -c icns`(见 `scripts/gen-tauri-icons.py`)。
- 生成后把新增图标文件 `git add`, 否则 CI checkout 不到。

### 2. ubuntu 上 `cargo clippy --workspace` 把 GUI crate 拉进来 → 缺系统库

Tauri GUI crate 依赖 GTK/webkit2gtk 系统库; GitHub ubuntu runner 默认**没装**,
`glib-sys` 等编译报 `The system library glib-2.0 required by crate glib-sys
was not found`。

修法(比装一整套 GTK 稳得多): **CI 的 core 测试 job 收窄到 core+cli 包**,
GUI 构建交给专门的 build job:

```yaml
# core tests job(ubuntu 也能过)
- name: Cargo clippy
  run: cargo clippy -p migrator-core -p hermes-migrator-cli -- -D warnings
- name: Cargo test
  run: cargo test -p migrator-core -p hermes-migrator-cli
```
GUI build job 只在 windows/macos runner 跑 `cargo tauri build`
(它们有 GUI 系统栈), 不要在 ubuntu 上打包 GUI。
包名以各 crate `Cargo.toml` 的 `name` 为准(不是目录名 / lib 名), 先 grep 确认。

### 3. Release workflow 非幂等 → 重跑就炸

`gh release create` 对已存在的 tag 直接 422。 CI 重跑(修完上面两个 bug 再推)
会撞上「同 tag 已有 release」。 修法(见 `templates/release-idempotent.yml` 片段):

```bash
# 空产物守卫: 不发布空 release
test -n "$(ls -A dist/ 2>/dev/null)" || { echo "no artifacts; abort"; exit 1; }
# 幂等: 已存在就先删再建
if gh release view "$TAG" >/dev/null 2>&1; then
  gh release delete "$TAG" --yes || true
fi
gh release create "$TAG" ... --target "$sha" dist/*   # sha 见下条
```

### 4. 无 checkout 的 Publish job: `--target <tag名>` 直接炸(2026-09 实测)

Publish job 若只有 `download-artifact`、**没有 `actions/checkout`**,
`gh release create ... --target v0.2.0`(tag 名)会先调本地 git 解析 tag→commit,
报 `failed to run git: fatal: not a git repository` —— build 全过、安装包全在,
4 秒挂在最后一步。修法: **纯 API 解析 tag→SHA**, 传给 `--target`:

```bash
TAG="${{ github.ref_name }}"; REPO="${{ github.repository }}"
ref_json="$(gh api "repos/$REPO/git/ref/tags/$TAG")"
sha="$(echo "$ref_json" | jq -r .object.sha)"
otype="$(echo "$ref_json" | jq -r .object.type)"
[ "$otype" = "tag" ] && sha="$(gh api "repos/$REPO/git/tags/$sha" --jq .object.sha)"  # annotated tag 需剥皮
gh release create "$TAG" ... --target "$sha" dist/*
```
本地可把这段调用逐条只读跑一遍实测验证(runner 上同款调用), 并
`bash -n` 校验 run block; YAML 用 ruby 复核。

### 5. 本机 headless 环境 `cargo tauri build` 打 DMG 挂:bundle_dmg.sh 的 Finder AppleEvent 超时(2026-09-30 hermes-agent-migrator 实测)

症状:本地(Agent/SSH/headless,或「有 Aqua 会话但 AppleEvent 无响应」)跑 `cargo tauri build` 全绿到最后一行 `Running bundle_dmg.sh` 才报 `error running bundle_dmg.sh`,**CI 却一直正常**。根因两层叠加:
- **层①(本质)**:Tauri 内置 `bundle_dmg.sh`(create-dmg fork)用 `osascript` 驱动 **Finder 摆图标/背景**。headless 里 Finder AppleEvent 无响应 → osascript 超时 **-1712** → 脚本 `exit 64`。`launchctl managername` 可能仍报 Aqua(终端挂在 GUI 会话),**不能用 managername 判**,要实测探针:`perl -e 'alarm 12; exec @ARGV' osascript -e 'tell application "Finder" to count of disks'`(成功=可用,超时/失败=skip)。
- **层②(坑叠加)**:`bundle/macos/` 下若有**同名成品 dmg**(之前手动 hdiutil 补的产物),会卡住脚本 `hdiutil convert`(报「文件已经存在」);脚本中间态 `rw.PID.xxx.dmg` 残留也要清。
修法(项目落 `gui/build_macos.sh` 入口,已提交 hermes-agent-migrator `2bee608`):
```bash
# 12s 限时 Finder AppleEvent 探针,失败 → export CI=true(让 tauri-bundler 加 --skip-jenkins)
if perl -e 'alarm 12; exec @ARGV' osascript -e 'tell application "Finder" to count of disks' >/dev/null 2>&1; then :; else export CI=true; fi
# CI=true 时 tauri-bundler 自动 --skip-jenkins,DMG 内容不变,只跳过图标摆位/背景(可接受)
# 桌面终端想保留布局:FORCE_GUI=1 ./build_macos.sh
```
要点:`tauri-bundler 2.9.4` **没有 `createDmgScript` 配置项**(源码 DmgSettings 无该字段),不能注入自定义脚本,只能借 `CI` 环境变量走 `--skip-jenkins`。CI 上 `CI=true` 是 GitHub 自带的,所以这问题**只有本机 headless 现形**——修完务必用同款 headless 环境复跑验证,别拿桌面终端绿了就算。

### 6. 平台 gate 的 Rust 陷阱(只有 Windows runner 会炸, 本地 unix 永远绿)

这两类 bug **在本地(mac/linux)测不出来**, 只有 CI 的 windows job 能暴露。
修好上面 1-3 重推后**才现形**(修一层暴露下一层, 见下)。 细节与 repro 见
`references/platform-gated-rust-traps.md`:

- **`mut` 变量只在 `#[cfg(unix)]` 分支里写入** → 非 unix 平台声明时必中
  `unused_mut`, `-D warnings` 下直接挂编译(而 unix 平台必须 mut, 不能删)。
  修在**声明处**而不是改逻辑: `#[cfg_attr(not(unix), allow(unused_mut))]`。
  典型: 存文件权限位(mode bits)只在 unix 有的 `permissions` map。
- **测试夹具/断言用 `Path::display().to_string()`**: unix 出正斜杠,
  **Windows 出反斜杠**。 若你的引擎按 `/` 归一化做匹配/替换, 用 display()
  写 fixture 或断言的测试在 Windows 必挂(源路径是 `C:\...` 匹配不上 `/` 规则),
  而本地永远绿。 fixture 与断言统一改成 `to_string_lossy().replace('\\\\','/')`
  归一化形式(引擎按 `/` 匹配的话, 引擎侧的输入也应同样归一化——同一契约)。
- **clippy lint 互锁: `io::Lines` 日志泵循环**(2026-09-25 三平台 CI core 测试
  全挂实测, 本地 `cargo check`/`cargo test` 全绿发现不了)。 读子进程
  stdout/stderr 的 `for line in x.lines() { if let Ok(line) = line {...} }`
  被 `manual_flatten` 判错(`-D warnings` 下直接挂编译); 而它建议的 `.flatten()`
  在 `Result<io::Lines>` 上又触发「iterator may loop forever」告警,
  `.filter_map(Result::ok)` 又触发 `lines_filter_map_ok` —— 三条规则互锁,
  无自动修解。 唯一干净写法(三条全静默, 语义不变):
  ```rust
  let mut out = child_stdout.lines();
  while let Some(Ok(line)) = out.next() {
      let _ = tx.send(line);
  }
  ```
  推送前必须按 CI 同款命令本地预跑 `cargo clippy -p <core> -p <cli> -- -D
  warnings`(与 CI yaml 逐字一致), 否则白等一轮 ~13min CI。

**本地交叉验证 Windows 代码路径: 首选 mingw-w64 + GNU target 全量 check**(2026-09-25
hermes-agent-migrator v0.3.0 实测): `brew install mingw-w64` 装好 C 交叉工具链后,
`x86_64-pc-windows-gnu` target 的 `cargo check` 可以**整 crate 通过类型检查**——
含 `#[cfg(windows)]` 专属分支与 lzma-sys 等 C 依赖(C 部分由 mingw 交叉编)。
比 MSVC target 被挡死时强得多, 也代替了下面最小 repro 的大多数场景:
```bash
brew install mingw-w64   # bottle ~356MB/装完 1.4GB; 时间长用 background=true
# 坑: 首次 install 可能静默失败(输出只有 Removing 行、keg 没建),
#     用 `brew list mingw-w64` 确认, 没建成就原命令重跑
rustup target add x86_64-pc-windows-gnu
CC_x86_64_pc_windows_gnu=x86_64-w64-mingw32-gcc \
AR_x86_64_pc_windows_gnu=x86_64-w64-mingw32-ar \
  cargo check -p <core> -p <cli> --target x86_64-pc-windows-gnu
```
MSVC target(`x86_64-pc-windows-msvc`)因 Mac 上没有 MSVC C 工具链,
`cc` 编 C 依赖仍会挂——不必再花力气, check 级验证已足够,
链接与最终裁决交给 CI 的 windows-latest(MSVC) job。

**轻量备选: 最小 rustc repro** — 只想验证某段无依赖逻辑的平台告警
(unused_mut 等)时, 把那段抽成独立 .rs,
`rustc --edition 2021 --target x86_64-pc-windows-msvc -W unused_mut repro.rs`
对「未修复/已修复」各跑一次(未修复必现 + 修复后消失 + unix target 无回归)。
输出路径别用 `/dev/null`(rustc 要建临时文件, 会报 Permission denied);
Windows target 链不到 `link.exe` 属正常(告警检查先于链接)。

## 关键坑: 经 GitHub Data API 推过的仓, git 本地与远程 lineage 分叉

如果之前是用 `gh api`/Git Data API(而非 `git push`)把提交推上远程的,
**远程 main 的 commit SHA 与本地 main 完全不同**(`git status` 里
`origin/main..HEAD` 和 `HEAD..origin/main` 都非空 = 分叉)。 此时直接
`git push` 会被拒(unrelated histories)。

正确恢复(2026-09 实测):
```bash
GIT_CURL_COMMAND="curl --resolve github.com:443:140.82.112.3" git fetch origin
git checkout -B main-cisync origin/main        # 站到远程 lineage 上
git cherry-pick <本地新提交SHA>                 # 把新改动落到远程 lineage(不 force-push)
GIT_CURL_COMMAND="curl --resolve github.com:443:140.82.112.3" git push origin main-cisync:main
git checkout main && git reset --hard origin/main   # 本地 main 对齐远程
git branch -D main-cisync
```
**绝不 `git push --force` 覆盖远程**——那会把远程已有 Release/tag 指的分叉抹掉。
用 cherry-pick 保 lineage。

## CI 后台看护(跑完才报结论)

**逐层暴露规律**: 每次 CI 跑红往往只暴露**最外层**的错误(tauri-build 图标缺失挡在 cargo 编译之前), 修完重推才暴露下一层(core clippy 的 platform-gated 告警), 再修再推才暴露第三层(test 的断言平台差异)。**别假设一次修全**——每个 run 都是新证据, 按 run 逐层推进。

`gh run view --job <job_id> --log` 拉全日志, 但 **run 未完成时拿不到**(输出
"logs will be available when it is complete"), 完成前只能看 step 级 ✓/✗ 结论。
日志巨大时先 `> /tmp/x.log` 落盘再 grep(直接管道会被输出截断)。

**gh 命令两个坑**:
- `gh run list -q '.[0].databaseId'` **必须配 `--json databaseId`**, 裸 `-q` 报
  "cannot use --jq without specifying --json"。
- `gh run view <id> --json status,conclusion -q '...'` 取结论轮询(看护循环用)。

**双 workflow 甄别(用户问「编译过了吗/CI 过了吗」时, 2026-09-25 实测)**:
带自动 Release 的仓往往同时有 **Release workflow**(tag 触发)和 **CI
workflow**(push main 触发)两个 run。 Release 打包全绿 ≠ CI 绿——clippy/
test 挂在 CI workflow, 而 exe/dmg/msi 照常发布, 用户容易看到 CI 红就以为
「编译没过」。 回复前必须:
1. `gh run list --limit 5` 列出**所有**相关 run(同名 commit 会触发多个
   workflow), 逐个查结论;
2. 挂的 job 用 `gh api .../jobs --jq '.jobs[].conclusion'` 定位到 step,
   `gh run view <id> --log-failed` 抓失败片段(不用等 run 完成);
3. 涉及「已发布?」时再 `gh release view <tag>` 核对 assets 实际存在。
   结论按 workflow 分开报:「Release 成功, CI 挂在 clippy, 已修」。

CI 全跑 ~10-15min。 别前台 sleep 干等; 用 terminal `background=true` +
`notify_on_complete=true` 起一个 `gh run view <id> --json status,conclusion`
轮询循环, 跑完自动回消息:
```bash
while true; do
  out=$(gh run view <run_id> --json status,conclusion -q '.status+" "+.conclusion' 2>/dev/null)
  case "$out" in completed*) echo "DONE: $out"; break;; *) sleep 60;; esac
done
```
**本地能验证的先本地跑**(同 CI 的 fmt/clippy/test 命令)拿到绿证据,
CI 只是最终权威裁决(平台差异只能靠真 runner)。 本地临时验证脚本写到系统
temp 目录, 跑完即删(见 `scripts/verify-cifix.sh` 模式)。

## 验证纪律

- YAML 校验本机可能没 pyyaml → 用 `ruby -ryaml -e "YAML.load_file(...)"`(系统自带)
  复核, 别把 pyyaml 缺失误判成「workflow 无效」。
- `gh release view` 取时间戳用 `assets[0].updatedAt`(顶层无 updatedAt)。
- 图标/配置改动提交前先 `git status --porcelain` 确认无未跟踪图标文件漏 add。

## 参考

- `scripts/gen-tauri-icons.py` — 从 1024 png 生成 .ico(多档)+ .icns 全流程
- `scripts/verify-cifix.sh` — 本地 ad-hoc 验证 CI 改动一致性模式(跑完删)
- `templates/release-idempotent.yml` — 幂等 release 发布 job 片段(含无 checkout 时的 API tag→SHA 解析, 见 §4)
- `references/ci-red-lights.md` — 三类红灯原始报错转录(对号入座用)
- `references/platform-gated-rust-traps.md` — 平台 gate Rust 陷阱(unix-only mut、
  display() 反斜杠夹具、最小 rustc 交叉 repro), Windows runner 才现形的 bug
- 通用 GitHub Release 上传/验证纪律: 见 `github-release-publishing`
