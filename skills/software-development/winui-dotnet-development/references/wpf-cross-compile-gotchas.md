# WPF 交叉编译的专属坑（macOS 上 EnableWindowsTargeting）

VoiceNotes Windows 版（WPF + WindowsForms + NAudio）在 macOS 交叉编译实战。
这些是 `dotnet build -p:EnableWindowsTargeting=true` 才暴露的编译错误，静态审查永远看不出来。

## 参考 csproj 组合

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>WinExe</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <UseWPF>true</UseWPF>
    <UseWindowsForms>true</UseWindowsForms>   <!-- NotifyIcon 托盘需要 -->
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <AssemblyName>VoiceNotes</AssemblyName>
    <RootNamespace>VoiceNotes</RootNamespace>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="NAudio" Version="2.2.1" />   <!-- 录音 + MediaFoundation 解码 -->
  </ItemGroup>
  <ItemGroup>
    <!-- 关键：WinForms 会注入隐式 global using，和 WPF 同名类型歧义 -->
    <Using Remove="System.Windows.Forms" />
  </ItemGroup>
</Project>
```

## 编译坑清单（全部本会话实测验证）

### 1. `Application` 歧义（CS0104）
`UseWindowsForms=true` 时 `System.Windows.Forms.Application` 与 `System.Windows.Application` 同名。
两种修法：
- csproj 加 `<Using Remove="System.Windows.Forms" />` 移除隐式 using（推荐，一劳永逸）；
- 或在 App.xaml.cs 用别名 `using Forms = System.Windows.Forms;` 并全限定 `Forms.NotifyIcon` 等。
症状原文：`CS0104: "Application"是"System.Windows.Forms.Application"和"System.Windows.Application"之间的不明确的引用`。

### 2. `x:Static` 必须带命名空间前缀（MC3050）
`{x:Static BoolToVisConverter.Instance}` 不带前缀 → `MC3050: 无法找到类型"BoolToVisConverter"。请注意，类型名区分大小写。`
正解：`xmlns:local="clr-namespace:<根命名空间>"` + `{x:Static local:Converter.Instance}`。
坑点：该错误在 C# code-behind 编译**通过之后**才暴露——WPF 的 MarkupCompilePass 顺序让
code-behind 错误先报，XAML 错误后报，所以修复时要一轮轮看新增错误。

### 3. `SaveFileDialog` 需 `using Microsoft.Win32;`（CS0246）
WPF 的 SaveFileDialog 在 `Microsoft.Win32` 命名空间，不在 System.Windows。

### 4. `BorderDashCap` 不是 WPF Border 的属性
虚线边框别想用 Border；只有 `Rectangle` 才有 `StrokeDashArray`/`StrokeDashCap`。Border 上写
`BorderDashCap="Round"` 会 XAML 编译失败（直接删掉该属性）。

### 5. `new Uri(@"C:\path\file.wav")` 在 .NET 8 是安全的（不要画蛇添足）
实测（.NET 8，纯 BCL，平台无关）：
```csharp
foreach (var p in new[]{ @"C:\Users\foo\录音 20260825.wav", "C:/Users/foo/a.wav" })
    try { Console.WriteLine(new Uri(p).AbsoluteUri); }
    catch (Exception ex) { Console.WriteLine("THROW: " + ex.GetType().Name); }
// 输出: file:///C:/Users/foo/%E5%BD%95%E9%9F%B3%2020260825.wav
```
结论：`new Uri(path)` 会把 Windows 盘符路径正确解析为 `file:///C:/...`（自动转义中文/空格）。
WPF `MediaPlayer.Open(new Uri(path))`、`BitmapImage(new Uri(path))` 直接可用，**无需**手写 `file:///` 拼接。

### 6. 隐式 using 与 System.IO 的误解
spec 常写"WPF 隐式 using 不含 System.IO"——实际上 .NET SDK 隐式 using **含** System.IO。
稳妥做法：每个用到 File/Directory/Path 的文件显式 `using System.IO;`（冗余 using 不报错、零成本）。

## NAudio 关键 API（录音 + 转码，录音→16k 单声道 WAV 喂 whisper）

- 录音：`new WaveInEvent { WaveFormat = new WaveFormat(16000,16,1), BufferMilliseconds = 100 }`
  + `DataAvailable` 回调里 `WaveFileWriter.Write(buffer, 0, bytesRecorded)`；RMS 音量
  `BitConverter.ToInt16(buffer, i) / 32768f` 累加平方再 `MathF.Sqrt(sum/count)`。
- 任意格式 → 16k/16bit/mono WAV：
  ```csharp
  using var reader = new MediaFoundationReader(input);
  using var resampler = new MediaFoundationResampler(reader, new WaveFormat(16000,16,1)) { ResamplerQuality = 60 };
  WaveFileWriter.CreateWaveFile16(output, resampler);   // 自动回填 RIFF/data 长度
  ```
- 注意：m4a/aac/mp4/mov 依赖 Windows Media Foundation 编解码器；flac/ogg 直给 whisper 更稳
  （whisper main.exe 原生支持 wav/flac/mp3/ogg）。

## whisper.cpp 进程调用约定（Windows vendor 版）

- `main.exe -m <模型> -l zh -ojf -of <输出基名无扩展> -f <wav> -pp`，用
  `ProcessStartInfo.ArgumentList.Add()` 逐参添加自动处理路径空格，`UseShellExecute=false`。
- 退出码 0 但输出 json 不存在 = 失败（先 `Directory.CreateDirectory` 确保输出目录存在）。
- 解析双格式：`transcription[].offsets{from,to}`(毫秒 /1000) → `segments[].{start,end}`(秒) → 报"JSON 结构无法识别"。
