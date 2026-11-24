---
name: cloudflare-tunnel-ops
description: "Use when 部署/排障 Cloudflare Tunnel:530/502、服务化、延迟、WS 验证。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [cloudflare, tunnel, cloudflared, proxy, networking]
    category: devops
---

# Cloudflare Tunnel 运维(cloudflared)

## When to Use

- 域名走 Cloudflare 代理但访问报 530 / 502 / error 1033 时
- 需要在服务器(尤其 Windows)部署/修复 cloudflared 隧道、注册服务、调延迟时
- 验证隧道后的 HTTP/WebSocket 链路时

## 部署步骤(CF API 直建,无需本机 cloudflared)

1. **下载**(服务器直连 GitHub 极慢/挂死):本机走代理 `curl -L --retry` → `scp` 上传。验证三件套:`curl -s https://api.github.com/repos/cloudflare/cloudflared/releases/latest` 拿真实字节数比对 + `--version` 能跑 + Authenticode 签名 Valid。
2. **创建隧道 + 凭据**(CF API):POST `/accounts/{account}/cfd_tunnel`;凭据 JSON(AccountTag/TunnelID/TunnelName/TunnelSecret)存服务器配置目录。
3. **config.yml**(放凭据同目录):
   ```yaml
   tunnel: <tunnel-id>
   credentials-file: <绝对路径>
   ingress:
     - hostname: example.com
       service: http://127.0.0.1:80
     - service: http_status:404
   ```
4. **DNS 路由**:CNAME `example.com` → `<tunnel-id>.cfargotunnel.com`,`proxied: true`(CF API PUT `/zones/{zone}/dns_records`)。
5. **启动验证**:`cloudflared tunnel --config <file> run` 看日志 `Registered tunnel connection ... location=XXX` 即成功。

## 错误码语义(先定位再动手)

| 现象 | 含义 |
|------|------|
| 530 / body `error code: 1033` | Argo Tunnel error:隧道不在线(cloudflared 没跑/没注册) |
| 502 / body `error code: 502` | 隧道在线但回源失败;或进程刚死、边缘连接超时未判定 down 的过渡态(重启服务即恢复) |
| HTTP 200 + 404 页面(含 CF 头) | 隧道+nginx 正常,404 来自应用层(如 HTTP/2 下 WS 请求) |
| `cf-error-code` 其他 | 查 Cloudflare 文档对应码 |

诊断顺序:① `sc query <服务>` 确认 cloudflared 在跑 ② 看 cloudflared 日志有无 `Registered tunnel connection` ③ 看 nginx/应用日志定位回源。

## cloudflared CLI 坑(2026.8.x 实测)

1. **`--config` 是 tunnel 子命令级 flag**:必须 `cloudflared tunnel --config <file> run`;放 run 后面报 `flag provided but not defined: -config`。
2. **`--no-autoupdate` 已移除**(报 flag not defined),不要加。
3. **打印 help 即退出 = 参数解析失败**:看 stdout 头部 `Incorrect Usage:` 行,错误在 help 前面(用 `Get-Content -TotalCount` 而非 -Tail 看)。
4. 配置 YAML:顶层 `protocol:`(quic|http2)、`tunnel:`、`credentials-file:`、`ingress:`(hostname→service,末尾兜底 `service: http_status:404`)。Windows 路径反斜杠直接写。

## Windows 服务化(关键)

- **`cloudflared service install` 装的是 agent 服务**:无参数运行,找 `%PROGRAMDATA%\Cloudflared\config.yml`,找不到就反复 1067 崩溃。绕开它。
- **正解:sc create 传统服务**(配置留在原处):
  ```
  sc create Cloudflared binPath= "C:\tools\cloudflared.exe tunnel --config C:\opt\...\.cloudflared\config.yml run" start= auto DisplayName= "Cloudflared Tunnel"
  sc start Cloudflared
  ```
- **ssh 会话启动的进程,ssh 断开即被杀**(Start-Process / start /b 都一样,日志 0 字节、进程消失)。要常驻必须服务化。
- 服务启动失败 1067 → 事件日志 SCM 记录 + `sc qc` 看 binPath;手动前台跑一次拿真实报错。

## 延迟分层诊断(慢 = 先定位,别乱调)

1. **本机 curl 的 remote_ip 在 198.18.0.0/15** = 代理 TUN fake-ip,测值含代理绕路,不代表真实链路;真实测量在服务器上做。
2. 三层基准:① 服务器 `curl http://127.0.0.1:80/ -w '%{time_starttransfer}'` 应毫秒级 ② 服务器 `curl https://域名` 多次取中位 = 真实隧道链路 ③ 本机 curl = 用户体验。
3. **隧道出口位置决定延迟**:cloudflared 日志 `Registered tunnel connection ... location=lax01`(lax=洛杉矶)。国内服务器出口选到洛杉矶时 TTFB ~800ms 是跨太平洋物理下限;切 `protocol: http2` 实测无帮助甚至略差(瓶颈是距离不是协议)。
4. 用户侧优化:浏览器走代理时给域名加直连规则(DIRECT),TTFB 可降一半。

## 验证三件套

```bash
curl -s -o /dev/null -w "%{http_code}" https://域名/                    # 200
curl --http1.1 -s -o /dev/null -w "%{http_code}" \
  -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" https://域名/ws       # 101
sc query Cloudflared | findstr STATE                                    # RUNNING
```

**curl 测 WS 必须 `--http1.1`**:HTTP/2 下 Upgrade 头无效,curl 会拿到应用 404 假象,浏览器不受影响。

## 大文件部署到受限服务器

服务器直连 GitHub 基本不动;ghproxy 不稳(段下载不完整)。可靠路径:本机走代理 curl 下载 → 校验字节数与官方 API 一致(cloudflared 可再验 `--version` + Authenticode)→ scp 上传。中断的下载会残留进程并发写同一文件(文件被锁+大小漂移):`Get-CimInstance Win32_Process` 查 cmdline 定位,`taskkill /F /PID` 清理后再删文件。

## 故障分层定位:绕过边缘逐层二分(403/502 通用,2026-09-30 实测)

边缘(域名)返回 401/403/5xx 但说不清是谁产的时,按层二分:

1. **绕 CF 直连源站同一路径**(服务器本机 `curl http://127.0.0.1:<port>/<path>`,必要时连中间反代层 nginx 也各打一次)。源站正常 + 边缘异常 = 拦截在 CF 边缘/隧道层,不是应用层,别去改应用代码/授权配置。
2. **看 4xx body 指纹**:源站代码里 403/401 的 body 格式(单字段 `{"error":"..."}` vs 带 ok 字段 `{"ok":false,"error":"forbidden"}` 等)与边缘返回逐字比对,不匹配 = 拦截响应不是源站产的,是中间某层(隧道 ingress 指到的其他服务)产的。grep 服务器本机各监听服务的代码找 403 返回行即可命中。
3. **看响应头判 CF 是否主动拦截**:CF WAF/安全规则主动拦截会带 `cf-mitigated` 头 + HTML 拦截页;只有 `cf-cache-status: DYNAMIC` 无 cf-mitigated = 上游响应被透传。受限 API token(缺 firewall:read 等)查不到 CF WAF 规则时(老版 WAF API 报 "No route" 是端点下线,非权限不足),**别耗在 CF 规则查询上,直接查 cloudflared ingress**。
4. **查 ingress 顺序匹配截胡**:`cloudflared config.yml` 的 ingress 按**从上到下顺序匹配,宽路径规则(如 `path: /api/*`)会吞掉其后所有子路径**。给 /api 下加新子服务时,若已有宽 `/api/*` 规则在前,新流量全被截胡(本案:宽规则指向另一个需鉴权头的服务 → 无头请求全 403,被截胡的服务整个瘫了)。修法:精确子路径规则排前、宽规则排后或改指正确服务;改完 `sc stop/start Cloudflared` + 三层 curl 验证(源站 / 反代 / CF 边缘同路径状态码一致 + 截胡方服务带鉴权头仍 200)。
6. **⚠️ 改 config 后 403 不消失 = 孤儿进程在抢隧道(2026-09-30 实测)**:手动 `cloudflared tunnel --config ... run` 拉起的进程是常驻孤儿(`sc stop/start` 服务不会杀它,它仍用**内存里的旧 ingress** 与服务的隧道连接并存)。改了 config.yml + 重启服务后若旧症状仍在,先 `Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" | Select ProcessId,CreationDate,CommandLine` 数进程——多个就是孤儿还活着;`taskkill /F /PID <孤儿>` 再 `sc start Cloudflared` 让服务进程接管新配置,然后重新 curl 验证。另注意 taskkill 孤儿时可能连带把刚 sc start 的服务进程也停掉,杀完再 `sc start` 一次。
5. 验证时注意:绕 CF 直连源站打"假凭据"接口返回的上游错误码(如 502 pns_upstream_error)往往是**预期态**,别当成新故障。

## 相关

- 本项目实例(your-domain.com/阿里云)凭据与拓扑见服务器 `C:\opt\yourname\config\cf-credentials.json` 与 某个自建项目 项目 skill;aliyun-ecs skill(user-owned)含阿里云服务器专属操作。
