# Windows nginx / cloudflared 配置写入与重载（阿里云 ECS 实测 2026-10-05）

服务器是 Windows 时，通过 SSH 改 `nginx.conf` / cloudflared `config.yml` 有一串必踩的坑。
本文件给出**已验证可用**的写法，别再用内联拼命令。

## 1. 写文件：base64 是最可靠的方式

内联 `ssh host "powershell -Command \"...\""` 里的 `$`、`&`、反斜杠会被 **bash + cmd 双层** 吞掉，
症状五花八门：`'Select' 不是内部或外部命令`、`'"' 不是内部...`、`unexpected EOF while looking for matching`、
`ssh variant 'simple' does not support setting port`。

**可靠写法 = 本地 base64 编码 → 服务器解码写文件**：

```bash
B64=$(base64 -i /tmp/nginx.conf.new | tr -d '\n')
ssh host "powershell -Command \"[IO.File]::WriteAllText('C:\nginx\conf\nginx.conf', [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$B64')), [System.Text.UTF8Encoding]::new(\$false)); Write-Host OK\""
```

这一步**同时**解决「引号转义」和「BOM」两个问题。

## 2. BOM 会让 nginx 起不来

Windows PowerShell 5.1 的 `Set-Content` / `Out-File` / `>` **默认写 UTF-8 BOM**。
nginx 会把 BOM 当成指令首字符，报 `unknown directive "#"`（明明第一行是注释）。

- 正确：`[IO.File]::WriteAllText(path, text, [Text.UTF8Encoding]::new($false))`
- 检查：`[IO.File]::ReadAllBytes(path)[0..2]` 不应是 `239,187,191`
- 救急（已写脏了）：读回内容 → 用 `UTF8Encoding($false)` 重写一遍即可去 BOM

## 3. `nginx -s reload` 报 Access is denied

`nginx: [error] OpenEvent("Global\ngx_reload_<pid>") failed (5: Access is denied)`
= 正在跑的 nginx master 是**别的会话/用户**启动的，当前 SSH 会话发不出 reload 信号。

解法（按序）：
```bash
ssh host "taskkill /F /IM nginx.exe"                     # 杀掉 master
ssh host "powershell -Command \"Start-Process -FilePath 'C:\nginx\nginx.exe' -WorkingDirectory 'C:\nginx' -WindowStyle Hidden\""
```
改 cloudflared 配置同理：`sc stop/start Cloudflared` 不生效时 `taskkill /F /IM cloudflared.exe` 再 `sc start Cloudflared`
（注意杀孤儿可能连带停掉刚起的服务进程，杀完再 `sc start` 一次）。

## 4. `nginx.exe` 前台跑会卡死 SSH 会话

`ssh host "cd C:\nginx && nginx.exe"` 会 hang 到命令超时（exit 124）——前台常驻进程占住 SSH 通道。
必须后台起：`Start-Process -FilePath 'C:\nginx\nginx.exe' -WorkingDirectory 'C:\nginx' -WindowStyle Hidden`。

## 5. cwd / 配置路径

`nginx.exe -t` 与 `-s reload` **必须在 `C:\nginx` 下跑**，否则相对路径 `logs/` 解析错、报
`CreateFile C:\Users\Administrator/logs/nginx.pid failed`。稳妥：`cd C:\nginx && nginx.exe -t`，
或显式 `nginx.exe -t -c C:\nginx\conf\nginx.conf`。

## 6. 加子域名时改**两处**

把一个 Web 应用迁到新子域名（如根域名 → `chat.example.com`）时：
1. **nginx `server_name`** 加上新子域（多域名空格分隔：`server_name a.com b.com chat.a.com;`）
2. 若前端 WebSocket 地址是用 `location.host` 拼出来的（`wss://<current-host>/ws`），
   则 **CSP `connect-src` 必须把新子域的 `wss://` / `ws://` 加进去**，否则浏览器拦掉 WS
   （症状：控制台 CSP 报错、连不上 ws、前端「正在重连」死循环）。

改完先 `nginx -t` 测语法，再 reload；最后从**外部**（本机 `curl --noproxy '*'`）测新域名的
`/api/health` 200 + 页面 200 + CSP 头里确含新 ws 源。

## 7. ECS 本机 curl 会被 SST/sing-box 代理干扰

服务器上 `curl.exe` 打自己域名常返回 `000` / `35` / `502`——那是服务器出网被代理污染，
**不代表公网不通**。判据：
- 服务器 `curl.exe --noproxy '*' ...` 或 `-H 'Host: <域名>' http://127.0.0.1/...` 直达 nginx 应正常；
- 公网可达性**从本机 Mac**（`curl --noproxy '*' https://<域名>/api/health`）或 iPhone 蜂窝网验证。

## 8. Windows shell 里的引号/管道

SSH 到 Windows 后默认落在 **cmd**，不是 bash：`export X=Y` 报「不是内部或外部命令」，
`Get-Content`/`Select-Object` 直接敲也报错（它们是 PowerShell cmdlet）。
- 要跑 PowerShell：`ssh host "powershell -Command \"...\""`（复杂脚本走第 1 条 base64/文件方案）。
- 要跑 cmd 内建：`ssh host "cmd /c \"...\""`。
- `type` 是 cmd 的，`Get-Content` 是 PowerShell 的，别混。
