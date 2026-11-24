---
name: e2ee-web-crypto
description: "Use when building E2EE web messaging with Web Crypto API."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, windows, linux]
metadata:
  hermes:
    tags: [e2ee, webcrypto, aes-gcm, ecdh, messaging, security]
    category: web-development
---

# E2EE Web 通讯应用(Web Crypto API)

## When to Use

构建端到端加密 Web 应用(聊天/私信/任何"服务器不可信"场景):需要设计密钥体系、消息加密、
密钥分发、服务器零明文验收。实战于 LinMinHao Chat(2026-08,已部署生产)。

## 密钥体系(实测模式)

```
身份(每设备):  Ed25519(签名) + ECDH P-256(密钥交换)
               私钥 JWK 只存 IndexedDB(库名独立,如 lmh-keys),绝不上传
               公钥(base64 raw)上传服务器
会话密钥:       32B 随机;ECDH(myPriv, memberPub) → HKDF-SHA256 → AES-GCM 包装
               wrappedKey = {v:1, iv, ct, pk}   ← pk = 包装者公钥(对方解包必需!)
消息:           AES-256-GCM;每消息独立 12B IV;密钥 = HKDF(sessionKey, salt=iv,
               info=`lmh-msg-v1:${roomId}:${seq}`);AAD = `${roomId}:${seq}:${ts}`
明文载荷:       JSON {t: text} / {f: {attId,name,size,mime}}(附件元数据)
```

要点:
- **wrappedKey 必须内嵌包装者公钥 pk** —— 否则解包方要额外查"谁包装的",服务器表结构会复杂化
- 服务器只存 wrappedKey 密文 + 消息密文 + 元数据,永远无法还原 sessionKey

## AAD 绑定 seq 的并发协议(关键设计)

消息加密的 AAD 含 seq,但发送前客户端不知道服务器将分配的 seq:

1. 客户端用本地 `lastSeq+1` 加密,请求体携带该 seq
2. 服务器校验 `seq == msg_count+1`,冲突返回 `409 {error:'seq_conflict', seq:<最新>}`
3. 客户端用新 seq 重新加密重试(≤3 次)

数据库 seq 分配用单条 UPDATE 原子递增,避免并发竞态。WS 只广播事件(roomId+seq),密文走 REST 拉取 —— 简化一致性,避免 WS 帧超限。

## 临时会话密钥带外分发(分享链接即密钥)

```
/t/<roomId>#k=<base64url(sessionKey)>
```

- URL fragment 不进 HTTP 请求 → nginx/服务器/日志均不可见
- 「刷新即焚」:页面加载时检测 sessionStorage active 标记(首次进入时设置)→
  清除 fragment(history.replaceState)+ 标记 + 内存密钥,界面清空;服务器密文归档保留
- 退出按钮 = 同一清除流程(leave API 仅打日志,不删服务器数据)

## 服务器零明文验收(交付前必做)

1. 发一条已知明文测试消息
2. 扫描 messages/*.enc、chat.db(只读 better-sqlite3 打开)、备份 zip 的**字节流**,断言不含该明文
3. 管理员接口响应断言不含明文
4. 日志脱敏:手机 `138****1234`、邮箱 `abc***@example.com`;敏感字段名(code/token/iv/cipher/privatekey)一律 REDACTED

## 验证码(E2EE 配套)

- DB 存 `HMAC-SHA256(pepper, code)`,不存明文(6 位码空间小,必须 pepper)
- 5 分钟有效、错误 5 次作废、用后立即失效、60s 发送间隔 + 目标 5 次/h + IP 限流
- 日志绝不记完整 code;dev 通道(验证码写安全日志)与生产通道(阿里云 SMS/DirectMail)分离

## 坑(实测)

- **AAD 含时间戳时,ts 必须由加密方决定并贯穿全链路**——服务器绝不能自己生成 ts 存库/返回。曾踩:加密 AAD=`roomId:seq:ts` 用客户端 Date.now(),服务器落库用自己的 Date.now(),接收方解密用服务器返回的 m.ts → 两次 ts 差网络延迟 → GCM 认证必失败 → 前端 `catch{}` 静默丢弃 → 现象是"发送方看到、对方永远收不到、刷新后自己也看不到"。正确做法:客户端把加密用的 ts 放进请求体,服务器校验合理性(`|ts-now|<30min`,超限 400)后原样用于 AAD/存储/返回。附件同理(加密附件与消息元数据用同一 ts,解密时从消息 ts 取)。
- **验证 E2EE 消息链路必须覆盖解密,不能只测广播**:"两个 WS 客户端都收到 msg 帧"是假阳性——事件到达 ≠ 接收方能解密显示。必须用 node WebCrypto 复刻前端同款算法(HKDF+AES-GCM,AAD 同构)走完 加密→发送→拉取→用返回 ts 解密→断言明文一致 全链路。
- **409 seq 重试必须对齐服务器序号**:catch(409) 后先 `lastSeqRef = e.data.seq - 1` 再重新加密重试;原样重发(不更新本地 seq)会 3 次全 409 死循环。
- **TS 5.7+ Uint8Array<ArrayBufferLike> 不满足 BufferSource 类型** → 定义 `export type Bytes = Uint8Array<ArrayBuffer>` 并在所有 subtle.* 调用链使用;base64 解码函数显式返回 Bytes
- Ed25519 私钥 JWK 的 `x` 字段即公钥:用 `jwkPubToB64(x)` 导出,不要 exportKey('raw', privateKey)(会失败);ECDH 公钥 = x||y 拼接
- 浏览器 Web Crypto 的 Ed25519 支持:Safari 17+/Chrome 113+/Firefox 127+(现代浏览器均可用)
- WS 认证:账号 JWT / 临时一次性短令牌(join 颁发,5 分钟,用后即废);心跳 25s、90s 无活动断开、帧上限 128KB
- 附件:服务器只能校验大小与客户端声明 MIME 白名单(无法验证密文内真实类型,E2EE 特性);下载强制 attachment + nosniff

## References

- `references/某个自建项目-case.md` — 完整项目案例(密钥导出/多设备/部署联动)
