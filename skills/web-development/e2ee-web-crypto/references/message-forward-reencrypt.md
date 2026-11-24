# 消息转发与跨房间迁移:必须按目标房间重加密

## 为什么不能直接复用原密文

每个房间有独立的 `sessionKey`,且消息 AAD = `${roomId}:${seq}:${ts}` 里含 `roomId`。
把源房间的 `{iv, cipher}` 原样搬到目标房间后,对方用目标房间的 sessionKey 解密,
GCM 认证必失败(密钥不符 + AAD 里的 roomId 不符)→ 现象是「转发的消息对方看不到/解密失败」。

## 正确流程

1. 用**源房间** sessionKey 解出明文(`decryptMessage(srcKey, {iv, ct: cipher}, srcRoomId, srcSeq, srcTs)`)
2. 用**目标房间** sessionKey 重新加密(`encryptMessage(tgtKey, plaintext, tgtRoomId, tgtNextSeq, Date.now())`)
3. 发送重加密后的 `{iv, cipher}`

## 坑(实测 某聊天App 转发/收藏)

- **字段名映射**:存储/API 层常把密文字段叫 `cipher`,而 `decryptMessage` 的签名是 `{iv, ct}` —— 传参要写 `ct: cipher`,漏了这个会拿到 undefined ct 直接解密失败。
- **源消息的 seq/ts 是解密 AAD 的必需输入**:转发接口签名若没带全源 `roomId/seq/ts`,要么显式加可选参数补齐,要么回查历史(`history` 按 `msgId` 找 `seq/ts`),不能为了省事直接搬密文。
- **服务端按目标房间重算 seq 时的竞态**:若转发路由在服务端用 `MAX(seq)+1` 重算目标 seq(而不是像普通 `/messages` 那样 409 协商),客户端用 `lastSeq+1` 预估加密,并发新消息插入时预估 seq ≠ 实际 seq → 接收方解密失败。转发接口若没有 seq 协商机制,需在文档里标注该竞态风险。
- **转发接口的成员校验**:服务端可能要求调用者同时是源房间 + 目标房间成员(防借 404/200 差异探测任意消息),客户端转发前先确认契约层字段名与 server 路由逐字对齐(sourceMsgId/srcRoomId/ts 等),字段名错会 400 `missing_fields`。
