# Tauri v2 打包图标实战坑(2026-09, Hermes Agent Migrator)

## 首选: Tauri CLI 一键生成(2026-09-25 换图标实战,有 node/cargo 时走这条)
```
cd gui/src-tauri && npx @tauri-apps/cli icon /path/to/master1024.png
# 或免 npm: cargo tauri icon master.png
```
- 一次重生成 `icons/` 全套: icon.png / icon.icns / icon.ico + 32/64/128 PNG + `ios/AppIcon-*` 全套 + Android mipmap(前景/圆角) + Windows `Square*Logo.png`
- icons/ 目录会从 3 个文件变成几十个(**预期行为**),`git add -A gui/src-tauri/icons/` 整目录入库——各平台 release 构建都需要这些,不是垃圾
- 确认 `tauri.conf.json` 的 `bundle.icon` 数组含 icns: `"icon": ["icons/icon.icns", "icons/icon.png"]`
- 母版用技能主流程画好 1024 PNG(模板 icon_drawer.swift),CLI 只负责缩放打包;vision 自检照旧
- 下方 sips/iconutil 手工管线是 **fallback**(无 node/npm 网络且 cargo 不可用时才用)

## 原始问题(无 CLI 可用时): 手搓 sips/iconutil 管线
`cargo tauri build` 在 macOS 上打包 .app/.dmg 时,若 `icons/` 目录只有 PNG 没有 icns,bundler 会报错:

```
Bundling Hermes Agent Migrator.app ...
Error failed to bundle project: Failed to create app icon: `No matching IconType`
```

(应用本体编译成功,仅 bundle 步骤失败;`target/release/<bin>` 仍在。)

## 修复

1. 用 1024×1024 PNG 母版生成 `.icns`(目录名必须是 `.iconset` 结尾,见下):

```bash
cd gui && mkdir appicon.iconset && S=src-tauri/icons/icon.png
for spec in "16:icon_16x16" "32:icon_16x16@2x" "32:icon_32x32" "64:icon_32x32@2x" \
            "128:icon_128x128" "256:icon_128x128@2x" "256:icon_256x256" \
            "512:icon_256x256@2x" "512:icon_512x512" "1024:icon_512x512@2x"; do
  px=${spec%%:*}; nm=${spec##*:}; sips -z $px $px "$S" --out "appicon.iconset/$nm.png" >/dev/null
done
iconutil -c icns appicon.iconset -o src-tauri/icons/icon.icns   # 必须 .iconset 目录名!
```

2. `src-tauri/tauri.conf.json` → `bundle.icon` 数组加入 icns:

```json
"icon": ["icons/icon.icns", "icons/icon.png"]
```

3. 重跑 `cargo tauri build` → `bundle/macos/*.app` + `bundle/dmg/*.dmg` 正常产出。

## iconutil 的隐形要求(本次最大坑)

- **输入 iconset 目录名必须以 `.iconset` 结尾**(如 `appicon.iconset`)。目录名叫 `iconset`(不带点)时,即使 10 张 PNG 尺寸全对,`iconutil -c icns` 也只报一句 `iconset:Invalid Iconset.`(重复两行),无任何其他提示。换 `.iconset` 结尾的目录名后立刻成功。
- 10 张 PNG 命名精确为 `icon_16x16.png … icon_512x512@2x.png`(16/32/64/128/256/512/@2x 双份),尺寸逐一对应;可用 PNG IHDR(16-24 字节大端宽高)做确定性自检。
- `sips -z <px> <px>` 生成的 PNG 是 RGBA(samplesPerPixel=4, space RGB),iconutil 接受;无需转色深。
- 临时 iconset 目录构建完成后删掉,只留 `.icns` 进 git(避免 10 张 PNG 入库)。

## 顺带发现

- **最快路径: `npx @tauri-apps/cli icon <master.png>`**(在 src-tauri/ 目录跑)一条命令生成全套: icons/icon.icns / icon.ico / icon.png(1024)+ 各尺寸 PNG + iOS AppIcon + Android mipmap + Windows Store Logo。2026-09 hermes-agent-migrator 实战:1024 母版质量过关后,不必手拼 iconset;仅需 SHA256 比对 bundle 内 icns 与仓库 icns 确认新图标进了正式产物。

- 版本号不一致坑: tauri.conf.json / Cargo.toml 的 `version` 与 CHANGELOG、GitHub tag 应保持一致,否则 DMG 文件名带旧版本号(如 0.1.0 的 DMG 却挂 v0.2.0 release)。改 tag 前先把 `gui/src-tauri/Cargo.toml`、`gui/src-tauri/tauri.conf.json`(以及 workspace 版本)一并 bump。

## 增量实战(2026-09-30 hermes-agent-migrator 换图标二轮,已验证)

- **母版可以直接收用户发来的图(jpg 也行)**: `cargo tauri icon /path/img.jpg` 实测直接吃 1254×1254 JPG,不必先转 PNG/不必 PIL 抠白边; 生成前先 `cp -R src-tauri/icons /tmp/icon-backup-<ts>` 备份旧图标。
- **验证嵌入的确定性方法**: 构建后 `shasum gui/src-tauri/icons/icon.icns` 与 `shasum target/release/bundle/macos/<App>.app/Contents/Resources/icon.icns`(Tauri 打包后 icns 直接叫 `icon.icns`, 不是 `app_icon.icns`——按 bundle 里实际文件名查 `Contents/Resources/`),**哈希逐字一致**即新图标进了正式产物; 别只看构建日志 "Bundling" 成功。
- **`cargo tauri build` 的 DMG 步骤报 `error running bundle_dmg.sh` 但 .app 已产出**(2026-09-30 实测, tauri-cli 2.11.4): 根因是生成的 `bundle_dmg.sh` 被单独跑/参数传递丢参, 报 `Not enough arguments`。 `.app` 本体与二进制不受影响(`target/release/<bin>` 正常)。兜底手打可分发 DMG:
  ```bash
  cd target/release/bundle/macos
  WORK=/tmp/dmg-stage; rm -rf $WORK; mkdir -p $WORK
  cp -R "<AppName>.app" $WORK/; ln -s /Applications $WORK/Applications
  hdiutil create -volname "<AppName>" -size 40m -fs HFS+ -srcfolder $WORK -o /tmp/raw.dmg
  hdiutil convert /tmp/raw.dmg -format UDZO -o /tmp/Out.dmg   # UDZO=可分发的压缩卷
  ```
  验证: `hdiutil attach -nobrowse` 挂载后 ls 看 .app+快捷方式在、`hdiutil detach` 卸载。
- **未签名 dev build 跑 `codesign -v <.app>` 会报 `code has no resources but signature indicates they must be present` 并 exit 1**: 这是未签名/ ad-hoc 状态, 不是产物损坏——与 某聊天App 未签名 IPA 同性质, 本地装/全能签重签都正常, 别因此误判构建失败。 交付未签名产物时向用户说明即可。
- 图标文件整目录入库: `git add gui/src-tauri/icons/` 一次全收(~50 文件, 含 android mipmap/ios 子目录), 不要挑文件 add, 否则 Windows/Android 端缺料。

## 兜底方案: 直接手写 .icns 容器(2026-10-31 实测, CraftCraft Launcher)

当 `iconutil` 反复报 `Invalid Iconset.` 又急着出包时, 可以**完全绕开 iconutil**, 用 Python 拼 icns。
icns 本质就是个「魔数 + 长度 + 一串带类型的 PNG 块」的容器, 现代 macOS 直接吃 PNG 载荷:

```
文件头: b'icns' + u32(总长度, 大端)
每个条目: 4字节类型码 + u32(条目长度, 含这 8 字节头) + 原始 PNG 字节
```

类型码与尺寸对应(全部直接塞 PNG, 不需要转 ARGB/JP2):

| 类型码 | 尺寸 |
|---|---|
| `ic11` | 32px  (16x16@2x) |
| `ic12` | 64px  (32x32@2x) |
| `ic07` | 128px |
| `ic08` | 256px |
| `ic09` | 512px |
| `ic10` | 1024px(512x512@2x) |

要点:
- 每个尺寸先用 PIL/sips 缩好存成独立 PNG, 再一次拼容器; 条目顺序不影响识别。
- 产物 284KB(6 个尺寸)即可被 `tauri build` 正常消费, `.app` + `.dmg` 全部产出。
- **别用 `file <x>.icns` 判断成败**: 部分沙盒环境 libmagic 版本不匹配会对合法 icns 报错,
  以「文件大小合理 + `tauri build` 不报 `No matching IconType` + bundle 里 `Contents/Resources/` 有 icns」为准。
- 这条是 **fallback**: 优先 `npx @tauri-apps/cli icon <master.png>`; 其次是修好 iconset 目录名走 iconutil;
  两者都不可用时再手拼容器。
