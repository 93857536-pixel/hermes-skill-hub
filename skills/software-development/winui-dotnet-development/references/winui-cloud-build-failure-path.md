# WinUI 3 首次 GitHub Actions 云构建:失败路径全记录

来源: MediaConverter 2026-08 实战(macOS 本机无 dotnet,远程 windows-latest 编
Windows EXE)。**首次云构建必踩 4 层坑,每层对应一类错误;按序排查,别乱改。**

## 失败层级总览(按出现顺序)

| 轮 | 症状 | 根因 | 修法 |
|----|------|------|------|
| 1 | CS0246 IValueConverter / CS0234 Microsoft.UI.* 找不到 | csproj 缺 PackageReference(UseWinUI>true 不够) | 加 WindowsAppSDK + BuildTools 包引用 |
| 2 | WMC0055 RequestedTheme='Default' / WMC0011 Unknown member MinWidth/Resources/VerticalScrollBarVisibility | XAML 用了 UWP 属性,WinUI 3 没有 | 删属性/移 Resources 到 Grid |
| 3 | WMC1509 No LocalAssembly + WMC0001/WMC0909 本项目类型解析失败 | dotnet publish 不走 XAML MarkupCompilePass2 | 换 dotnet msbuild /t:Publish |
| 4 | "The term 'msbuild' is not recognized" | msbuild 不在 windows-latest PATH | 用 dotnet msbuild(不是裸 msbuild) |

## 第 1 层: 缺 PackageReference

`UseWinUI>true` 本身不够。缺失症状全是"引用解析失败":
- `error CS0246: IValueConverter could not be found`(BoolToVisibilityConverter.cs)
- `error CS0234: 'Dispatching' does not exist in 'Microsoft.UI'`
- `error CS0234: 'Windows' does not exist in 'Microsoft'`(AppNotifications)
- `error CS0234: 'UnhandledExceptionEventArgs' does not exist in 'Microsoft.UI.Xaml'`

修法(版本先校验再写入):
```xml
<ItemGroup>
  <PackageReference Include="Microsoft.WindowsAppSDK" Version="1.8.260710003" />
  <PackageReference Include="Microsoft.Windows.SDK.BuildTools" Version="10.0.26100.7705" />
</ItemGroup>
```
版本校验: `curl https://api.nuget.org/v3-flatcontainer/<包名小写>/index.json | python3 -c "import json,sys; print(json.load(sys.stdin)['versions'][-3:])"`
⚠️ 教训: 本会话写了 BuildTools 10.0.26100.3916(不存在),还原直接失败;先查列表再写。
WindowsAppSDK 选 1.8.x 稳定线(项目 API 兼容),BuildTools 选 10.0.26100.x 存在的版本。

## 第 2 层: XAML 编译器错误(WMC 前缀)

静态审查永远看不出来,必须真编译才暴露。一次 grep 拿全再批量修:
`gh run view <id> --log | grep -E "WMC"`

- `WMC0055: Cannot assign text value 'Default' into 'RequestedTheme' of type
  'ApplicationTheme'` — Application 根标签不能写 RequestedTheme="Default"
  (枚举只有 Light/Dark;跟随系统是默认行为,直接删属性)。
- `WMC0011: Unknown member 'MinWidth'/'MinHeight'/'Resources' on element 'Window'`
  — WinUI 3 的 Window 没有这些属性(那是 UWP 的)。删尺寸属性;
  `Window.Resources` 移到根元素(如 `<Grid.Resources>`)。⚠️ 移 Resources 时注意
  别把原有 xmlns 声明重复粘贴(XML 属性重复会再报错)。
- `WMC0011: Unknown member 'VerticalScrollBarVisibility' on element 'TextBox'`
  — 该属性属于 ScrollViewer;TextBox 上没有,直接删。

## 第 3 层: dotnet publish 缺 XAML 编译链(最隐蔽)

**症状**: 包引用修好、XAML 语法修好之后,仍然报:
```
XamlCompiler warning WMC1509: No LocalAssembly parameter given during
  MarkupCompilePass2 ... will likely cause type resolution errors
XamlCompiler error WMC0001: Unknown type 'BoolToVisibilityConverter'
  in XML namespace 'using:MediaConverter.Converters'
XamlCompiler error WMC0909: Cannot resolve DataType viewmodels:TaskItemViewModel
XamlCompiler error WMC0001: Unknown type 'TaskCard' in XML namespace 'using:MediaConverter.Views'
XamlCompiler error WMC9999: Object reference not set to an instance of an object
```
**注意**: 这些错误**不代表你的类型有问题**——类型文件都在、namespace 都对。
根因是 `dotnet publish`(dotnet CLI)不走完整 XAML MarkupCompilePass2 链,
LocalAssembly 没传进去,项目自身类型全部解析失败。

**修法**: 换 MSBuild 引擎的 publish:
```
dotnet msbuild Windows/MediaConverter/MediaConverter.csproj `
  /restore /t:Publish `
  /p:Configuration=Release /p:Platform=x64 `
  /p:RuntimeIdentifier=win-x64 /p:SelfContained=true `
  /p:EnableMsixTooling=true
```

## 第 4 层: msbuild 不在 PATH

换 msbuild 后立即报:
```
The term 'msbuild' is not recognized as a name of a cmdlet, function,
  script file, or executable program.
```
windows-latest runner 的 PATH 没有 msbuild.exe。**用 `dotnet msbuild`**
(dotnet 已由 setup-dotnet 安装,自带完整 MSBuild 引擎)。

## 迭代纪律

- 每轮 pull **完整**错误日志: `gh run view <id> --log | grep -E "error|WMC|not recognized"`
  后台监控脚本抓到的模糊 "exit code 1" 不够定位。
- 一次修一类错误,批量修完再推(如第 2 层把所有 WMC 一次修完),别改一个推一次。
- 触发: `gh workflow run windows-build.yml --ref main -f tag=v1.0.0`
  轮询: `gh run view <id> --json status,conclusion`
- 成功判据: run completed/success + `gh release view <tag> --json assets` 出现
  MediaConverter-Windows.zip。
