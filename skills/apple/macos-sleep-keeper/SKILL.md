---
name: macos-sleep-keeper
description: "Use when 构建 macOS 合盖保活/自动熄屏守护工具(pmset disablesleep 类)。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [macos, pmset, sleep, caffeinate, menu-bar, clamshell, hermes, launchagent]
    category: apple
---

# macOS Sleep Keeper(合盖保活 / 自动熄屏守护工具)

构建「后台任务跑着时不让 Mac 睡(合盖也不睡),任务结束后宽限 N 分钟无人操作就自动熄屏睡眠」这类菜单栏守护工具。
参考实现:HermesKeeper(一个已开源的 SwiftPM 菜单栏工具)。

## When to Use
- 用户要求合盖笔记本跑长任务(agent/构建/cron)不中断
- 「X 在跑就保活,X 结束 5 分钟后没人动就自动睡眠」的状态机需求
- 菜单栏小工具:状态图标 + 手动覆盖(立即唤醒/立即睡眠)+ 登录自启

## 关键技术事实(全部实测过)
1. **caffeinate 挡不住合盖(clamshell)睡眠** —— portable Mac 合盖默认强制睡,唯一能阻止的机制是机器级开关 `sudo pmset -a disablesleep 1`;状态读 `pmset -g | grep SleepDisabled`(1=被阻止)。
2. **SleepDisabled=1 时 `pmset sleepnow` 会被拒绝** → 自动熄屏前必须先 `disablesleep 0` 再 sleepnow。
3. **root 通道**:app 内一律 `sudo -n pmset ...`(无 NOPASSWD 时快速失败不卡 UI);完整功能需 `/etc/sudoers.d/xxx` 加 `user ALL=(root) NOPASSWD: /usr/bin/pmset`。本机(yourname)是全局 NOPASSWD,直接可用。
4. **用户在场判定**:`ioreg -rc IOHIDSystem` 的 `HIDIdleTime`(纳秒) < 窗口(默认 60s),或盖子开着(`ioreg -rc IOService` → `AppleClamshellState == No`)。合盖+外接键盘敲字 = 在场,不会误睡。
5. **崩溃安全**:启动时做状态对账(残留 disablesleep=1 且 hermes 不忙 → 释放);**退出必须复位 disablesleep=0**,否则留下「永不睡眠」的坑。

## 忙闲信号(hermes 场景)
| 信号 | 可靠性 | 说明 |
|---|---|---|
| `~/.hermes/state.db` mtime | **主信号** | 每个回合/工具调用都写库(~15s),最近 N 秒内写过 = busy |
| `gateway_state.json → active_agents` | 辅助 | 只在回合边界写入,单独用会漏判 |
| 同文件 `pid` + `kill(pid,0)` | 兜底 | gateway 进程没了就一律按「不忙」处理 |

## 状态机(实测跑通的参考)
```
hermes 忙              → SleepDisabled=1   硬阻止(合盖也醒着)
忙完 < grace(默认 300s) → SleepDisabled=1   宽限期
宽限期内用户在场        → SleepDisabled=0   交回系统策略,不强制睡
宽限过期 + 用户不在      → disablesleep=0 + pmset sleepnow(一次性,flag 防重发)
一直空闲                → SleepDisabled=0   系统自管
```

## 构建配方
- SwiftPM executable + 手搓 .app 包(LSUIElement=true,ad-hoc codesign `codesign --force --deep --sign -`,先 `xattr -cr`);骨架见 `macos-menubar-swiftpm-app` 技能
- 登录自启用**每用户 LaunchAgent**(plist 放 ~/Library/LaunchAgents),比 SMAppService 对手写/ad-hoc 包可靠;⚠️ 在 hermes gateway 会话终端里 `launchctl bootstrap` 会被安全策略拦截——plist 装好即可,下次登录自动加载
- 配置:Application Support/config.json + 环境变量覆盖(测试用);**dry-run 模式**(只写日志不碰电源)+ 假 hermes 目录跑 `--selftest` 全状态机
- 定时器工作放 off-main queue;UI 经 onTick 回调回主线程

## Pitfalls
- **ioreg 管道死锁**:Swift Process 跑 `ioreg -rc IOService` 输出 ~95KB > 64KB pipe 缓冲,`waitUntilExit()` 永久阻塞 → 先 `pipe.fileHandleForReading.readDataToEndOfFile()` 再 wait。shell 里无此问题。
- **合盖+电池+disablesleep = 跑到没电**:向用户明示「长时间合盖跑任务请插电」,这是需求性质不是 bug。
- **自动熄屏的副作用**:机器睡着时 hermes gateway/微信机器人会掉线,开盖恢复——交付时主动说清,并给「关闭自动熄屏」开关(只保活不熄屏模式)。
- 菜单栏图标随三态变化(bolt=保活/timer=宽限倒计时/moon=空闲)比单一图标好用;状态文案放 tooltip 里。

## 验证
- `pmset -g | grep SleepDisabled` 1↔0 随状态切换(对照日志)
- dry-run 自测: `HERMES_KEEPER_DRYRUN=1 HERMES_KEEPER_HOME=<假目录> ./HermesKeeper --selftest 18` 走完全状态机不碰真实电源
- 退出释放测试:quit app 后 flag 回到 0(必测,防「永不睡眠」残留)
- 探测脚本: `scripts/pmset-probe.sh`(查 flag/sudo NOPASSWD/hermes 信号)

## 相关
- `macos-menubar-swiftpm-app` — 菜单栏 SwiftPM 应用骨架
- `macos-launchd-services` / `macos-autostart-control` — 常驻服务与自启
- `github-release-publishing` — 交付 dmg 到 Release
