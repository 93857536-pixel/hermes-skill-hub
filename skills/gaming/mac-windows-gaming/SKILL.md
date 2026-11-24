---
name: mac-windows-gaming
description: Use when 用户要在 Mac 上玩 Windows 游戏:方案选型、安装、兼容性查证。
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [gaming, crossover, wine, compatibility, macos]
    related_skills: [macos-app-install]
---

# Mac 上运行 Windows 游戏

## When to Use
- 用户想在 Mac 上玩 Windows 独占游戏或跑 Windows 软件,需要方案选型
- 需要安装/配置 CrossOver 或 Whisky,或查某游戏在 Mac 上的兼容性
- 用户提出破解付费软件时,需要拒绝并引导到免费替代

## 方案速览(按 Apple Silicon 情况)
- **CrossOver**(付费约 $74,14 天试用):最省心,CodeWeavers 维护,官方兼容性数据库几千个应用评级,热门游戏适配好,内置 Steam/Epic/战网一键安装器
- **Whisky**(免费开源):基于苹果 GPTK 2(D3DMetal)+ Wine,性能与 CrossOver 同级(某些场景略好);缺点是社区驱动、冷门游戏要自己调环境变量/补 dll。GPTK2 仅 Apple Silicon
- **虚拟机**(Parallels/VMware/UTM):Apple Silicon 上无 GPU 直通,3D 游戏基本跑不动,仅适合老游戏/办公软件。Parallels 图形最好但仍远远不够
- **云游戏**(腾讯 START 等):吃网速不吃显卡,本地硬件弱时玩 3A 的唯一现实路径
- 排除项:Whisky/GPTK 2 仅 Apple Silicon;Intel Mac 用 CrossOver/Wine 但核显机型性能有限

## 兼容性查证(先查再装,别猜)
1. **Apple Gaming Wiki**(最权威):https://www.applegamingwiki.com/wiki/<Game_Name> —— 按 CrossOver / Wine / Parallels 分级:Perfect / Runs / Playable / Menu / Unplayable,带实测设备和日期
2. CrossOver 兼容性数据库:https://www.codeweavers.com/compatibility
3. ProtonDB 参考:https://www.protondb.com (Linux 数据,交叉参考)
4. 抓取注意:web_extract 在本环境可能被 SSRF 保护拦截(报 "Blocked: private or internal network"),改用 `curl -A <UA>` 抓 HTML + python 正则去标签解析
5. 已知硬结论:
   - Forza Horizon 4/5 全系列 Mac 上任何方案都不可玩(微软 Xbox Live/PlayFab DRM;CrossOver/Wine 启动不了,Parallels 只能进菜单)见 references/forza-horizon-macos.md
   - 带反作弊的网游(EAC/BattlEye/Vanguard,如无畏契约/APEX)一律不可玩
   - 已下架游戏(如 FH4,2024-12 从商店下架)注意告知用户买不到正版

## 安装 CrossOver(官方渠道)
1. `brew info --cask crossover` 拿当前版本号;官方包是 **.zip 不是 .dmg**(URL 形如 media.codeweavers.com/pub/crossover/cxmac/demo/crossover-<ver>.zip,直接猜 .dmg 会 404)
2. codeweavers.com 主站按地区重定向到中国代理(马软 crossoverchina.com),其"试用下载"链接指向捆绑包(如 leigodarm64.dmg 是雷神加速器),勿用;始终走 media.codeweavers.com 直链
3. 国内网络下载加速(关键,默认节点限速 60KB/s,14 倍提速法):见 references/codeweavers-download-accel.md
4. 解压 zip 到 /Applications;架构验证用 `lipo -info`(本环境 file 命令的 libmagic 损坏会刷屏,勿用)
5. 首次启动 → 出现"试用版"窗口 → 点"现在试用"按钮即可,14 天

## 常见坑(排障顺序)
- **curl 秒败先查代理环境变量**:shell 残留 HTTPS_PROXY=http://127.0.0.1:1082 指向死代理时所有 curl 立即失败(exit 7 / http 000)。先 `unset HTTPS_PROXY HTTP_PROXY ALL_PROXY` 或加 `--noproxy '*'`,再判断是否网络问题
- media.codeweavers.com 无 User-Agent 直接 http 000,必须带 UA(Homebrew UA 即可)
- 下载进度停滞时用 `du -sh ~/Library/Caches/Homebrew/downloads/` 看 brew 缓存判断是否真在下载

## 破解请求处理
用户要求破解/绕过付费授权时:明确拒绝(违反许可协议与版权法),不提供破解指引;立即给免费替代(Apple Silicon → Whisky)+ 合法购买渠道(CrossOver 中国官网 crossoverchina.com 常打折)。免费替代与付费版对比要具体(省心 vs 免费 vs 性能),让用户自己选。
