---
name: github-release-publishing
description: "Publish app binaries as GitHub Releases and verify uploads."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [github, release, gh, packaging, verification, ditto]
    related_skills: [github-repo-management, github-auth]
---

# GitHub Release 发布与验证

## 硬性规则(用户明确要求,每次必须遵守)

**⚠️ 全局签名规则(用户 2026-11-15 明确要求): 上架 GitHub Release 的安装包与发给用户的安装包一律不签名。** 无论 iOS(IPA)、Android(APK)、macOS(dmg/app)、Windows(exe/MSI),交付的构建产物必须是未签名版本。具体操作:
- iOS: `CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO` 构建, 产物无 `_CodeSignature/` 与 `embedded.mobileprovision`(见 ios-unsigned-ipa-delivery)
- Android: 交付 `assembleDebug` 包或去掉 signingConfigs 的 release 包(不要 apksigner 签过)
- macOS/Windows: 跳过 codesign/notarize/Inno Setup 签名步骤, dmg/exe 保持未签名
- 交付汇报时如实标注「未签名」, 不代签

**凡是把构建产物(IPA/dmg/zip/exe 等)上传到 GitHub 仓库,都必须同时:**
1. **打 tag**(`git tag -a v<ver>`,推上远端)
2. **创建 Release**(`gh release create v<ver>`,把产物作为附件上传,而非只塞进分支)

不允许把可执行产物只 push 到 main 分支就完事——用户 2026-09-26 明确指出:ios-ipa-archive 和 WeChatExporterMonitor 两个仓库的 IPA 当时只推在 main 上、没建 Release,用户找不到下载入口。**每次交付构建产物前,先检查目标仓库有没有 Release;有就传附件(`gh release upload --clobber`),没有就当场 tag + 建 Release。**

适用范围: 把构建产物(app 二进制、zip 包)发布为 GitHub Release,并**验证外部副作用真实生效**。基础命令(gh release create 的 curl 变体等)见 bundled `github-repo-management` §8——本技能补上它缺失的发布纪律与验证步骤。

## 完整流程(macOS app 示例)

```bash
# 1. 打包(保留签名与权限;--sequesterRsrc 保留资源分支)
ditto -c -k --sequesterRsrc --keepParent "build/Release/App.app" "App-macOS-v1.0.0.zip"
# 版本号取 Info.plist: /usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" App.app/Contents/Info.plist

# 2. tag + 推 tag —— 推 tag 不会推分支提交!
git tag -a v1.0.0 -m "App v1.0.0"
git push origin v1.0.0
git push origin HEAD   # 分支提交必须单独推

# 3. 创建 release + 上传资产
gh release create v1.0.0 "App-macOS-v1.0.0.zip" --title "App v1.0.0" --notes "..."

# 4. 验证(API 层): state=uploaded + sha256 digest
gh release view v1.0.0 --json assets,tagName,url

# 5. 验证(真实下载)——外部副作用必须实测,不能只信 API
curl -sL -r 0-1023 -o /tmp/h.bin "<download_url>" -w "HTTP %{http_code}\n"   # 期望 206
shasum -a 256 "App-macOS-v1.0.0.zip"   # 与 gh 返回的 digest 逐字比对
```

## 更新已发布资产的资产(修 bug 后重发)

同版本号小修(如 UI 修复)后重发: 重新 ditto 打包 → **覆盖上传**:
```bash
gh release upload v1.0.0 "App-macOS-v1.0.0.zip" --clobber   # --clobber 覆盖同名资产
gh release view v1.0.0 --json assets   # 确认 digest 变了(新包)且 state=uploaded
```
注意 digest 变化是"上传真的生效"的硬证据——digest 没变说明传的是旧文件。

**字节级确认(轻量,不下载)**: 快速答复"更新成功了吗"时不用下载比对 sha256——本机 `stat -f "%z" <包>` 与远端 `gh release view <tag> --json assets --jq '.[].size'` 逐项对比,字节一致 + 远端 `updatedAt` 晚于本地构建时间 = 上传的就是这个新包。dmg/zip 字节精确一致是强证据(2026-08 实测: 本地 47950092 = 远端 47950092)。

**时间戳陷阱**: 上次会话确认过"Release 有资产"≠"最新构建已上传"。重建包后必须核对 assets 的 updatedAt 是否晚于本地构建时间,否则旧验证结果会误导(2026-08 误判过一次——21:06 验证成功的是旧 dmg,21:23 重建的新 dmg 是否替换靠字节+时间戳才确认)。

**重打 = 新哈希,这是正常的,别拿旧 hash 判断是否过期**(2026-10-31 实测):
同一份源码两次 `npm run tauri build`,dmg 的 sha256 不同(`459eca3f…` → `1bfb90b4…`,字节数也差几个),
因为 DMG 打包会写入时间戳/资源分叉。两个后果,都容易判错:
- **不能拿"上次记的 hash"判断远端资产是否过期** —— 只能跟**当前本机刚构建的那份**比:
  `stat -f %z <包>` + `shasum -a 256 <包>` 对上远端 `assets[].size` / `digest`,且 `updatedAt` 晚于本次构建时刻。
- **也不能把"digest 变了"当成内容真的变了** —— 它同样可能只是重打的产物。反过来,同一份源码重打后
  digest 没变才更可疑(说明 `--clobber` 没生效)。

**tag 落后 main 时先做决定,别默默发**(手动发版无 CI 时最常见):
实测出现过 `v0.2.0 → a86280e` 而 `main → 1ac640a`(中间是个纯测试提交)的漂移。发版前跑一次:
```bash
git rev-parse v0.2.0^{commit}    # tag 指向
git rev-parse HEAD               # 分支头
```
不一致就显式二选一:(a) 在 HEAD **重打 + `git tag -f` + `push -f`** 让包与 tag 完全对应(推荐,可复现);
(b) 明确记录"落后的是纯测试/文档提交,二进制等价",别糊过去。别一边说"已发布"一边让 tag 指向旧代码。

**git push 报 `HTTP2 framing layer` / 连接超时 → 先查 DNS 给的是不是死 IP（2026-10-31 实测）**：
症状是 `fatal: unable to access ...: Error in the HTTP2 framing layer`，接着 75s/311s 超时；
但同一时刻 `api.github.com` 返回 200。判据与解法：
```bash
dig +short github.com                      # 实测给出 20.205.243.166 —— 该 IP 已死
# 逐个探其它 A 记录，找出还活着的：
for ip in 140.82.112.3 140.82.113.3 140.82.116.3; do
  curl -s -m 4 -o /dev/null -w "$ip %{http_code}\n" --resolve "github.com:443:$ip" https://github.com/
done                                       # 140.82.112.3 / 140.82.116.3 回 200
# 不改 /etc/hosts（无需 sudo、不影响其它进程），让 git 单次走活 IP：
git -c http.curloptResolve=github.com:443:140.82.112.3 -c http.version=HTTP/1.1 push origin main
git -c http.curloptResolve=github.com:443:140.82.112.3 -c http.version=HTTP/1.1 push -f origin v0.2.0
```
- `gh`（走 api.github.com）在此时**仍然可用**，所以 `gh release upload --clobber`、`gh api .../git/ref/tags/...`、`gh release edit` 都能正常跑——**代码推送与资产上传统走两条路**，别因为 git 挂了就以为整个 GitHub 不可达。
- 下载验证也一样：走 `https://api.github.com/repos/<o>/<r>/releases/assets/<id>` + `-H "Accept: application/octet-stream"`（api 通即可），不必强求 github.com/releases/download 直链。
- ⚠️ **别拿 `| tail` 的退出码当 push 成功判据**（本次 `exit=0` 实为 tail 的码）。必须查远端：
  `git ls-remote origin refs/heads/main` 或 `gh api repos/<o>/<r>/commits/main --jq .sha` 与本地 `git rev-parse HEAD` 比对。
- ⚠️ **强推 annotated tag 后要解两层才确认指向**：`gh api .../git/ref/tags/v0.2.0 --jq .object.sha` 给的是 **tag 对象** SHA，
  还要再 `gh api .../git/tags/<tagobj> --jq .object.sha` 才是 commit。只有与 `git rev-parse v0.2.0^{commit}` 相等才算 tag 指对了。

**代理诊断(gh 连不上时,按序查)**:1. `lsof -nP -iTCP:1082 -sTCP:LISTEN` —— 进程存在 ≠ 端口在听;确认 MacPacket 真在监听
2. `scutil --proxy | grep -iE "http|socks"` —— 系统代理是否已配置
3. `curl -s -m 5 -o /dev/null -w "%{http_code}" -x http://127.0.0.1:1082 https://api.github.com/` —— 实测,200 才算通
4. 刚 `open -a` 代理 app 后要等几秒再测;监听 1082 的进程是 MacPacket(Shadowrocket 的配套代理进程,不是 Shadowrocket.app 本体)
5. 代理没起时 curl 报 `proxyconnect tcp: dial tcp 127.0.0.1:1082: connect: connection refused`——此时所有 gh 调用都失败,别急着怀疑 gh 本身

**歧义确认**: 用户问"上传成功了吗/新的上传成功了吗"时,先确认指哪个上传。实际歧义有**三层**,别只查一个就下结论(2026-08 实测连续猜错三次被纠正):
1. 夸克网盘自动备份(本机 on_session_end hook 每次会话结束都上传,日志会误导)
2. GitHub Release **资产**(dmg/zip/exe)
3. GitHub **代码推送**(git push,HEAD 是否到远端)
用户说"上传 github"≠"传资产",可能指 push。**并列验证三处**再答复,或直接 clarify 问清是哪一种;查最近会话只用于定位候选,不用于替代确认。\n\n**"推送成功了吗"的正确验证**(用户说"叫你推送"时):
```bash
git fetch origin -q
git rev-parse HEAD                        # 本地
git ls-remote origin HEAD | cut -f1       # 远端
git log --oneline origin/main..HEAD       # 空 = 无未推送提交
git status -sb                            # ## main...origin/main 无 ahead = 已同步
```
注意: 推 tag 不推分支,`gh release upload` 也不等于 push——两者都要查。另外仓库可能不在 ~/Projects(如迁移到 ~/Programming/Projects 或编程盘),先 `mdfind -name <repo>` 定位再查。

**删除旧资产**(用户要求"把旧的删掉"、dmg 替代 zip 时):
```bash
gh release delete-asset v1.0.0 "App-macOS-v1.0.0.zip"   # 按资产名删,无需 --clobber
gh release view v1.0.0 --json assets                    # 确认已从列表消失
```

## 交付 dmg(用户要求"可安装包,不是源码/zip"时)

用户对"打包好的"定义因平台而异: zip 里的 .app 在某些用户眼里仍算"源码/中间产物",
明确要 dmg 时用 hdiutil(系统自带,无需 create-dmg/brew):
```bash
# 标准布局: 内含 app(拖入 Applications 即可安装)
hdiutil create -volname "App Name" -srcfolder "build/Release/App.app" \
  -ov -format UDZO "App-macOS-v1.0.0.dmg"
# 验证可挂载(必须做,别只信文件大小)
hdiutil attach App-macOS-v1.0.0.dmg -nobrowse && ls "/Volumes/App Name/" && hdiutil detach "/Volumes/App Name"
```
- `-srcfolder` 直接接受 .app bundle(自动带 Applications 链接的布局可后续用
  AppleScript 定制,最小可用先这样)。
- 上传同 zip 流程:`gh release upload v1.0.0 "App-macOS-v1.0.0.dmg" --clobber`。
- **Windows exe 本机编不了时**(无 dotnet/Windows): 用 GitHub Actions windows-latest
  runner 云编译,见 `winui-dotnet-development` 技能的
  `templates/windows-exe-inno-build.yml` + `templates/installer.iss` +
  `references/winui-cloud-build-failure-path.md`。**交付形态: 单文件 Inno Setup
  安装器 exe(不是 zip)**——用户明确要求 Release 只留 exe + dmg。

## 多端统一发行(一个 tag 挂多平台资产, 2026-11 某聊天App v1.9.28 实测)

用户要"一个发行版含 N 个系统的安装包和说明"时:
1. **资产本地备齐 + 统一命名** `<项目>-<平台>-<版本><-签名态>.<ext>`(如 `X-ios-unsigned-v28.ipa` / `X-android-v1.9.16-debug.apk` / `X-harmony-v1.9.16-unsigned.hap`),先算 `shasum -a 256` 留底。
2. **一条命令多资产建 Release,长说明走文件**:多端说明塞不下内联 `--notes`,写文件用 `--notes-file`(模板见 `templates/release-notes-multiplatform.md`):
   ```bash
   # git 被墙/DNS 污染时 tag 走 API(见「git 传输被 DNS/代理卡死」条)
   gh api -X POST repos/<o>/<r>/git/refs -f ref=refs/tags/v1.9.28 -f sha=<远端main SHA>
   gh release create v1.9.28 asset-a asset-b asset-c -R <o>/<r> --title "..." --notes-file release-notes.md
   ```
   资产名 = 本地文件名(要改名先 `cp` 再传,见 ios-unsigned-ipa-delivery 同名资产坑)。
3. **仓库 About 同步**(API 直改,不依赖 git 可达):`gh repo edit <o>/<r> --description "功能 | 多系统安装包 | 安装方式 | 技术栈"`(用户 About 格式惯例,见「建仓」条)。
4. **README 下载区同步**(contents API PUT):加多端下载表(平台/资产/版本/安装方式)+ 指向最新 Release 的链接 + 签名约定说明。
5. 验证三件套不变:assets `state=uploaded` + 远端 digest 与本地 shasum 逐字 + README 渲染检查。

**⚠️ 各端「不签名」规则的落地差异(2026-11-15 实测,notes 必须如实标注)**:
- **iOS**: 真·未签 IPA(`CODE_SIGNING_ALLOWED=NO`),靠全能签/Esign 第三方签名安装
- **Android**: ⚠️ **Android 系统硬性要求 APK 必须带签名才能安装**(与 iOS 完全不同,未签 APK 在系统层直接拒装)——「一律不签名」在 Android 上的实际落地 = 用 `assembleDebug` 的**公共 debug key**(DN: CN=Android Debug),**不用项目私有 keystore**;notes/README 必须写明「公共 debug 证书签名,非项目私钥;若装过私签版需先卸载」
- **鸿蒙**: 未签 HAP **无法直接安装到正式真机**,需华为开发者账号 .p12 证书 + DevEco Studio 自动签名(或 build-profile.json5 配 signingConfigs 重编);notes 如实标注此限制,别假装能直接装
- 签名状态写进**资产文件名**(`-unsigned` / `-debug`),用户不读 notes 也能判断安装前是否要补签名

## Tauri v2 应用发版(2026-10 CraftCraft v0.2.0 实测)

`npm run tauri build` 一条命令跑完 前端构建 + cargo release + bundle,产物:
```
src-tauri/target/release/bundle/dmg/<ProductName>_<ver>_<arch>.dmg
src-tauri/target/release/bundle/macos/<ProductName>.app
```

- **版本号必须改三处**,漏一处就出错:`package.json`、`src-tauri/Cargo.toml`(`[package]` 段)、
  `src-tauri/tauri.conf.json`。dmg 文件名与 app 的 `CFBundleShortVersionString` 都取自
  tauri.conf.json;Cargo.toml 漏改会让 `--version` 与实际包名不一致。改完 grep 三处复核。
- ⚠️ **上传后资产名里的空格会变成点**:本地 `CraftCraft Launcher_0.2.0_aarch64.dmg` →
  远端 `CraftCraft.Launcher_0.2.0_aarch64.dmg`。手拼下载 URL 必须用**点**版,用空格版直接 404。
  稳妥做法:`gh release view <tag> --json assets --jq '.assets[].name'` 取真名再拼 URL。
- Tauri 产物路径含空格,`ls` / `stat` / `hdiutil` / `gh release create` 的参数全部整体加引号。
- `tauri build` 只出**本机平台**包。要三平台齐全(Windows exe / Linux deb)得走 GitHub Actions
  的 windows-latest / ubuntu-latest job,再把产物挂到同一个 Release。

### 最强验证:把下载回来的包挂载 + 查二进制

sha256 一致只证明"字节没坏",不证明"用户下到的这份真的带这版功能"。多走两步闭环:
```bash
curl -sL -o /tmp/dl.dmg "<release download url>"        # 用远端真名(点号版)
hdiutil attach /tmp/dl.dmg -nobrowse -mountpoint /tmp/vfy
/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" \
    "/tmp/vfy/<App>.app/Contents/Info.plist"             # 版本是否为新版
python3 -c "b=open('/tmp/vfy/<App>.app/Contents/MacOS/<bin>','rb').read();
print('probe:', b'tlh_aa' in b)"                         # 本次新增功能是否编进去
hdiutil detach /tmp/vfy
```
探针优先选项目里新增的明确字符串(语言表 locale 码、新功能文案、版本常量);
Rust/Go/C 按 UTF-8 搜,C#/.NET 按 UTF-16LE 搜(见上方「中文字符串验证」)。

## 建仓→推代码→发 Release 的正确顺序(2026-10 实测)

顺序错了会卡死。首次发布新仓库按这个次序：

```bash
# 1. 建仓 + About/topics(用户明确要求:About 格式 功能|平台产物|运行方式|技术栈)
gh repo create <owner>/<name> --private --description "功能 | 平台产物 | 本地运行 | 技术栈"
gh repo edit <owner>/<name> --visibility public --accept-visibility-change-consequences
gh repo edit <owner>/<name> --add-topic minecraft,launcher,tauri   # 逗号分隔

# 2. 推代码 —— 必须先有提交,tag 单独推
git remote add origin https://github.com/<owner>/<name>.git
git push origin main
git push origin v0.1.0

# 3. 建 Release + 传资产
gh api repos/<owner>/<name>/releases -f tag_name=v0.1.0 -f name="..." -f body="..."
gh release upload v0.1.0 "<path/to/artifact.dmg>"
```

- ⚠️ **空仓库不能建 Release**：零提交时 `gh api .../releases -f tag_name=...` 返回
  `422 Validation Failed / Repository is empty`，`git/ref/tags/<tag>` 返回
  `409 Git Repository is empty`。这不是 API 用法问题，是**顺序问题**——先 push 代码和 tag。
- ⚠️ **传资产用 `gh release upload <tag> <path>`，别手搓 assets API**（2026-10 实测三个反例）：
  - `gh api .../releases/<id>/assets -F name=... -F file=@<path>` → `accepts 1 arg(s), received 2`
  - 手打 `uploads.github.com/.../assets?name=...` + `--data-binary` → `400 Multipart form data required`
  - `gh release upload` 一条命令就成功（7MB dmg 零报错），是首选。
- ⚠️ **路径含空格**（`CraftCraft Launcher_0.1.0_aarch64.dmg`）：必须整体加引号；本次连续 3 次
  `stat` / `test -f` 因空格被拆成两个参数而误判"文件不存在"。先 `ls -la "$PATH"` 确认存在，再传。

**先试直连 `git push`，别一上来就搭中继**（2026-10-31 实测代价 ~15 轮）：
记忆里"本机 git push 不通、必须走 ECS 中继"可能是**过期**结论。本次照记忆先搭中继，连续失败
（ECS 是 Windows 无 bash → 内联 PowerShell 引号反复解析失败 → 服务器 `git clone` 走 HTTPS 报
`Connection was reset`），最后裸 `git push origin main` **一次就成功**。
正确判据：`curl -s -m 5 -o /dev/null -w "%{http_code}" https://api.github.com/` 得 200 →
**直接跑 `git push` 并给足 60s**；真失败再上中继，且优先修网络而不是自写 relay 脚本。

## Pitfalls(真实踩坑)

- **推 tag 不推分支**: `git push origin v1.0.0` 之后 Release 指向的 commit 可能不在远端。发布前确认 `git push origin HEAD` 已执行,用 `git status` 看是否领先 origin。
- **`gh release upload` 成功时「什么都不打印」**: `--clobber` 覆盖上传成功后 stdout 为空、exit 0（实测 2026-10/11 连续两次）。**空输出 ≠ 失败**，但也**不能当成功**——必须立刻查 digest：
  ```bash
  gh release view <tag> --json assets --jq '.assets[]|{name,size,state,digest}'
  # 与本地 shasum -a 256 + stat -f %z 逐字比对
  ```
  判成功的三件套：`state=uploaded` + `size` 与本地字节一致 + `digest` 与本地 sha256 逐字相同。
  只看到 exit 0 就报"上传成功"是错的（可能只是没覆盖上）。
- **`state: uploaded` 只是 API 状态**: `gh release view --json assets` 说 uploaded 不等于真能下载。必须 curl 范围请求(HTTP 206)+ sha256 对照才算真验证。
- **上传即验证窗口**: 创建 Release 后立即做下载验证,此时发现问题(资产损坏/404)还能删掉重建;拖到用户下载才发现就晚了。
- **路径含空格**: ditto/curl 的目标路径一律加引号,`Media\ Converter.app` 这类裸转义在变量展开时会失效。
- **`gh release view --json` 字段名错误会整体失败**: 顶层没有 `updatedAt`(在 assets 数组的每个元素里),传错字段 gh 报 `Unknown JSON field` 且**不输出任何 JSON**——下游 json.load 会收到空输入报 JSONDecodeError。先 `gh release view --json <field> 2>&1` 看报错里的 Available fields 列表,再取正确字段;资产时间用 `assets[0].updatedAt`。
  - **顶层可用字段白名单(2026-10 实测)**: apiUrl, assets, author, body, createdAt, databaseId, id, isDraft, isImmutable, isPrerelease, name, publishedAt, tagName, tarballUrl, targetCommitish, uploadUrl, url, zipballUrl。**没有 `state`**——`gh release view v1.0.0 --json state` 会直接报 `Unknown JSON field` 并整体失败;资产状态只能从 `assets` 里取:`gh release view v1.0.0 --json assets --jq '.assets[].state'`。
- **gh 命令的网络**: 先 `curl -s -m 5 -o /dev/null -w "%{http_code}" https://api.github.com/` 探测直连(200=通)。直连通就裸跑;只有直连不通才 `export HTTPS_PROXY=http://127.0.0.1:1082`(本机 MacPacket 代理)再跑 gh/git push/curl。部分机器 1082 是死代理(连接拒绝),此时盲套代理反而全挂——以探测结果为准,别默认要代理。(2026-09 实测:本机 api.github.com 直连 200,全程未配代理。)
- **curl 下载 Release 资产的 URL 别走 command substitution**: `curl -o x.ipa "$(gh release view ... --jq .assets[].browser_download_url)"` 在 gh 输出空/带换行时报 `option : blank argument where content is expected`,极难排查。稳妥写法: URL 手拼 `https://github.com/<o>/<r>/releases/download/<tag>/<file>`,或 `-r 0-1023` 范围请求单独测。
- **github.com 直连不通时,走 API 资产端点全量下载(必须带 Accept 头)**: `gh api repos/<o>/<r>/releases/assets/<id>` 返回的是资产 JSON;取二进制要加 `-H "Accept: application/octet-stream"`,curl 会 302 跳到 release-assets.githubusercontent.com,`-L` 跟随即可拿到完整包(2026-10 HermesKeeper 实测 90107B 全量下载成功)。**坑: 不带该头时 curl 拿到的是 ~1.7KB 的 JSON 元数据,照样 HTTP 200——必须比对字节数/计算 sha256 与本地一致才能确认真的拿到了二进制,不能只看 HTTP 200**。gh 的 `--jq` 输出带换行,进 curl 前 `tr -d '"'` 清理。
- **tag 触发自动发布 workflow 的重触发（2026-09 实测 3 轮）**: release workflow 只在 tag **ref 被推送**时触发；发版 job 失败后只 push main 的修复提交**不会**重跑 release（那只触发 ci.yml）。重发 = 把 tag 强制移到修复 commit 再推:
  ```bash
  git push origin main                  # 修复提交先上 main
  git tag -f v1.0.0                     # 重指到新 HEAD（注意: git tag 没有 -q 开关,`git tag -f -q` 报 unknown switch）
  git push -f origin v1.0.0             # 强推同名牌,workflow 才会重新触发
  ```
  轻量 tag 时 `git rev-parse v1.0.0` 即 commit SHA，可核对 tag 指向；同 tag 名会先后产生多个 run（ci + release 各一），别把旧的失败 release run 当最新——后台监控旧 run 的 watch 通知也会迟到误报，以 tag 当前指向的 commit 对应的 run 为准。
  ⚠️ **强推 tag 后旧 run 不会自动消失（2026-10-05 WeChatExporter v2.19.3 实测）**: `git tag -f` + `push -f` 只触发**新的** release run，**旧 run 仍在跑**——它基于旧 commit 构建，跑完会把资产挂到同名 release 上覆盖新资产。强推 tag 的同时**必须取消旧 run**：`curl -X POST -H "Authorization: token $TOK" https://api.github.com/repos/<o>/<r>/actions/runs/<old_run_id>/cancel`（202=已取消；已终态的 run 返回 409，无害）。找旧 run：`GET .../actions/runs?per_page=5&created=%3E<时间戳>` 列 created_at 早于强推时刻且 in_progress 的 run。tag 强推走 git 通道（ECS relay）时取消 action 走本机 api.github.com（token `gh auth token`，40 字符），两边可并行。
- **中文字符串验证**: `strings` 默认只输出 ASCII,查中文标签会误报"没编译进去";用 python 字节扫描 `'完成'.encode() in open(bin,'rb').read()`。
- **macOS 打包路径**: `ditto -c -k --sequesterRsrc --keepParent` 保留签名与资源分支;版本号从 Info.plist 读,别硬编码。
- **git 传输被 DNS/代理卡死时,tag/Release 改走 API**(国内网络常见): `git push` 先报 `HTTP2 framing layer`, 再报 `Failed to connect ... port 443`; `--resolve github.com:443:<IP>` 与临时 `/etc/hosts` 有时仍被 HTTP2 卡死。此时**别卡在 push 上**——`gh` 走 api.github.com(通常没被污染),直接用 API 建 ref + 发 Release:
  ```bash
  SHA=$(gh api repos/<owner>/<repo>/commits/main --jq .sha)
  # 创建 tag 用 POST(不是 PUT; PUT 会 422 "Reference does not exist")
  gh api -X POST repos/<owner>/<repo>/git/refs -f ref=refs/tags/v1.0.0 -f sha=$SHA --jq .ref
  gh release create v1.0.0 <asset> --title "..." --notes "..."
  ```
  注意 `git -c http.version=HTTP/1.1` 的 `-c` 必须放在 `git` 之后、`push` 之前(`git push ... -c` 会把 `-c` 当 push 选项报错)。API 建的 tag 指向 main 当前 SHA, 后续本地有新提交时等网络恢复再补 `git push`。

## 本机 GitHub 完全不可达时的中继推送（2026-09 实测）

场景：本机（第二台 Mac）github.com / api.github.com 的 HTTPS 被重置、ssh.github.com:443 也被代理拦成 198.18.x 假 IP → gh 与 git 全线失败。⚠️ 此时 `gh auth status` 会**误报** `The token in keyring is invalid`——那是网络不通，不是 token 死了。判据：到一台能连 api.github.com 的机器上验一次，只有返回 401 `Bad credentials` 才是真失效（实测本机报 invalid、同一 token 在服务器上用是好的，40 字符）。

中继推送（借一台能连 GitHub 的机器，例：阿里云 ECS，其 clone 的 remote = `ssh://git@ssh.github.com:443/<owner>/<repo>.git`）：

```bash
# 本机：commit + tag 后做【增量】bundle（实测几 KB，别传整个仓库）
git bundle create /tmp/fix.bundle refs/tags/v1.0.1 ^<中继机上已有的 commit>
git bundle verify /tmp/fix.bundle      # 确认 prereq 就是中继机已有的 commit
scp /tmp/fix.bundle relay:C:/fix.bundle

# 中继机：fetch bundle 的对象 → 按 SHA 推送（提交 SHA 与本机完全一致，不是重做一份提交）
git fetch C:/fix.bundle +refs/tags/v1.0.1:refs/tags/v1.0.1
git push origin refs/tags/v1.0.1
git push origin <sha>:refs/heads/main
git fetch origin && git merge --ff-only origin/main   # 顺手让中继机 clone 跟上，别留个落后的副本
```

- ⚠️ **SSH over 443 会偶发抖动**：同一条命令可能报 `Permission denied (publickey)`（假权限错误——`ssh -T -p 443 -i <key> git@ssh.github.com` 若回 `Hi <owner>/<repo>! You've successfully authenticated` 就证明密钥有效）或 GitHub `remote: Internal Server Error`（带 request id）。**带重试（4–8 次、间隔 5s）+ 显式 `GIT_SSH_COMMAND="<ssh.exe> -p 443 -i <key> -o IdentitiesOnly=yes"` 就成功**；不要因一次失败去改部署密钥或断定它是只读。
- ⚠️ **token 别经工具 stdout 传递**：`gh auth token` 直接打印会被掩码成 `gho_i5...6MMd`（13 字符），拿它调用必然 401。写文件再传：`gh auth token > /tmp/tok` → scp → `open(path).read().strip()`（`${#TOK}` 应为 40）；用完删掉。
- ⚠️ 中继机上的可达性是**部分可达**：实测 github.com 直连被重置、api.github.com 与 *.githubusercontent.com 直连可用，而机器上的代理反而全挂（带代理一律 `Recv failure: Connection was reset`）→ 逐 host 实测再决定用不用代理，别默认"代理更稳"。
- ⚠️ 中继机上 ssh 内联 PowerShell / 复杂引号会被吃（报 `/private/tmp.created_at: No such file` 之类莫名字符串）→ 脚本本地 write_file 写好再 scp 过去执行，不要内联拼命令。

## 免全量下载的产物内容核验（慢链路 / 被封时）

需求：证明"Release 里那个可执行文件真的含本次修复"，但整包 80MB 而链路只有 ~12KB/s（全量 1 小时+）。做法：走 Release **asset API 端点**（`Accept: application/octet-stream`）拿 302 直链，再用 range 请求**只取 ZIP 里那一个成员**：

1. `curl -I -H "Accept: application/octet-stream" .../releases/assets/<id>` → 取 `Location:`（指向 `release-assets.githubusercontent.com`）
2. range 取尾部 256KB → 解析 EOCD（`PK\x05\x06`，cd_size@12 / cd_off@16）→ 中央目录条目用 `<4s6H3I5H2I` 解（comp_type@10 / comp_size@20 / uncomp_size@24 / nlen@28 / elen@30 / lho@42；**格式串写错会报 `unpack requires a buffer of 42 bytes`**）
3. range 取该成员 local header（30B）→ 数据偏移 = lho+30+nlen+elen；再 range 取 `comp_size` 字节 → `zlib.decompress(raw, -15)`（comp_type=8）
4. 在解出的二进制里搜预期文案（C#/.NET 字符串常量在 #US 堆 → 按 **UTF-16LE** 搜；Go/Rust/C 用 UTF-8）

实测：83051640 字节的 Windows 包只传输 ~400KB 就取出 `WeChatExporter.dll`（373760B，与 central dir 记录一致）并命中 4 条新增中文文案，比全量下载快两个数量级。
脚本：`scripts/verify-release-artifact-member.py`（repo/tag/asset/member/待搜文案全部参数化，在能连 api.github.com 的机器上跑）。

## 参考

- `templates/release-notes-multiplatform.md` — 多端统一发行的 Release notes 模板(资产清单表 + 每端安装说明 + 签名约定 + E2EE/自部署指引),配合「多端统一发行」节用。
- `scripts/verify-release-artifact-member.py` — 免全量下载核验 Release 资产内某个 ZIP 成员（range 取中央目录 + 目标成员 → inflate → 中文/字符串按 UTF-16LE 搜）；在能连 api.github.com 的机器上跑，参数化 repo/tag/asset/member/probe。
- `scripts/download-release-asset.sh` — github.com 直连抖动时经 API 资产端点（带 `Accept: application/octet-stream`）全量下载 Release 资产并与本地构建比对 size + sha256 的验证配方（2026-10 HermesKeeper 实测 90107B 逐字一致；漏 Accept 头会静默拿到 1.7KB JSON 元数据）。
- 本技能来自 MediaConverter v1.0.0 发布实践(2026-08): 全流程 + 双验证(API 层 + 真实下载)跑通。
