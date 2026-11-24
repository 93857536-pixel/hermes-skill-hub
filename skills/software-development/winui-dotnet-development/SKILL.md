---
name: winui-dotnet-development
description: "Windows 原生桌面应用(WinUI 3/.NET 8)开发与静态审查,FFmpeg 进程管理."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, windows]
metadata:
  hermes:
    tags: [windows, winui, dotnet, csharp, ffmpeg, process, code-review, msix]
    related_skills: [dual-native-app-development, macos-appkit-development, requesting-code-review]
---

# Windows 原生桌面应用开发与审查 (winui-dotnet-development)

**用途**: 交付/审查 Windows 原生桌面应用(WinUI 3 + .NET 8 + Windows App SDK)。对应
macOS 侧的 `macos-appkit-development`。已在 MediaConverter Windows 端实战(静态审查,
本机无 Windows 编译环境)。

**触发**: 用户要求开发/审查 Windows 原生应用;双端项目中的 Windows 端(与
dual-native-app-development 配合);审查任何 .NET 进程封装/异步任务管理代码。

## 无 Windows 编译环境时的静态审查流程

本机(macOS)无 dotnet/Windows 时,交付 = 完整源码 + 静态审查,必须如实标注"未编译":

1. **读全核心逻辑文件**(不要只看 diff): Services/ 下 FfmpegRunner、FfmpegArgumentBuilder、
   TaskManager、ProbeService、ProgressParser、FfmpegLocator、NativeMethods、SettingsService;
   ViewModels/、Views/ 的 code-behind。XAML 与 code-behind 事件处理器一一对应核对。
2. **对照 Core 契约**(双端项目): 参数拼装、进度解析协议、硬件编码变体必须与 macOS 端一致。
   改动同步性检查:`grep -rn "0:v:0"` 对比两端 —— 一端修了另一端可能漏。
3. **按问题模式清单逐项排查**(见 references/winui-dotnet-ffmpeg-review-patterns.md):
   信号量泄漏、ThreadStatic 串线、音频容器参数矛盾、日志 O(n²)、死代码、功能未接线。
4. **用实际二进制验证 ffmpeg 行为**: 本机 macOS 的 ffmpeg 与 Windows 端行为一致处可直接
   实测(如 `ffmpeg -encoders` 输出到 **stdout** 而非 stderr——实测 167 行含硬件编码器)。
5. **汇报格式**: 按严重度分级(🔴 崩溃/卡死 → 🟡 功能缺失 → 🟢 轻微),每条给
   位置/现象/后果/修复建议;明确列出"已验证正确无需改动"的点。

## .NET 进程管理的核心审查原则

- **Exited 回调访问 Process 成员**: Dispose 后访问 `_process.ExitCode` 抛
  ObjectDisposedException;信号量释放/tcs 完成必须放 finally 且对异常免疫,否则队列瘫痪。
- **跨实例共享状态**: 严禁 `[ThreadStatic]` 存累积器(并行任务回调可在同线程池线程
  交错);每个 runner 实例持有自己的状态。
- **参数与文件类型匹配**: 输出为音频扩展名时参数模板必须剔除视频映射/编码器。
- **双端功能一致性**: 逐项对比两端设置项(如"默认音频编码"macOS 有 Windows 缺)。

## WinUI 3 特有坑

- **unpackaged 模式**: `NotificationService.Register()` 必须真正被调用(App.xaml.cs
  构造),否则 `Show()` 直接 return 永远无通知;无 AUMID 时静默降级是预期行为。
- **Mica 背景**: `SystemBackdrop = MicaBackdrop()` 需 try/catch(Win11 才生效)。
- **FolderPicker/FileOpenPicker**: 必须 `WinRT.Interop.InitializeWithWindow.Initialize`
  绑定窗口句柄,否则 unpackaged 下抛异常。
- **线程封送**: ffmpeg 进度回调在后台线程,更新 ViewModel 需 `DispatcherQueue.TryEnqueue`。

## 打包与签名(Scripts/ 已备)

- `build-msix.ps1` / `sign.ps1` / `dev-run.ps1` / `fetch-ffmpeg.ps1`(下载 ffmpeg 内置)。
- csproj 五要素核对: TargetFramework / UseWinUI / WindowsPackageType / SelfContained /
  AppxManifest;P/Invoke 声明(DllImport)权限常量要查证(如 PROCESS_SUSPEND_RESUME=0x0800)。

## 无 Windows 环境时交付 EXE: GitHub Actions 云构建

本机(macOS)无 dotnet 时,用户仍可能要求 Release 交付 exe(而非源码/MSIX 中间产物)。
用 GitHub Actions `windows-latest` runner 远程编译自包含 EXE 并自动上传 Release:

- 完整可复制的模板见 `templates/windows-exe-inno-build.yml`(setup-msbuild → msbuild
  /t:Publish 自包含 → 捆绑 gyan.dev ffmpeg/ffprobe → Inno Setup 编译单文件安装器
  → softprops/action-gh-release 上传),配套安装器脚本 `templates/installer.iss`。
  ⚠️ 旧模板 `templates/windows-exe-build.yml` 是 zip 打包版(2026-08 被用户要求
  弃用——"只留 exe 和 dmg"),如仍在库中请忽略,以 inno 版为准。
- **交付形态: 单文件 setup.exe,不是 zip**(2026-08 用户明确要求"只留 exe 和 dmg")。
  WinUI 3 自包含产物是几十个文件(exe+dll+bin/ffmpeg),不支持 .NET 单文件发布,
  必须用 Inno Setup 把整个 publish 目录打成安装器: `choco install innosetup -y` →
  `iscc "/O$env:GITHUB_WORKSPACE" "/DMyAppVersion=$ver" "/DPublishDir=$pubDir" Windows/Scripts/installer.iss`
  (iss 脚本放仓库 Windows/Scripts/,AppId 用固定 GUID,PrivilegesRequired=lowest 装到
  {localappdata}\Programs)。**坑: iscc 默认输出到 .iss 所在目录,必须 /O 指定
  GITHUB_WORKSPACE,否则上传步骤找不到文件**。
- 前置: csproj 必须 `WindowsPackageType=None` + `WindowsAppSDKSelfContained=true`
  (否则产 MSIX 而非裸 exe);runner 自带 .NET 8 + Windows App SDK NuGet 自还原。
- **⚠️ 必须用 VS 的 msbuild.exe,不能用 dotnet publish/dotnet msbuild**:
  两者都缺 XAML MarkupCompilePass2 的 LocalAssembly 传递(WMC1509 → 项目类型
  解析失败)。在 Publish 步骤前加 `microsoft/setup-msbuild@v2` 把 VS msbuild.exe
  加入 PATH,再用裸 `msbuild /t:Publish`。完整失败链见
  `references/winui-cloud-build-failure-path.md`(5 层)。
- 触发: `gh workflow run windows-build.yml --ref main -f tag=v1.0.0`;
  轮询 `gh run view <id> --json status,conclusion`,失败看
  `gh run view <id> --log | grep -E "Error|error CS|WMC"`。
- **验证纪律**: 云构建是真实验证(日志 + Release 资产列表),workflow 静态验证只查
  结构/命令/缩进(偶数);跨行反引号续行命令 grep 匹配不到,先折叠换行再搜;
  验证脚本 grep 要排除注释行(注释里写 "dotnet publish" 会被误判为残留)。
- **验证脚本自身 bug 是误报主源**: 复杂 grep/cut/sed 链极易自伤——heredoc 里的
  `\(` 被 shell 转义吃掉、`cut -d'"' -f4` 字段错位、`split('>')[0]` 截断根标签、
  正则 `\b` 误匹配 `<UserControl.Resources`(单词边界在 "." 前成立)。凡涉及
  字符串匹配/计数,优先用 python 精确检查(`re.search` + 排除注释行)而非
  shell 文本链;脚本先跑通再下结论,FAIL 先怀疑脚本再怀疑代码。

## 首次真实编译的坑(静态审查查不出来的编译错误)

静态审查只能保证逻辑,首次在 windows-latest 上 `dotnet publish` 会暴露两类编译错误:

**① csproj 缺 PackageReference(最常见的首次失败)**
`UseWinUI>true` 本身不够——还必须显式声明:
```xml
<ItemGroup>
  <PackageReference Include="Microsoft.WindowsAppSDK" Version="1.8.260710003" />
  <PackageReference Include="Microsoft.Windows.SDK.BuildTools" Version="10.0.26100.7705" />
</ItemGroup>
```
缺失症状(全是引用解析失败): `IValueConverter` 找不到(CS0246)、
`Microsoft.UI.Dispatching`/`Microsoft.Windows.AppNotifications` 不存在(CS0234)、
`Microsoft.UI.Xaml.UnhandledExceptionEventArgs` 不存在。
- **版本必须先在 NuGet 校验存在再写入**: `curl https://api.nuget.org/v3-flatcontainer/<包名小写>/index.json | python3 -c "import json,sys; print(json.load(sys.stdin)['versions'][-3:])"`。本会话写了个不存在的 BuildTools 版本(10.0.26100.3916),publish 还原时直接失败。
- WindowsAppSDK 用 1.8.x 稳定线即可(项目 API 兼容),BuildTools 选 10.0.26100.x 确认存在的版本。

**② XAML 编译器错误(WMC 前缀,静态审查永远看不出来)**
- `WMC0055: Cannot assign 'Default' into 'RequestedTheme' of type 'ApplicationTheme'`:
  Application 根标签**不能**写 `RequestedTheme="Default"`(枚举只有 Light/Dark;跟随系统是默认行为,直接删属性)。
- `WMC0011: Unknown member 'MinWidth'/'MinHeight'/'Resources' on element 'Window'`:
  WinUI 3 的 `Window` **没有** MinWidth/MinHeight/Resources 属性(那是 UWP 的)。
  删掉尺寸属性;`Window.Resources` 移到根元素(如 `<Grid.Resources>`)。
- `WMC0011: Unknown member 'VerticalScrollBarVisibility' on element 'TextBox'`:
  该属性属于 ScrollViewer,TextBox 上没有,直接删。
- `WMC1110: Invalid binding path 'X' : Property not found on type 'TaskCard'`(一批
  几十个,全在 UserControl 的 x:Bind 上): UserControl 的 `{x:Bind}` **编译期绑定到
  UserControl 自身类型**,属性却在 DataContext(TaskItemViewModel)上。
  **⚠️ 加 `x:DataType` 无效**(本会话实测:加了仍报同样错误)——x:DataType 只影响
  编译期校验,不改变运行时绑定源。正解: UserControl 内所有 `{x:Bind}` 改为经典
  `{Binding}`(运行时沿 DataContext 链解析),并删掉 x:DataType。批量替换:
  `python3 -c "src=open('TaskCard.xaml').read(); open('TaskCard.xaml','w').write(src.replace('{x:Bind','{Binding'))"`。
  注意: DataTemplate 里的 `x:DataType` 是有效的(定义模板数据源类型),但
  UserControl 根元素上的 x:DataType 不改变 x:Bind 的绑定源——两者别混淆。
- 排查: `gh run view <id> --log | grep -E "WMC|error CS"` 一次拿全所有 WMC 错误再批量修,别改一个推一次。

**③ 迭代循环**: 静态修复 → push → `gh workflow run` → 读错误日志 → 修 → 重推。
首次云构建往往要 2-3 轮(缺包引用 → XAML 错误 → 才到打包/上传)。每轮都要
pull 完整错误日志(`gh run view <id> --log | grep -E "error|WMC"`),不要只看
监控脚本抓到的模糊 "exit code 1"。

**④ XAML Pass2 编译链(最隐蔽,卡最久)**: 包引用和 XAML 语法都修好后,仍报
`WMC1509 No LocalAssembly` + `WMC0001 Unknown type` + `WMC0909 Cannot resolve
DataType` + `WMC9999`——**这不是你的类型有问题**(文件都在、namespace 都对),
是编译链不对: dotnet publish 和 dotnet msbuild 都缺 MarkupCompilePass2 的
LocalAssembly 传递。唯一解: `microsoft/setup-msbuild@v2`(vs-version 指定,如
'17.8')把 VS 的 msbuild.exe 加进 PATH,再用裸 `msbuild /t:Publish`。

**⑤ C# 编译错误(过了 XAML 才暴露,静态审查查不出)**:
- `CS1061: 'SettingsWindow' does not contain 'ShowAsync'`: WinUI 3 的 Window
  没有 ShowAsync(那是 ContentDialog 的),用 `settingsWindow.Activate()`。
- `CS0191: A readonly field cannot be assigned to`: 只读字段在方法里赋值
  (如 `_taskPid` 在 Start() 里 `= _process.Id`),改非 readonly 或构造器赋值。
- `CS1061: 'ResolutionItem'/'FrameRateItem' does not contain 'Value'`: 自定义
  模型类是普通类没有 `.Value` 包装,直接用 `.Width` / `.Fps`(nullable 用
  `is { } w` 模式匹配)。

## 验证

- 本机无 dotnet: 静态审查清单 + 问题模式核对 + 汇报如实标注"未编译,需 Windows 验证"。
- 有 Windows 环境: `dotnet build` → MSIX 打包 → 真机冒烟(转码/暂停/恢复/取消全路径)。
