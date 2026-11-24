---
name: gh-actions-ssh-deploy
description: "Use when 配 GitHub Actions 走 SSH 部署:密钥存 secret 卫生与手动触发。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [github-actions, ssh, deploy, secrets, ci]
    category: devops
---

# GitHub Actions → SSH/SCP 部署到远程服务器

## When to Use

- 给仓库配「CI 编译 → scp/ssh 部署到远程服务器」的 workflow,GitHub secret 要存 SSH 部署密钥时
- CI 卡在 `Permission denied (publickey)` / `error in libcrypto` 要定位是密钥卫生问题还是服务端问题
- 手动触发部署 workflow、重跑某次 run
- 部署后健康检查挂 CI:服务端 watchdog 自愈窗口竞态、公网 CF 域 GitHub 出口被 bot 管理 403、Windows 远程 shell 诊断

只收录**已验证**的密钥/secret 卫生与触发手法;服务端(尤其 Windows OpenSSH)排障见 aliyun-workbench-cli
「Windows 实例跑 PowerShell 的坑」一节。

## 存 SSH 部署密钥:单行 base64,绝不存原始 PEM

明文多行 PEM 粘进 GitHub secret 会丢换行 → runner 上 `ssh`/`ssh-keygen` 报
`error in libcrypto` 或 `Permission denied (publickey)`,且**极难肉眼排查**
(密钥看着正常,解出来却缺 `\n`)。一律存单行 base64:

```bash
# 存(单行 base64,抗换行截断)
gh secret set SERVER_DEPLOY_KEY -R owner/repo <<<"$(base64 < ~/.ssh/id_ed25519 | tr -d '\n')"

# 回读校验(必须与本地逐字节一致才进 workflow)
gh secret view SERVER_DEPLOY_KEY -R owner/repo | base64 -d | diff - ~/.ssh/id_ed25519 && echo OK
```

workflow 侧(解码 + fail-fast):

```yaml
- name: Prepare deploy key
  run: |
    mkdir -p ~/.ssh && chmod 700 ~/.ssh
    echo "${{ secrets.SERVER_DEPLOY_KEY }}" | base64 -d > ~/.ssh/id_ed25519
    chmod 600 ~/.ssh/id_ed25519
    ssh-keygen -l -f ~/.ssh/id_ed25519   # 坏密钥在这里就挂,不带病走到 scp/ssh
```

## secret 的 404 不是权限问题

- `gh api repos/o/r/actions/secrets/NAME`(GET/POST 单条)**secret 不存在时返回 404 Not Found**,
  长得像「token 缺 scope」,但其实是「还没建」。别在这上面耗时间查权限。
- 正确姿势:直接用 `gh secret set NAME -R o/r`(POST 创建语义),再
  `gh api repos/o/r/actions/secrets` 只列名确认存在。
- org 级 `/orgs/<o>/secrets/<n>` 是**另一套** RSA 加密 API,别拿仓库 secret 去打。

## 手动触发 / 重跑

```bash
gh workflow run deploy-server.yml            # workflow_dispatch(必要时加 --ref main)
gh run list --limit 3                        # 看最新 run
gh run view <id> --log | grep -E "×|##\[error\]|Permission" | head   # 只看失败点
gh run view <id> --log-failed                # 只失败 step
```

## run: 标量折叠坑(2026-11-24 结案:旧"已知硬骨头"的真凶在此)

旧版"已知硬骨头"描述的「同把 key 从 Mac 通、从 GitHub runner 被拒, lookup_sid 1332」**不是源 IP / LSA / credential agent 问题**, 真凶是 workflow 里 ssh 续行命令用了 `run:` 普通 YAML 多行标量: 反斜杠+换行被折叠成空格, bash 把「\+空格」当转义空格, 前导空格粘进 user@host 参数 → ssh 把用户名发成 ` ci-deploy`(带前导空格) → 服务端查无此用户 → 1332 拒绝。重启 sshd / 重启 ECS 实例自然都无效。

**规则: workflow 里 ssh/scp 多行续行一律 `run: |` 块风格, 禁用普通标量:**

```yaml
# ❌ 错: 普通多行标量, 续行的反斜杠+换行被折叠成「\+空格」→ 前导空格粘进用户名
run: ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes \
  ci-deploy@1.2.3.4 "echo ok"

# ✅ 对: run: | 块风格, 反斜杠+换行原样保留
run: |
  ssh -i ~/.ssh/id_ed25519 -o BatchMode=yes \
    ci-deploy@1.2.3.4 "echo ok"
```

铁证定位法: 服务端 `sshd -E` DEBUG3 日志对比两条连接的用户名行——正常 `userauth-request for user ci-deploy`(user 后 1 个空格) vs 异常 `for user  ci-deploy`(user 后 2 个空格, 前导空格已粘进用户名)。回归防护: 对 workflow 的 `run` 体断言「含反斜杠+换行」, 有人改回普通标量立即 FAIL。

## 部署后健康检查: 两层设计(权威层判成败 + 信息层不阻塞)

- **权威层**: SSH 到服务端 `curl -s -m 10 http://127.0.0.1:<port>/api/health`。重试窗口必须**盖过服务端自愈周期**——有每分钟 watchdog 时, 3×15s 会全撞 node 重启间隙误判失败, 6×15s(90s) 才稳。远程命令带诊断 `curl.exe ... 2>&1; echo CURLRC_$LASTEXITCODE`(Windows OpenSSH 默认远程 shell 是 PowerShell; CI 的 bash 侧写 `\$LASTEXITCODE` 转义, `$` 会被 bash 先解析)。`curl -s` 会静默吞连接错误, 必须带 stderr+退出码否则空输出查不出原因。
- **信息层(不阻塞)**: 公网域走 Cloudflare 时带浏览器 UA 重试, 非 200 只 warning 不 exit 1。GitHub runner 是数据中心出口 + 裸 curl 特征, **常被 CF bot 管理间歇拦 403**(同一 run 内一会 200 一会 403), 403 ≠ 部署失败, 别让它挂 CI。改 CF WAF/bot 策略须用户明确指令(云端配置不擅动)。
- 定位 403 来源: 本机直探 `127.0.0.1:<port>` 得 200 + 公网响应头 `server: cloudflare` → 403 在 CF 层而非本机 nginx。
