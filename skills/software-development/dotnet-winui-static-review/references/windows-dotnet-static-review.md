# Windows (WinUI 3 / .NET 8) 静态审查清单

适用:本机无 dotnet/Windows 环境时,只能对 Windows 端做静态审查(例如双端原生项目中 macOS 可编译、Windows 只能静态交付)。来自 MediaConverter 双端项目的 10 个真实 bug(全部已修复),按 bug 类组织,下次审查逐类排查。

## 进程/异步类(最易出致命 bug)

1. **Process.Exited 回调访问 `_process.ExitCode` 抛 ObjectDisposedException**:
   `Cancel()`(Kill 进程)后立即 `Dispose()`,Exited 事件在后台线程排队,触发时 `_process` 已释放 → 访问 ExitCode 抛异常 → 回调中断 → `SemaphoreSlim.Release()` 和 `TaskCompletionSource.TrySetResult` 永不执行 → **整个任务队列瘫痪**。
   修法:Exited 回调内先 try/catch 缓存退出码到字段,再广播事件;取消路径**不要**立即 Dispose runner,让 Exited 回调统一负责 Dispose + Release。
   检查点:`_process.Exited` 处理器里是否直接访问 `_process.ExitCode`;`Cancel*` 方法里是否 Cancel 后立刻 Dispose。

2. **取消守卫缺失**:进程被 Kill 后 Exited 仍会触发(exitCode≠0),回调会把已设的 `Cancelled` 状态覆盖成 `Failed` 并触发 TaskFailed。
   修法:Exited 回调开头 `if (task.State != TaskState.Cancelled)` 再改状态;finally 里照常 Release + 完成 tcs。
   检查点:取消路径设状态与 Exited 回调改状态之间是否有竞态守卫。

3. **进度解析器用 `[ThreadStatic]`/static 累积器**:并行任务(N 个 ffmpeg 进程)的 stdout 回调可能在同一线程池线程**交错**执行,共享累积器 → 任务 A 的 out_time 被任务 B 读到,进度/剩余时间错乱。
   修法:累积器改为 FfmpegRunner 实例字段,每进程独立解析器实例(类从 static 改 instance)。
   检查点:进度解析类是否 static/ThreadStatic;每个 runner 是否持有独立实例。

4. **SemaphoreSlim 释放路径**:保证所有出口(正常 Exited / catch 异常)恰好 Release 一次;取消路径靠 Exited 回调释放,不要双重释放。取消+立即 Dispose 又 Kill 的组合最容易泄漏。

## 参数构建类

5. **Convert 模式 + 音频容器(OutputFormatId 为 mp3/m4a/wav 等)**:会生成 `-c:v libx264 out.mp3` 这类 ffmpeg **必失败**参数。
   修法:Build() 里检测 `_catalog.AudioFormats.Any(f => f.Id == preset.OutputFormatId)` → 自动降级调用 BuildExtractAudio,**且降级分支提前 return 前必须补 `-nostdin -threads 0` 尾部参数**(正常路径的尾部参数在 switch 之后统一追加,提前 return 会漏)。
   检查点:输出格式为音频容器时,参数里不能出现 `-c:v`/`-map 0:v`。

6. **音频编码器兼容性修正用错值**:`GetCodecFix` 第三参数必须传 `preset.AudioCodecId`,不要硬编码 `format?.DefaultAudioCodec ?? "aac"` —— 否则用户选的音频编码被静默忽略。同源问题:ConversionPreset 必须有 AudioCodecId 字段(macOS 端有,Windows 端曾缺失)。

## 功能缺失 / 双端一致性

7. **双端功能对齐检查**:macOS 端有的设置项(如"默认音频编码"),Windows 端 ConversionPreset / SettingsWindow / TaskCard 必须全套有——模型字段、设置窗口填充+保存、任务卡片下拉+变更事件,缺一环用户就无法选择。
8. **死代码**:`ConcurrentDictionary` value 永不为 null,`_runners.Where(kvp => kvp.Value == null)` 恒空集合 → 方法永远 no-op。`RemoveCompleted` 类方法要么删要么改占位并注释原因。
9. **初始化遗漏**:定义但从未调用的 `Register()`/`Install()`(如 NotificationService)——全项目 grep 调用点,App 构造/OnLaunched 里补。

## 其他

10. **FindFfprobe 降级**:用户指定 ffmpeg 路径但同目录无 ffprobe 时,应继续走缓存/系统查找,不要直接返回 null(否则时长探测永远失败)。缓存命中前先 `File.Exists` 校验。
11. **日志累积 O(n²)**:`LogText = LogText + line` 每行全量拼接,2000 行时 UI 卡死。改 StringBuilder 增量追加,读取时一次性 ToString(),追加时通知一次。
12. **StartAllAsync 出队顺序**:先 `await semaphore.WaitAsync()` 再 `TryDequeue`;若先出队再等信号量,等待中的任务既不在队列也不在 runners,**取消操作会漏掉它**。队列空时 Release 并 break。
13. **空方法占位**(`LoadAsync` 等)无调用点直接删,别留。

## 验证手法

- `ffmpeg -hide_banner -encoders` 输出到 **stdout**(实测 ffmpeg 7.0),读 stdout 正确,不要"修正"成 stderr。
- 无 dotnet 时:python 静态检查(grep/UTF-8 字节扫描)+ 逐文件逻辑复查;commit message 标注 `NOT COMPILED: no dotnet`;汇报时诚实说明"未编译"。
- 静态验证脚本模板:对每个修复点写 grep 断言(注意排除注释里的关键词,避免误报,如注释解释"为什么不用 ThreadStatic"会让 `grep ThreadStatic` 命中)。
