---
name: hermes-weixin-integration
description: "接入/排障 Hermes 微信通道(iLink 个人微信+企微)。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hermes, weixin, wechat, wecom, gateway, ilink]
---

# Hermes 微信接入 (hermes-weixin-integration)

## When to Use

- 用户说"把你接入我的微信 / 微信里也能用 / 接微信机器人"
- 微信通道收不到消息、不回复、gateway 里 weixin 连不上
- 需要给微信配 home channel(cron/通知推到微信)
- 顺带适用: hindsight 记忆报 `Database migration failed`(embedded PG 没跑)

**用途**: 把 Hermes 接到微信并保证长期可用。三条通道:
1. **个人微信 — iLink Bot**(扫码登录,长轮询,无需公网)← 用户说"接入我的微信"通常指这个
2. **企业微信 wecom**(AI Bot WebSocket,需企微后台创建机器人)
3. **企业微信 wecom_callback**(自建应用 + 公网回调,需 corpid/token/aeskey)

**决定性事实**: Hermes **支持个人微信**(`gateway/platforms/weixin.py`,腾讯 iLink Bot),不要回答用户"个人微信没法接"。查文档 `website/docs/user-guide/messaging/weixin.md` 与 `wecom.md`(本地仓库即权威)。

## 1. 个人微信(iLink Bot)接入步骤

```bash
# 0. 前置依赖(缺 qrcode 则二维码渲染失败)
~/.hermes/hermes-agent/venv/bin/python -m pip install -q qrcode aiohttp cryptography

# 1. 取二维码 —— 官方向导
hermes gateway setup        # 选 Weixin → 扫码 → 确认
```
`hermes gateway setup` 是交互式 TUI,agent 无法直接选菜单。**自动化做法**(用户只需扫桌面图片):
写脚本调用库函数 `gateway.platforms.weixin.qr_login("/Users/<u>/.hermes", timeout_seconds=600)`,
用自定义 stdout 捕获它打印的 `https://liteapp.weixin.qq.com/...` URL,立刻 `qrcode.make(url).save(~/Desktop/weixin_qr.png)`,
再让用户用微信扫码。成功后 qr_login 自己保存 `~/.hermes/weixin/accounts/<account>.json`。

```bash
# 2. 凭证写 ~/.hermes/.env (qr_login 不会自己写,需补)
WEIXIN_ACCOUNT_ID=<ilink_bot_id>
WEIXIN_TOKEN=<bot_token>
WEIXIN_BASE_URL=https://ilinkai.weixin.qq.com
WEIXIN_CDN_BASE_URL=https://novac2c.cdn.weixin.qq.com/c2c
WEIXIN_DM_POLICY=allowlist
WEIXIN_ALLOWED_USERS=<扫码者 ilink_user_id, 形如 xxx@im.wechat>
WEIXIN_HOME_CHANNEL=<同一 chat_id>     # 让 cron/通知默认推微信
WEIXIN_HOME_CHANNEL_NAME=微信

# 3. 常驻服务(开机自启 + 崩溃自动重启)
hermes gateway install --start-now --start-on-login
hermes gateway status
```

## 2. 验证(必须双向都验)

```bash
# 入站: 让用户在微信发一条, 然后
grep -a -E "inbound message|weixin connected" ~/.hermes/logs/gateway.log | tail
grep -a "platform=weixin" ~/.hermes/logs/agent.log | tail   # 会话是否用了预期模型

# 出站(不依赖用户配合): 直连 API 发一条
~/.hermes/hermes-agent/venv/bin/python -c "
import asyncio,os,sys,pathlib
for k in ('HTTPS_PROXY','HTTP_PROXY','https_proxy','http_proxy'): os.environ.pop(k,None)
for l in (pathlib.Path.home()/'.hermes'/'.env').read_text().splitlines():
    if '=' in l and not l.strip().startswith('#'): k,v=l.split('=',1); os.environ[k.strip()]=v.strip()
sys.path.insert(0,'/Users/yourname/.hermes/hermes-agent')
from gateway.platforms.weixin import send_weixin_direct
print(asyncio.run(send_weixin_direct(extra={},token=None,chat_id='<chat_id>',message='测试')))
"   # 期望 {'success': True, ...}

# 或走 home channel
hermes send --to weixin "测试"
```

## 3. 坑位(pitfalls,实测踩过)

- **死代理会让 aiohttp 失败**: 本机 `HTTPS_PROXY=127.0.0.1:1082` 是死代理,`aiohttp.ClientSession(trust_env=True)` 会读它 → 脚本里先 `os.environ.pop('HTTPS_PROXY'/'HTTP_PROXY'/...)`。curl 同理需 `env -u HTTPS_PROXY`。
- **`hermes send --to weixin:<chat_id>` 会报 "Could not resolve"**: CLI 解析依赖已发现的 channel 目录(新接入时为 0)。解法:先写 `WEIXIN_HOME_CHANNEL`,再用 `hermes send --to weixin "..."`;或直接用 `send_weixin_direct`。
- **`send_weixin_direct` 裸跑报 token missing**: 它读环境变量,裸 python 进程不加载 `.env` → 需手动解析 `.env` 注入 `os.environ`(见上)。
- **二维码过期**: `qr_login` 内部会刷新并重新 print URL,但自己生成的 PNG 不会自动更新(只在首次生成)。用户超时未扫就重跑脚本。
- **iLink 是 bot 身份,不是你的微信号**: account 形如 `xxxx@im.bot`。私聊可靠;普通微信群一般拉不进去、群内 @ 常收不到事件(官方文档警告)。别承诺群里能用。
- **DM 策略**: 用 `allowlist` + 扫码返回的 `ilink_user_id`(不是微信号、不是手机号)。留空则退化为 pairing,需 `hermes pairing approve`。
- **gateway 与 CLI 会话模型不同源**: 运行中的会话快照启动时的模型;`agent.log` 里 `model=... provider=... platform=weixin` 才是微信会话真实用的模型。
- **`pkill -f hindsight` 会误杀 embedded PostgreSQL**(其命令行含 `hindsight-embed-hermes` 数据目录)→ 用精确 pid 或 `pg_ctl stop`。

## 4. 企业微信(wecom)速查

- 扫码建机器人: `hermes gateway setup` → 选 WeCom(自动创建应用并取 bot_id/secret)
- 手动: 企微管理后台 → 应用 → 创建 AI Bot → 复制 Bot ID / Secret
- `.env`: `WECOM_BOT_ID` / `WECOM_SECRET`(可选 `WECOM_HOME_CHANNEL`、`WECOM_ALLOWED_USERS`)
- 特点: WebSocket 常连、不流式、无 typing 指示;支持图片/文件/语音/视频与 markdown

## 5. 附带:hindsight 记忆依赖的 embedded PostgreSQL 看护

hindsight daemon **不会自己拉起** embedded PG(只复用已在跑的),PG 不在则报 `Database migration failed` → 记忆工具全挂。
看护服务(已部署): `~/Library/LaunchAgents/ai.hermes.hindsight-pg.plist` → 脚本 `~/.hermes/scripts/hindsight-pg-keepalive.sh`
(检测 `pg_isready` 失败则 `pg_ctl start`,开机自启 + 每 300s 自愈)。PG 二进制 `~/.pg0/installation/18.1.0/bin`,
数据目录 `~/.pg0/instances/hindsight-embed-hermes/data`。**勿用 `pkill -f hindsight`**。
