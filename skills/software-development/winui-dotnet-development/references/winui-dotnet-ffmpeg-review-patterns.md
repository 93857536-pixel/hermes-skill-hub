# WinUI 3 / .NET FFmpeg 进程管理:审查问题模式清单

来源: MediaConverter Windows 端(WinUI 3 + .NET 8 + FFmpeg)静态审查(2026-08)。
本机无 Windows/dotnet 编译环境,以下为静态审查结论,修复后需在 Windows 上验证。
审查顺序: FfmpegRunner → TaskManager → ProgressParser → FfmpegArgumentBuilder →
FfmpegLocator → SettingsService/UI,逐项核对下列模式。

## 🔴 严重: 取消任务 → 信号量泄漏,队列瘫痪

时序(全是真 bug):
1. `TaskManager.CancelTaskAsync` 里 `runner.Cancel()`(Kill 进程树)→ 进程终止
2. 立即 `runner.Dispose()` → `_process.Dispose()`
3. 进程终止后 `Exited` 事件才异步触发,回调访问 `_process.ExitCode`
4. `_process` 已释放 → 抛 `ObjectDisposedException`
5. `_concurrencySemaphore.Release()` 与 `tcs.TrySetResult()` 永不执行
6. 后果: 信号量永久占满,后续所有任务卡死在 `WaitAsync()`,任务队列瘫痪

修复方向: Exited 回调内访问 `_process` 成员前 try/catch,或 Dispose 前摘除
`_process.Exited` 处理器;信号量释放放 finally 且对异常免疫。

## 🔴 严重: [ThreadStatic] 累积器在并行任务下串线

`ProgressParser` 用 `[ThreadStatic] private static ProgressAccumulator _current`。
ffmpeg stdout 回调在线程池线程触发;默认 2+ 并行任务时,两个进程的 stdout 回调
**可能在同一线程池线程交错执行** → 共享同一 ThreadStatic 累积器 → 任务 A 的
out_time 被任务 B 读到 → 进度/剩余时间错乱。

修复方向: 累积器改为 FfmpegRunner 实例字段,每进程独立(ThreadStatic 只保证线程
隔离,不保证进程隔离——跨实例共享状态严禁用它)。

## 🔴 严重: 转换模式 + 音频容器 → 参数矛盾必失败

用户把输出格式选成 mp3/m4a 等音频容器但模式仍是 Convert → 参数含 `-c:v libx264`
写进 .mp3 → ffmpeg 报错秒退(与 macOS 端 smoke 测试踩过的同一类坑;macOS 端修复为
按输出扩展名选 preset,Windows 端无此防护)。

修复方向: 输出为音频扩展名时参数模板剔除视频映射/视频编码器,或自动切音频提取模式。

## 🟡 中: 功能缺失 — 缺"默认音频编码"设置

`ConversionPreset` 有 `VideoCodecId` 无 `AudioCodecId`;SettingsWindow.xaml 无音频
编码下拉框 → 音频编码永远用格式默认值,用户无法选择。双端功能不一致(macOS 有)。

修复方向: 补 AudioCodecId 字段 + UI 下拉 + SettingsService 读写。

## 🟡 中: 日志拼接 O(n²) 卡 UI

`ConversionTask.AppendLog` 用 `current + line` 全量字符串拼接,2000 行上限但每行
都复制整个字符串;且每行触发 PropertyChanged → 大文件转码时 UI 严重卡顿。

修复方向: StringBuilder/行缓冲 + UI 更新节流。

## 🟡 中: 死代码 — RemoveCompleted 永远空操作

`_runners.Where(kvp => kvp.Value == null)` — ConcurrentDictionary 的 value 永远
非 null → 过滤结果永远为空 → 方法什么都不做(幸好 ViewModel 自己从集合删了)。

## 🟢 轻: 功能未接线

- `NotificationService.Register()` 定义了但 `App.xaml.cs` 从未调用 → `_registered`
  永远 false,`Show()` 直接 return,通知永远不显示。
- `FindFfprobe(用户指定路径)`: 用户指定 ffmpeg 但 ffprobe 不在同目录 → 返回 null,
  不降级到系统路径 → 时长探测失败。

## ✅ 已验证正确(无需改动)

- `-map 0:v:0?` 修复已同步(纯音频输入参数正确)。
- 硬件编码器探测读 **stdout** 是对的: 实测 ffmpeg 7.0 `-encoders` 输出到 stdout
  (167 行,含 3 个硬件编码器),不是 stderr。
- NativeMethods `PROCESS_SUSPEND_RESUME = 0x0800` 权限值正确。
- 进度回调经 DispatcherQueue 封送 UI,线程模型设计正确(除 ThreadStatic 那处)。
- `GetCodecFix` 编码器兼容修正逻辑正确。
