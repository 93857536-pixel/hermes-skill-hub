---
name: open-source-publishing
description: "Use when 把项目开源发布到 GitHub:隐私清理、占位化、README 配置清单、建仓推送、远程验证。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [github, open-source, privacy, publishing, release]
    category: github
---

# 开源发布(GitHub,隐私清理优先)

## When to Use

- 用户要把项目/成品开源发布到 GitHub 时
- 需要保证仓库不含任何隐私(邮箱/IP/密钥/个人域名/服务器信息)时
- 需要写 README「配置清单」让使用者自己填时

## 核心原则(用户硬性要求,2026-08-17 实测)

1. 发布前必须隐私审查:仓库零真实凭据、零个人邮箱、零服务器 IP、零个人域名(除非用户明确要求保留,如在线体验链接)
2. README 必须写「你需要自己填的配置」清单:每项给环境变量名、是否必填、怎么获取(典型坑:SMTP **授权码≠邮箱密码**,要说明在邮箱设置里开启 SMTP 服务生成)
3. 交付时把「刻意保留的内容」(README 在线体验链接、GitHub 用户名署名)明确列出让用户决定去留——用 clarify 问,别擅自删

## 步骤

### 1. 隐私审查(工作区 + git 历史,两处都要扫)

```bash
# 工作区扫描(排除 node_modules/dist/.git)
grep -rInE --exclude-dir=node_modules --exclude-dir=dist --exclude-dir=.git \
  '<你的邮箱>|<服务器IP>|<个人域名>|cfat_|LTAI|AKIA|AKID|BEGIN (RSA|OPENSSH|EC) PRIVATE|sk-[A-Za-z0-9]{20,}' .

# git 历史内容扫描(关键:已删除的凭据文件、提交作者邮箱会留在历史 blob)
git log -p --all | grep -iE '邮箱|IP|api.?key|password|secret'
git rev-list --objects --all | awk '{print $2}' | sort -u   # 历史中出现过的文件名
git log -1 --format='%an <%ae>'                              # 作者邮箱
```

检查重点:config 默认值(如 CORS_ORIGIN)、deploy/*.ps1、docs/*.md、README、git 提交作者。

### 2. 占位化(替换而非删除,保持模板可直接用)

- 域名占位用 **`your-domain.example`**:是合法域名语法,nginx `server_name`、CSP `connect-src wss://...`、健康检查 URL 里都能直接替换;不要用 `<你的域名>` 尖括号形式(会破坏配置语法)
- 文档(md)里邮箱/IP 用 `<你的邮箱>` / `<你的服务器IP>`;脚本(ps1)里改成 `Read-Host` 交互输入最稳
- 代码默认值:敏感默认值改成开发默认 + 注释「生产必须设置 XX 环境变量」(例:corsOrigin 默认 `http://localhost:5173`)
- .gitignore 补漏:`*.tsbuildinfo`、`*.local` 等构建缓存
- PowerShell 5.1 兼容:注释里也别写 `Let's`(撇号在无 BOM+GBK 环境可能破坏解析);Read-Host 的参数引号是合法语法

### 3. README(宣传 + 配置清单)

- 顶部:标语、shields.io 静态 badges、在线体验链接(用户要推广才放,先确认)
- 功能对比表 + 快速开始:不想折腾 → 直接在线体验;想自部署 → 5 分钟 dev 模式命令
- ⚙️「你需要自己填的配置」表格:环境变量 / 必填? / 说明(含授权码获取方式)
- E2EE/安全原则、技术栈、目录结构、文档链接、LICENSE(MIT 模板)
- 加一句「仓库不含任何真实密钥,全部走环境变量」的隐私声明

### 4. git 重新初始化(历史含个人邮箱时最干净)

```bash
rm -rf .git && git init -b main
git config user.name "<github用户名>"
git config user.email "<github用户名>@users.noreply.github.com"   # noreply,不暴露真实邮箱
git add -A && git status --short   # 逐个确认暂存清单
git commit -m "..."
```

### 5. 建仓推送(gh)

**先探测直连,别盲套代理(2026-09 实测)**: 部分机器 1082 代理是死代理(连接拒绝/超时),强行 export 反而把可用的直连搞挂:

```bash
curl -s -m 5 -o /dev/null -w "%{http_code}" https://api.github.com/   # 200 → 直连可用
```
直连通 → 确保 `unset HTTPS_PROXY HTTP_PROXY` 后裸跑 gh/git;不通 → 才 export 代理并按 gh 诊断步骤排查。

```bash
export HTTPS_PROXY=http://127.0.0.1:1082   # CLI 访问 GitHub 需走代理
gh repo create <name> --public --source . --remote origin --description "..." --push
gh repo edit <owner>/<name> --add-topic e2ee,privacy,react,...   # 推广标签 5-10 个
```

- **⚠️ 仓库 description 是用户硬性要求(2026-08-25)**: 每个新建仓库必须设置 About 栏 description,格式固定为 `功能 | 平台产物 | 运行方式 | 技术栈`。基准样例: WeChatExporter = `微信聊天记录导出 | macOS DMG + Windows | 本地运行 | Swift + WPF`;VoiceNotes = `语音转文字 + AI 会议纪要 | macOS DMG + Windows | 本地运行 | Swift + WPF`。只改 README 不算数——用户明确指正过"大标题底下"指的是 GitHub 页面 About 栏,必须 `gh repo edit --description` 设置。同时补 5-10 个 topics(语言/平台/功能关键词)。
  **更新已有仓库时 description 与 topics 是两个独立 API 调用(2026-09-25 实测)**:
  `gh api repos/<o>/<r> -X PATCH` 只设 `description`——topics **不会**随 PATCH
  生效(返回体里 topics 仍是旧值,极易误判"已改好");topics 必须单独
  `PUT repos/<o>/<r>/topics`,body 是 `{"names": [...]}` **全量替换**(非追加,
  先 `GET .../topics` 读旧值拼新值)。改完两边都要回读
  `gh api repos/<o>/<r>/topics --jq .names` 验证。
- `gh api` 503 / push `SSL_ERROR_SYSCALL` = GitHub 或代理临时抖动,重试(最多 5 次,间隔 4s),不是凭据问题
- 刚建的无协作者仓库,`git commit --amend` 后 `git push --force` 安全
- 仓库创建成功但 push 失败的场景:先成功创建、后单独重试 push(`git push -u origin main`)

### 6. 远程验证(不能只信本地)

```bash
# 列出远程仓库所有文件,确认无敏感文件
gh api repos/<owner>/<repo>/git/trees/main?recursive=1 --jq '.tree[].path' \
  | grep -iE 'env\.json|admin\.cred|jwt\.secret|\.pem$|authorized_keys' || echo "远程干净"
```

## Pitfalls

- **只放二进制/安装包、不放源码时,源码里的隐私扫描不覆盖二进制**: 用户说「不要源码,只要能用」→ 发布 Release 附 IPA/zip/exe。此时源码 grep 扫不到编译进二进制的凭据(如阿里云 PNS/号码认证 AppEncryptInfo、第三方 SDK 的 AppKey/Secret、Firebase 配置、自建后端的 API 端点与域名)。交付前**主动清点一遍**: `grep -nE "appKey|appSecret|apiKey|secret|token" <主源码目录>`,凡命中且会进二进制的,在 README 或交付汇报里**如实标注「IPA 内嵌 XX SDK 凭据,敏感者可在控制台轮换该 AppKey」**,别默认用户知道。(2026-09 实测:某聊天App 公开 IPA 内嵌阿里云 PNS AppEncryptInfo,已主动向用户披露并建议轮换。)

  **判定规则:先做「暴露面等价」比较,再决定要不要清洗/轮换**(2026-10 实测,避免了两次不必要的破坏性操作)。命中内嵌凭据时先问一句:**这个字符串是否已经随你分发的二进制公开了?**
  - **客户端内嵌型**(SDK 设计上就要嵌在客户端:`setAuthSDKInfo`/AppEncryptInfo、Firebase 配置、Client Secret)→ 任何拿到安装包的人 `strings` 就能提取。若本仓库 Releases 正在分发该二进制,则**源码里出现它与「包已公开」是同一暴露面**:此时 ① 清洗源码属安全表演(收益≈0)② **不要**据此要求轮换(会打断已发货客户端的鉴权)③ **不要**为此重写 git 历史(SHA 全变、并行分支变孤儿,代价远大于收益)。正确动作:如实披露 + 说明「若要真正收紧,须在控制台轮换并改造成运行时下发」,把选择权交用户。
  - **服务端型**(AccessKey/Secret、JWT secret、DB 口令、SSH 私钥、后台 API token)→ **绝不能进仓库**;若只存在于未推送的本地提交里,**尚未推送 = 尚未泄露**,此时是最低成本窗口:优先**先改源码再推**(必要时才动历史),别等到推完再补救。
  - 拿不准就按「服务端型」从紧处理,但**在汇报里说清判断依据**,不要只给结论。
- **扫描模式别太宽**:GitHub 用户名(如 example-user)会命中「数字串」模式 → 敏感模式精确到邮箱形式(`example-user@qq\.com`),用户名/署名是刻意保留
- **README 里刻意保留的在线体验链接**会被扫描命中 → 断言改成「your-domain.com 只允许出现在 README.md」,不是零命中
- **本地 src 可能落后于线上运行逻辑**(尤其 dist 被直接改过的项目):发布前用「本地 tsc 编译 → diff 本地 dist vs 线上 dist」找差异,把线上逻辑同步回 src 再发布(详见 某个自建项目 skill 的同步方法)
- **编译产物对比要做等价归一**:空串初始化 vs undefined、单行 if vs 带大括号、CRLF——不归一就误报
- 线上 dist 目录可能有顶层残留旧文件(如 temp.js/chat.js 与 routes/ 下重复)→ 只比「本地存在的文件」
- 已验证后再改文件,记得 `git commit --amend` + force push 保持历史干净

## 验证

发布后跑 ad-hoc 验证脚本(模板见 `scripts/verify-publish.mjs`):tsc 编译 → 产物对比(等价归一)→ 敏感扫描(白名单式断言)→ 逻辑模拟 → 脚本兼容性。写临时脚本到系统 temp 目录,跑完即删。

## 相关

- github-repo-management:建仓/推送/release 的机械操作(本 skill 是其隐私/内容前置步骤)
- 某个自建项目:该项目 src↔dist 同步方法、已开源仓库状态
- aliyun-ecs:远程 PowerShell 引号坑、Windows 服务器部署
