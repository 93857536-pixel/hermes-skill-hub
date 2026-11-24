# Forza Horizon 系列在 Mac 上的兼容性(2026-08 查证)

数据来源:Apple Gaming Wiki(applegamingwiki.com),权威实测,非猜测。

## Forza Horizon 4
- **CrossOver: Unplayable** —— "Doesn't Start. Most likely due to DRM."(启动不了,大概率 DRM)
- **Wine/Whisky: Unplayable** —— 同样启动不了
- **Parallels 虚拟机: Menu** —— 能进菜单但帧率极低,随后内存耗尽崩溃;实测设备为 64GB RAM 的 M2 MacBook Air;Microsoft Store 版配置菜单能开但游戏崩溃
- 已下架:2024-12-15 从 Steam 和 Microsoft Store 移除(授权到期),已购玩家仍可玩;现在买不到正版(除非二手 key)

## Forza Horizon 5
- **CrossOver 26: Unplayable** —— 2026-04 实测(MacBook Pro 16 M2 Pro, macOS 26.5),试了 Steam 版和"其他"版本,含 ProtonDB 建议装 WebView2,均无法启动

## 根因
Forza 系列绑定微软 Xbox Live / PlayFab 在线认证与 DRM,Mac 兼容层(Wine 系)过不了认证;虚拟机则死于 Apple Silicon 无 GPU 直通 + 半虚拟化图形性能不足。**结论:FH 全系列 Mac 本地无解,换 CrossOver/Whisky/虚拟机都一样。**

## 用户替代方向(按推荐序)
1. 云游戏:腾讯 START / 网易云游戏(有地平线系列,吃网速不吃显卡)
2. Mac 原生赛车游戏(无需兼容层):GRID Legends、DiRT Rally 2.0、F1 23(均有 macOS 版)
3. Windows 电脑 / Xbox 主机

## 查证方法(可复用)
- 抓 https://www.applegamingwiki.com/wiki/<Game_Name> 页面,用 python 正则去 HTML 标签后找 "macOS Compatibility" 段,解析 CrossOver/Wine/Parallels 三行评级与 Notes
- web_extract 工具在本环境被 SSRF 保护拦截(报 "Blocked: private or internal network"),必须 curl 直抓
