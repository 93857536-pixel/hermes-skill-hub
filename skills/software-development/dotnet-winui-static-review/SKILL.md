---
name: dotnet-winui-static-review
description: "静态审查 Windows/.NET 桌面端代码(无 dotnet 环境时)。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [dotnet, winui, csharp, static-review, code-review, ffmpeg, process]
    related_skills: [dual-native-app-development, requesting-code-review, systematic-debugging]
---

# .NET / WinUI 静态审查(无编译环境)

**用途**: 本机没有 dotnet/Windows 环境时,对 Windows 端(WinUI 3 / .NET 8 / WPF / 控制台)代码做静态审查,找到"编译过但运行时必炸"的 bug 类。已在 MediaConverter 双端项目实战验证:10 个真实 bug 全部命中,修复后静态复验通过。

**触发**: 双端原生项目需要审 Windows 端;用户要求"看一下 Windows 端有没有问题";或任何 .NET 代码无法本机编译时的审查请求。

## 审查顺序(按 bug 严重度)

### 1. 进程/异步类(最易致命)

- **Process.Exited 回调访问 `_process.ExitCode`**:取消路径 `Cancel()`(Kill)后立即 `Dispose()`,Exited 事件在后台线程排队,触发时 `_process` 已释放 → 抛 ObjectDisposedException → 回调中断 → `SemaphoreSlim.Release()` / `TaskCompletionSource.TrySetResult` 永不执行 → **整个任务队列瘫痪**。修法:Exited 回调内 try/catch 缓存退出码到字段再广播;取消路径不要立即 Dispose,让 Exited 回调统一负责释放。
- **取消守卫缺失**:进程被 Kill 后 Exited 仍触发(exitCode≠0),会把已设的 `Cancelled` 覆盖成 `Failed`。修法:回调开头 `if (task.State != TaskState.Cancelled)` 再改状态,finally 照常 Release。
- **进度解析器用 `[ThreadStatic]`/static 累积器**:并行任务(N 个进程)的 stdout 回调在同一线程池线程交错执行,共享累积器 → 任务间进度互相污染。修法:每 runner 独立解析器实例。
- **SemaphoreSlim 释放路径**:所有出口(正常 Exited / catch)恰好 Release 一次;取消路径靠 Exited 回调释放,避免双重释放。

### 2. 参数构建类

- **容器与编码器不匹配**(如 FFmpeg):输出格式为音频容器(mp3/m4a/wav)但模式仍是 Convert → 生成 `-c:v libx264 out.mp3` 必失败。修法:检测音频容器自动降级提取音频;**提前 return 分支必须补尾部参数**(`-nostdin -threads 0`),否则漏掉。
- **兼容性修正用错值**:GetCodecFix 第三参数要传用户选的 codec,不要硬编码格式默认值,否则用户选择被静默忽略。

### 3. 功能缺失 / 双端一致性

- **双端对齐检查**:一端有的设置项,另一端模型/UI/保存全套要有——模型字段、窗口填充+保存、卡片下拉+变更事件,缺一环用户无法选择。
- **死代码**:`ConcurrentDictionary.Where(kvp => kvp.Value == null)` 恒空(值永不为 null)→ 方法永远 no-op,删或改占位。
- **初始化遗漏**:定义但从未调用的 `Register()`/`Install()`——全项目 grep 调用点。

### 4. 其他

- **缓存路径降级**:用户指定可执行文件路径但兄弟工具不在同目录,应继续走系统查找,不要直接返回 null。
- **日志累积 O(n²)**:`LogText = LogText + line` 每行全量拼接 → 改 StringBuilder。
- **出队顺序**:先 `await semaphore.WaitAsync()` 再 `TryDequeue`,否则等待中的任务既不在队列也不在 runners,取消会漏掉。
- **空方法占位**无调用点直接删。

## 验证手法

- 本机无 dotnet:python 静态检查(grep / UTF-8 字节扫描)+ 逐文件逻辑复查;commit message 标注 `NOT COMPILED: no dotnet`;汇报如实说明"未编译"。
- 静态验证脚本:对每个修复点写 grep 断言,**注意排除注释里的关键词**(如注释解释"为什么不用 ThreadStatic"会让 `grep ThreadStatic` 误命中)。
- 外部命令输出流别猜:实测确认(如 `ffmpeg -encoders` 输出到 stdout)。

## 参考

- 完整 10-bug 清单与代码级修法:见 `references/windows-dotnet-static-review.md`(从 dual-native 项目实战整理)。
