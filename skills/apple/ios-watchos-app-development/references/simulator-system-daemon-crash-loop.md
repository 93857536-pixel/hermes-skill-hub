# 模拟器系统守护进程崩溃循环 (crash loop) 排查与止血

2026-09-25 实例: Xcode 27 beta + iOS 27.0 模拟器 (iPhone 17 Pro Max), 模拟器实时监听循环
(sim-live-watch) 运行期间, 用户反复收到 macOS 崩溃报告对话框。崩溃的是**被测 App 之外的
系统守护进程**, 与正在开发的 App 无关。

## 症状识别

- 对话框 Process = 模拟器 coalition 下的**系统守护进程** (如 `PosterBoard`, 壁纸/PosterKit 服务),
  parent = `launchd_sim`, 与被测 App 无调用关系
- 崩溃异常常为 `EXC_BREAKPOINT (SIGTRAP)` = 系统框架内断言失败 (如
  `-[PRPosterDescriptor _initWithPath:].cold.1` 读壁纸描述符路径时断言崩)
- **循环模式**: 崩一次, launchd_sim 秒级自动拉起, 再崩 → 几秒一个报告, 对话框反复弹
- 特征指纹: 崩溃报告**栈完全相同**, 时间戳密集 (实例: 6 分钟内 25 份, 间隔 ~10s)

## 诊断步骤

1. 数崩溃报告确认循环:
   ```bash
   ls -lt ~/Library/Logs/DiagnosticReports/ | grep -iE "<进程名>" | head
   ls ~/Library/Logs/DiagnosticReports/ | grep -icE "<进程名>"   # 计数
   ```
2. 对比时间戳间隔 + 抽查 2 份报告栈是否一致 → 一致 = 同一断言死循环, 非随机崩溃
3. 判定归属: 栈全在 `PosterKit`/`BoardServices`/Apple 框架 = **系统守护进程崩**,
   与你的 App 无关, 不必改 App 代码

## 止血修复 (以 PosterBoard 为例, 已验证有效)

```bash
SIM=5F3849D6-...; # 目标模拟器 UDID
SIMDATA=~/Library/Developer/CoreSimulator/Devices/$SIM/data

# 0) 先停掉运行中的监听循环 (sim-live-watch 等), 避免模拟器重启时互相干扰
#    (terminal 里 kill / Hermes process kill 都行)

# 1) 关模拟器
xcrun simctl shutdown $SIM

# 2) 第一刀: 清 PosterKit 缓存 (temp/trash 下堆的坏 descriptor)
rm -rf "$SIMDATA/Library/Application Support/com.apple.PosterKit"

# 3) 重启验证; 若仍崩 (simctl spawn 查 launchctl 退出码 -5 = SIGTRAP), 说明坏数据
#    在 SQLite 仓库, 第二刀 (shutdown 后):
#    rm -rf "$SIMDATA/Library/Application Support/PRBPosterExtensionDataStore" \
#             "$SIMDATA/Library/Caches/com.apple.Posters.UnityPosterApp.ExtragalacticPoster"
#    再 boot
xcrun simctl boot $SIM
```

## 验证判据

- **零新报告**: 记录修复时刻, 等 60s 后
  `find ~/Library/Logs/DiagnosticReports -name "<进程名>*" -newermt "<修复时刻>"` → 空 = 止血成功
- **模拟器内退出码**: `xcrun simctl spawn $SIM launchctl list | grep <进程名>`
  末列 `-5` (SIGTRAP) = 又崩过; `0` = 干净运行
- 修复后重启 sim-live-watch 循环, 初始构建 BUILD SUCCEEDED 即全链路恢复

## 性质与副作用

- 属 Xcode beta + iOS 模拟器 beta 组件问题, 数据卷里壁纸服务状态损坏是常见诱因
- 清掉的是壁纸描述符缓存/数据仓库, 模拟器壁纸数据会重建, **无用户可见副作用**
- 以后复发: 同样操作再清一遍即可; 若该模拟器已不需要, 也可 `simctl erase` 整卷重置
- **别把这类弹窗当成"我的 App 崩了"去改 App 代码** —— 先认进程名与 coalition
