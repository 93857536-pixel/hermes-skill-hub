---
name: hermes-messaging-gateways
description: "接入 Hermes 消息网关平台(微信/企业微信)。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [hermes, gateway, messaging, weixin, wecom, platform]
---

# Hermes 消息网关平台接入 (hermes-messaging-gateways)

## When to Use

**用途**: 把 Hermes 接到某个聊天平台(用户说"把你接入我的微信/企业微信/钉钉/飞书…"),或排查网关收发消息问题。

**触发时机**: 任何 `hermes gateway …`、"接入我的 X"、平台适配器/凭证/回调相关的请求。

## 0. 先查本地资料,再动手(顺序很重要)

1. 平台清单 = 插件目录 + 内置适配器:
   - `ls ~/.hermes/hermes-agent/plugins/platforms/` (a2a, buzz, dingtalk, discord, email, feishu,
     google_chat, homeassistant, irc, line, matrix, mattermost, ntfy, photon, raft, simplex, slack, sms,
     teams, telegram, wecom, whatsapp)
   - `~/.hermes/hermes-agent/gateway/platforms/*.py` = 内置适配器(**weixin 个人微信在这里**,
     `gateway/platforms/weixin.py`,不在 plugins 目录下;所以 `ls plugins/platforms | grep weixin` 为空 ≠ 不支持)
2. 该版本的权威文档在仓库里,优先于网站(版本匹配、离线可读):
   `~/.hermes/hermes-agent/website/docs/user-guide/messaging/<platform>.md`
   (已有: weixin.md 个人微信、wecom.md 企业微信机器人、wecom-callback.md 回调式、index.md)
3. `hermes gateway --help` 第一行就列出支持的平台族("Telegram, Discord, WhatsApp, Weixin, and more")。

## 1. 个人微信 (Weixin) —— 腾讯 iLink Bot,扫码登录

不需要公网、不需要 webhook、不需要企业资质。适配器用 iLink 长轮询 + AES-128-ECB 媒体加密。

**依赖**: `aiohttp` + `cryptography`(另装 `qrcode` 用于终端/PNG 二维码渲染),装进 hermes 自己的 venv:
`~/.hermes/hermes-agent/venv/bin/python -m pip install qrcode`

**最短路径(用户就在终端前)**: `hermes gateway setup` → 选 Weixin → 扫终端二维码 → 手机确认。
向导会调 `qr_login()`、把 `WEIXIN_ACCOUNT_ID / WEIXIN_TOKEN / WEIXIN_BASE_URL` 写进 `~/.hermes/.env`,
并询问 DM 授权策略;凭证同时由适配器存到 `~/.hermes/weixin/accounts/`。

**用户不在终端前 / 想让 agent 代跑时**: 用 `scripts/weixin_qr_login.py`(本 skill 自带):
调用同一个 `qr_login()`,把二维码渲染成 PNG 放桌面(用户双击 + 微信扫一扫),扫完自动把 `WEIXIN_*` 写进 `.env`:

```bash
~/.hermes/hermes-agent/venv/bin/python <skill_dir>/scripts/weixin_qr_login.py
# 后台跑 + tee 到日志,再从日志抓 [QR_IMAGE] / [QR_URL] 报给用户去扫
```

**关键 env**: `WEIXIN_ACCOUNT_ID` `WEIXIN_TOKEN` `WEIXIN_BASE_URL` `WEIXIN_CDN_BASE_URL`
`WEIXIN_DM_POLICY`(open|allowlist|pairing|disabled) `WEIXIN_ALLOWED_USERS` `WEIXIN_HOME_CHANNEL`。
iLink 默认 API `https://ilinkai.weixin.qq.com`;扫码数据用返回里的 `qrcode_img_content`(完整 liteapp URL),
不是 `qrcode` 十六进制串;状态机 wait → scaned / scaned_but_redirect(跟着 `redirect_host` 换 base_url 继续轮询)
/ expired(自动刷新,最多 3 次)/ confirmed(`ilink_bot_id` + `bot_token`)。

**必须提前告知用户的限制**(官方文档警告,别等用户踩坑):
- 扫码得到的是 **iLink bot 身份**(形如 `a5ace6fd482e@im.bot`),不是用户本人的微信号;
- 普通微信群一般拉不进 bot、群事件通常不投递到网关;可靠路径是**私聊这个 bot**;
- `WEIXIN_GROUP_POLICY` 只在 iLink 真投递群事件时才有意义。

**启动**: `hermes gateway run`(前台)/ `hermes gateway install && hermes gateway start`(常驻)。网关必须常驻才收发。

## 2. 企业微信 (WeCom) —— 两种模式

| 模式 | 凭证 | 是否需要公网 |
|---|---|---|
| AI Bot(推荐)WebSocket | `WECOM_BOT_ID` + `WECOM_SECRET` | 否(`wss://openws.work.weixin.qq.com`) |
| 自建应用回调 | `WECOM_CALLBACK_CORP_ID/CORP_SECRET/AGENT_ID/TOKEN/ENCODING_AES_KEY` | 需要公网回调 URL(可配 CF Tunnel) |

`hermes gateway setup` 选 WeCom 支持**扫码建 Bot**(自动建应用并取回 ID/Secret),失败才回退手填。
能力差异:WeCom 每次回复是**整条消息**,不流式、无 typing 指示。

## 3. 改 Hermes 配置的正确姿势(通用,踩过两次)

- **`patch` / `write_file` 工具会拒绝写 `~/.hermes/config.yaml`**("Refusing to write to Hermes config
  file")。必须走 CLI:`hermes config set <dotted.key> <value>` / `unset <key>` / `get <key>`。
  点路径可用(`providers.agnes-cn.key_env`、`auxiliary.vision.model`)。
- **CLI 写不了列表**:`hermes config set fallback_providers '[{...}]'` 会把整串 JSON 当**字符串**存进去
  (`get` 出来带引号,回退链失效)。列表型键要用 hermes 自带 venv 的 ruamel.yaml 原地改:

```python
# 用 ~/.hermes/hermes-agent/venv/bin/python 跑;ruamel 随 hermes 安装
from ruamel.yaml import YAML
p = "/Users/<user>/.hermes/config.yaml"
yaml = YAML(); yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)        # 保住原序列缩进风格
d = yaml.load(open(p))
d["fallback_providers"] = [{"provider": "...", "model": "...", "base_url": "..."}, ...]
yaml.dump(d, open(p, "w"))
```
  改完必须 `hermes config get <key>` 复核是列表结构,再 `hermes fallback list` 看真实生效顺序。
- `hermes config set` 会**重写整个 config.yaml 并丢掉尾部注释块**("Security / Fallback Model" 说明文字)。
  无害,但别误判成改坏;介意就先 `cp config.yaml config.yaml.bak.<原因>-$(date +%Y%m%d_%H%M%S)`。
- 改配置前先备份;用户偏好"只新增隔离配置、不动已有默认模型/密钥"。

## 4. 坑位

- **死代理会让适配器静默失败**:本机 `HTTPS_PROXY=127.0.0.1:1082` 是死代理,而 aiohttp
  `ClientSession(trust_env=True)` 会读它 → 脚本开头 `os.environ.pop()` 掉所有 `*_PROXY`;
  curl 侧用 `env -u HTTPS_PROXY -u HTTP_PROXY …` 或 `--noproxy '*'`。
- **二维码有效期很短**(约 5 分钟):生成后立刻让用户扫;`qr_login` 会自己刷新并重印 URL,
  但自写脚本的 PNG 只在**首次**抓到 URL 时生成,过期要重新跑脚本(别让用户扫旧图)。
- **凭证写进 .env 后要重启网关**才生效,再 `hermes gateway status` 验证。
- **网关必须常驻**(`run` 或 `install`+`start`);CLI 会话里 cron 的输出不会推回终端。
- **iLink 出站 ~30s sendmessage 冷却限流(2026-11-14 实测)**:weixin 出站密集发送会触发 `iLink sendmessage rate limited; cooldown active for 30.0s`(gateway.log),且**每次重试都会重新打开 30s 电路** → 连环重试永远发不出去(实测 8 分钟连环 8 次全撞冷却)。纪律:撞限流后**停一切出站 ≥60s,再只发一次**。入站(用户发的消息)完全不受限流影响,"用户能发消息、Hermes 发不出"多数是出站冷却,不是通道故障。
- **`hermes send` 报 "Sent to weixin home channel" ≠ 送达**:CLI 是乐观入队即报成功,网关侧实际可能撞限流失败。验证:发送后 `grep -E "rate limited|Sending" ~/.hermes/logs/gateway.log | tail` 看发送时间点之后有无新 `Sending` 行且无 rate limited;文件类(`MEDIA:<绝对路径>`)最终仍需用户确认收到。

## 5. 排障:平台回复慢(多半是模型 API 延迟,别怪平台)

用户说"某平台回得慢"时,先定位是**平台收包慢**还是**LLM 调用慢**——多数时候是后者,盲目调平台配置是浪费。

1. `~/.hermes/logs/gateway.log`:找 `inbound message`(收包)与 `response ready: ... time=NNs api_calls=N`(完成)日志对 = 端到端耗时;`inbound from=...` 与 `inbound message` 只差几秒 = 平台侧正常。
2. `~/.hermes/logs/agent.log`:`API call #N: model=... provider=... latency=Xs` 逐调用耗时;单调用几十秒、整条消息 time=160s+ → 延迟在模型 API 侧。
3. 节点压测对比(几秒出结论):
   ```bash
   curl -sS -o /dev/null -w "ttfb=%{time_starttransfer}s total=%{time_total}s\n" \
     -X POST <base_url>/chat/completions -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"<model>","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
   ```
   实测案例(2026-09):同模型 agnes-3.0-flash,国际站 apihub.agnes-ai.com 首字 17~42s,中国站 api.agnes-ai.cn 首字 0.8s——50 倍差。

**修复 + 重启**(provider 类配置改完必须重启网关):
- `hermes config set model.provider <节点>` + `hermes config set model.base_url <url>`(两站 key 不通用时换 key_env 对应节点,见 references/agnes-dual-site-provider.md)
- launchd 常驻(macOS): `launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway`;或 `hermes gateway stop && hermes gateway start`
- 重启后看 gateway.log 确认平台重连(weixin 自动恢复 accounts/ 下 context token,旧会话不断);让用户在平台实测一条消息验证。

## 6. 验证清单

1. `hermes gateway status` → 运行中;`hermes gateway list` → 该 profile 已连接。
2. `grep -E "^WEIXIN_|^WECOM_" ~/.hermes/.env` → 凭证齐全(展示时打码)。
3. 让用户在平台里发一条消息,确认双向收发;失败看 `~/.hermes/logs/gateway.log`。

## 7. 附带文件

- `scripts/weixin_qr_login.py` — 个人微信扫码脚本:生成桌面二维码 PNG + 自动写 `WEIXIN_*` 到 `.env`。
  复制后改开头 `HERMES_HOME` 路径即可复用。
