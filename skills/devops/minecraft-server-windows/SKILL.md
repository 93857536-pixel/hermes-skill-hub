---
name: minecraft-server-windows
description: "Windows Server 部署 Minecraft Java 服务器。Use when 用户要部署 MC 服务器。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, macos]
metadata:
  hermes:
    tags: [minecraft, windows-server, java, server-deploy, game-server]
    category: devops
---

# Minecraft Java Edition 服务器部署(Windows Server)

## 持久化架构(2026-10-06 定稿,自愈闭环)
- **跑法**: `check.ps1` 探测 25565 端口,死则调 `launch.ps1`(稳定参数 -Xms128M/-Xmx512M,2GB 机器勿用 8G)。
- **看门狗**: 计划任务 `MinecraftWatchdog` 每 5min 跑 check.ps1;/ru SYSTEM。
- **开机自启**: `MinecraftBoot`(AtStartup 触发 → check.ps1),服务器重启后自动拉起。
- **备份**: `MinecraftBackup` 计划任务(backup.ps1)。
- **坑**: 早期注册过一个名为 `minecraft` 的 Windows 服务 → 指向旧版 `mc-runner.ps1`(-Xms4G/-Xmx8G,2GB 机器必 OOM 炸弹),**已 Stop-Service + 禁用(Disabled)**,切勿再启用;一切自愈走计划任务而非服务。
- **演练方法**: `Stop-Process java` → `schtasks /run /tn MinecraftWatchdog` → 90s 内 25565 恢复监听即闭环。

## When to Use

- 用户在阿里云 ECS Windows Server 上需要部署 Minecraft Java Edition 多人服务器
- 用户希望朋友通过域名(mc.example.com)加入服务器
- 需要 Windows 服务化、崩溃自恢复、自动备份的完整生产级部署

## 重要：版本号确认(首次交互必做)

**不要凭记忆断言版本号不存在 —— 以官方清单为准。** 2026 年起 Minecraft 版本号已切换为年份格式(如 `26.3` 是真实存在的正式版 release,已在本机环境成功部署并验证运行)。

收到陌生版本号(如 "26.3")时：
1. 先跑 `references/version-check.ps1` 查官方清单(`launchermeta.mojang.com/mc/game/version_manifest_v2.json`)确认该 id 是否存在、type 是否为 release
2. 清单里查无此 id → 温和确认用户意图(可能指 1.20.4 / 1.21.1)；清单里有 → 直接按该版本部署
3. 不假设、不凭印象拒绝
4. 参考脚本 `references/server-recon.ps1` 可全面体检服务器环境

## 第一步：全面体检(不急着装东西)

用 SSH 执行体检脚本(`references/server-recon.ps1`)，检查：

| 检查项 | 说明 |
|---|---|
| Windows Server 版本 + Build | `Get-CimInstance Win32_OperatingSystem` |
| CPU 核心数 + 型号 | `Get-CimInstance Win32_Processor` |
| RAM 总量 + 可用量 | `Get-CimInstance Win32_OperatingSystem` |
| C 盘剩余空间 | `Get-PSDrive C` (至少需要 5GB 给 Minecraft + 世界) |
| 公网 IPv4 | 阿里云元数据 `http://100.100.100.200/latest/meta-data/eipv4` |
| 内网 IPv4 | `Get-NetIPAddress -AddressFamily IPv4` |
| Java 是否已安装 | `java -version` + `where.exe java` |
| JAVA_HOME / PATH | `$env:JAVA_HOME` |
| 端口 25565 是否被占用 | `Get-NetTCPConnection -LocalPort 25565` |
| Windows 防火墙状态 | `Get-NetFirewallProfile` |
| 已有 Minecraft 残留目录 | `Test-Path C:\Minecraft` |
| 已有 Java 进程 | `Get-Process java` |
| IIS / nginx / Docker 等已有服务 | `Get-Service` + `Get-Process` |
| 现有 schtasks 任务名 | `schtasks /query /fo CSV` (避免命名冲突) |

**⚠️ 绝不删除/停止其他服务。** 如发现冲突先告诉用户。

## 第二步：安装 Java

**Minecraft 版本与 Java 版本对照：**
- 1.16.5 及以下 → Java 8
- 1.17 ~ 1.20.4 → Java 17
- 1.21+ → Java 21
- **26.x(2026 年份版本)→ Java 25**(从版本 manifest 的 `javaVersion.majorVersion` 读,别猜)

**Java 来源(2026-10-05 实测可用)**:Microsoft OpenJDK MSI 链接易变;Eclipse Temurin API 稳定:`https://api.adoptium.net/v3/binary/latest/<N>/ga/windows/x64/jdk/hotspot/normal/eclipse`(zip,解压即用,免安装,`-Djava.home` 或设 JAVA_HOME 指过去即可)。

**server.jar 获取(以 26.3 为例)**:
```
1. GET https://launchermeta.mojang.com/mc/game/version_manifest_v2.json → 找 id=26.3 (type=release)
2. GET 该条目的 url(piston-meta 的 26.3.json) → downloads.server.url + sha1
3. GET https://piston-data.mojang.com/v1/objects/<sha1>/server.jar → 校验 sha1 一致
```

**JVM 参数坑**: `-XX:+ParallelRefProcFailedRefHandlerThreads` 等**不存在的 flag 会让 JVM 拒启**(server.err.log: "Unrecognized VM option"),启动前 `java -XX:flag -version` 逐个验过;26.x 安全组合: `-Xms4G -Xmx8G -XX:+UseG1GC -XX:MaxGCPauseMillis=50 -XX:+UseStringDeduplication`(内存按机器实际配,2TB RAM 的机器 8G 也够)。

**Start-Process 坑**: `Start-Process -FilePath java.exe -ArgumentList '-jar','server.jar'` 的 **cwd 不是调用目录** → "Unable to access jarfile server.jar"。必须带 `-WorkingDirectory "C:\Minecraft"`;同法传日志 `-RedirectStandardOutput/-RedirectStandardError`。

**DNS/域名接入(2026-10-05 实测)**: 目标域名 `your-domain.com` 的 NS 在 **Cloudflare**——用 alidns-ops 加记录公网**不生效**(DescribeDomainRecords 显示 ENABLE 但公网 NXDOMAIN),必须走 CF API(服务器 `curl.exe --noproxy *` + cf-credentials.json,记录名写相对名 `mc`,JSON body 无 BOM,见 某个自建项目 skill「2026-10-05 新记录」)。

**优先方案：用 Microsoft Build of OpenJDK(官方 MSI 包)**
```powershell
# 下载 MSI(以 Java 21 为例)
Invoke-WebRequest -Uri "https://download.microsoft.com/download/5/a/1/5a1f4b2e-8d8a-4f9e-8b7c-3d1e2f4a5b6c/msi/x64/jdk-21_windows-x64.msi" -OutFile "$env:TEMP\openjdk21.msi"
# 静默安装(管理员权限)
msiexec /i "$env:TEMP\openjdk21.msi" /quiet ADDLOCAL=All INSTALLDIR="C:\Program Files\Java\jdk-21"
```
⚠️ **先查官方下载地址**，链接可能变化。备选：Eclipse Temurin(`https://adoptium.net`)。

**安装后验证：**
```powershell
java -version
where.exe java
[Environment]::GetEnvironmentVariable("JAVA_HOME", "Machine")
```

## 第三步：部署 Minecraft Server

**目录结构：**
```
C:\Minecraft\
  server.jar          ← 从官方下载
  server.properties   ← 手动编辑
  eula.txt            ← 首次启动后创建
  world\              ← 自动创建
  logs\               ← 自动创建
  backups\            ← 手动创建
```

**下载 server.jar：**
```powershell
# 官方 Vanilla
$version = "1.21.1"  # 改为你确认的版本
$url = "https://piston-data.mojang.com/v1/objects/<sha1>/server.jar"
# 先查版本元数据获取 sha1：
$meta = Invoke-RestMethod "https://launchermeta.mojang.com/mc/game/version_manifest.json"
$target = ($meta.versions | Where-Object { $_.id -eq $version })[0]
$sha1 = ($meta.versions | Where-Object { $_.id -eq $version }).downloads.server.url.split("/")[-1]
$jarUrl = "https://piston-data.mojang.com/v1/objects/$sha1/server.jar"
Invoke-WebRequest -Uri $jarUrl -OutFile "C:\Minecraft\server.jar"
```

**首次运行生成文件：**
```powershell
cd C:\Minecraft
java -Xmx1G -Xms1G -jar server.jar nogui
# 停掉
taskkill /F /IM java.exe
# 编辑 eula.txt → eula=true
# 编辑 server.properties
```

**server.properties 最小配置：**
```properties
server-port=25565
server-ip=
online-mode=true
gamemode=survival
difficulty=normal
pvp=true
spawn-protection=0
enable-command-block=false
max-players=20
motd=Hermes Minecraft Server | Java 21
```

## 第四步：Windows 服务化(NSSM)

**下载 NSSM(来源：`https://nssm.cc/download`)：**
```powershell
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "$env:TEMP\nssm.zip"
Expand-Archive "$env:TEMP\nssm.zip" "C:\Tools\nssm"
```

**注册服务：**
```powershell
$JAVA_BIN = "C:\Program Files\Java\jdk-21\bin\java.exe"
$NVM = "C:\Tools\nssm\win64\nssm.exe"
$NVM install MinecraftJava $JAVA_BIN
$NVM set MinecraftJava AppParameters "-Xmx2G -Xms2G -jar C:\Minecraft\server.jar nogui"
$NVM set MinecraftJava AppDirectory "C:\Minecraft"
$NVM set MinecraftJava AppStdout "C:\Minecraft\logs\stdout.log"
$NVM set MinecraftJava AppStderr "C:\Minecraft\logs\stderr.log"
$NVM set MinecraftJava AppRotateBytes 10485760
$NVM set MinecraftJava AppRotateFiles 5
$NVM start MinecraftJava
```

**NSSM 优势：**
- 开机自动启动
- 崩溃后自动重启(默认 `AppRestartDelay=10000`)
- 正常 `stop` 命令 → NSSM 发送 `AppExit default SIGTERM`(Minecraft 会执行 `save-all` + `stop`)
- 日志轮转

## 第五步：Windows 防火墙规则

```powershell
New-NetFirewallRule -DisplayName "Minecraft Java Server" `
  -Direction Inbound -Protocol TCP -LocalPort 25565 `
  -Action Allow -Profile Any
```

## 第六步：自动备份(schtasks)

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -Command `
  \$src = 'C:\Minecraft\world'; \$dst = 'C:\Minecraft\backups\backup-' + (Get-Date -Format 'yyyy-MM-dd') + '.zip';
  if (Test-Path \$dst) { Remove-Item \$dst -Force };
  Compress-Archive -Path \$src -DestinationPath \$dst -Force;
  Get-ChildItem 'C:\Minecraft\backups\backup-*.zip' | Where-Object { \$_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Force"
$trigger = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName "MinecraftBackup" -Action $action -Trigger $trigger -RunLevel Highest -User SYSTEM
```
⚠️ **`-User SYSTEM` 必带**(schtasks 写法:`/ru SYSTEM /rl HIGHEST`)。无桌面 Core ECS 没有常驻登录用户,默认身份的计划任务("仅用户登录时运行")会**静默永不触发**,见下方 Pitfalls「计划任务默认身份永不触发」。

## 第七步：DNS + 安全组

**DNS：** 用 `alidns-ops` skill 添加 A 记录：
```bash
python3 ~/bin/dns.py AddDomainRecord DomainName=liminhao.top RR=mc Type=A Value=<公网IP> TTL=600
```

**阿里云安全组：** 必须在控制台手动添加 TCP 25565 入方向规则。
**技能无法自动修改安全组**，需在回复中明确告知用户操作步骤。

## 第八步：连通性测试

```powershell
# 本地回环
Test-NetConnection 127.0.0.1 -Port 25565
# 内网 IP
Test-NetConnection 172.18.182.22 -Port 25565
# 域名
Test-NetConnection your-domain.com -Port 25565
nslookup your-domain.com
netstat -ano | findstr :25565
```

## Pitfalls

### ⚠️ Minecraft 版本号陷阱(已修正 2026-10)
陌生版本号(如 "26.3")**先查官方清单再表态**，不要凭记忆说"不存在"。2026 年版本号已切换为年份格式，`26.3` 是真实 release(已部署验证)。清单里查无此 id 才回头确认用户意图。
脚本 `references/version-check.ps1` 可快速列出官方版本列表。

### ⚠️ 不要关闭 Windows 防火墙
用户可能要求"简化网络配置"，但**永远不要执行** `netsh advfirewall set allprofiles state off`。只加具体的 Allow 规则。

### ⚠️ Minecraft 优雅停止 vs taskkill
不能用 `taskkill /F` 强杀，会导致世界数据丢失。NSSM 的默认行为是发 SIGTERM，Minecraft 会执行 `save-all` 后退出。如需手动停止：`nssm stop MinecraftJava`。

### ⚠️ Windows Server 无 GUI
所有操作必须通过 SSH + PowerShell 完成。不要依赖任何 GUI 工具。

### ⚠️ SSH 用户的 Admin 权限
阿里云 ECS 的 SSH 用户可能是普通用户(如 `Administrator` 但不在 Administrators 组)。执行 `new-itemproperty`、`New-NetFirewallRule`、`nssm install` 需要管理员权限。如当前用户无权限，需提示用户用管理员账号登录。

### ⚠️ 端口冲突检测
部署前必须检查 25565 是否被占用。如果被占用，查出是什么进程，**不要直接 kill**，告诉用户。

### ⚠️ JVM 堆内存必须按机器实际 RAM 配置
部署前先读 `TotalPhysicalMemory`。**2GB ECS 上 `-Xmx` 配大的实例会反复静默死掉**(无 OOM 异常、无 hs_err、日志干净停在 "Server empty for 60 seconds, pausing" 后被系统挤掉——该闲时暂停节点是内存压力峰值)。经验值：
- 2GB 机器：`-Xms128M -Xmx512M`
- 4GB 机器：`-Xms256M -Xmx1024M`
- 8GB+ 机器：`-Xmx2G~4G`

改堆参数后必须重启 java 并**实测过一次 60s 空闲暂停窗口**(等 ~2 分钟再查进程),堆配大了死得最快就死在这个点。

### ⚠️ java 静默死亡排查(无崩溃日志)
若 `Get-Process java` 查无进程但日志结尾干净(无 FATAL/OOM/异常堆栈)：
1. 查 `Win32_OperatingSystem.FreePhysicalMemory` + pagefile `Win32_PageFileUsage`——整机 RAM 被吃光时宿主直接挤掉 java，JVM 侧不留痕迹
2. 死点常卡在 "Server empty, pausing" 附近，与崩溃栈无关
3. 修复=降堆(见上),不是加 watchdog 硬扛
4. **SSH 嵌套引号常把进程查询打空,空输出 ≠ 进程不存在**——用"端口监听 + 日志 last-write-time + 进程"三对照确认进程状态,别只看单次查询

### ⚠️ SSH 里跑复杂 PowerShell 用"脚本文件法"
`ssh host "powershell -Command \"...\""` 嵌套引号+转义几乎必翻车(输出被吞、远端 PowerShell 里没有 `head`/`tail`、`@{n=...}` 哈希表被引号吃坏)。可靠姿势：
1. 本地 `write_file` 写 `.ps1`
2. `scp x.ps1 host:C:/path/x.ps1`
3. `ssh host "powershell -NoProfile -ExecutionPolicy Bypass -File C:\path\x.ps1"`
凡超过 3 行的远端 PowerShell 都走这条路。

### ⚠️ 计划任务默认身份在无桌面 Core 上"静默永不触发"(2026-10 实测)
`schtasks /create` 不带 `/ru` 时任务按创建者身份、"仅用户登录时运行"创建。无桌面 Core ECS 的 SSH 会话不算已登录 → 定时器一次都没跑过,**但 `LastRun`/`NextRun` 显示为空、`/run` 还报"成功"**,极易误判为"任务正常"。
- **修复**: 重建为 SYSTEM 身份 `schtasks /create /tn X /ru SYSTEM /rl HIGHEST ...`(PS 写法加 `-User SYSTEM`)
- **验证自愈要端到端**: 杀掉目标进程后**不做任何手动触发**,纯等定时器节拍(如 5min)看进程是否自动回来 + 日志重写。手动 `/run` 成功 ≠ 定时器有效
- 辅助: `icacls 'C:\Minecraft' /grant SYSTEM:(OI)(CI)F` 保证 SYSTEM 身份任务对数据目录有写权限

## Related

- `aliyun-ecs`：服务器 SSH 连接方式、PowerShell 引号坑
- `alidns-ops`：阿里云 DNS API 操作(记录查询/增删;本侧查 .top 记录被 GFW 污染时以 `DescribeDomainRecords` 库内状态为准)