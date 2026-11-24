; Media Converter - Windows 安装器 (Inno Setup)
; 由 GitHub Actions 调用: iscc /DMyAppVersion=X.Y.Z /DPublishDir=<publish> installer.iss
; 产物: 单个 setup.exe,内含主程序 + 全部运行时 dll + bin/ffmpeg.exe + bin/ffprobe.exe
; 2026-08-11 实战验证: WinUI 3 自包含产物是多文件,必须用安装器打包成单 exe
; (WinUI 3 官方不支持 .NET 单文件发布,裸 exe 跑不起来)。
; 仓库内位置: Windows/Scripts/installer.iss(与 workflow 同目录约定)

#define MyAppName "Media Converter"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppExeName "MediaConverter.exe"

[Setup]
AppId={{E4E0C8B4-6700-4C9C-8917-D651F54F34D8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=MediaConverter-Windows-v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"

[Files]
Source: "{#PublishDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent
