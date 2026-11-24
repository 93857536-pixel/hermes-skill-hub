# 模拟器"边写边看"实时循环 (Device Hub 常显 + 自动构建安装重启)

适用: 用户要求"我写代码时, Mac 上的 iPhone 模拟器画面要实时跟着变"(2026-09-25 DeviceToolbox 实测, Xcode 27 beta / macOS 27.2 / iOS 27.0 模拟器)。

## 交付前必说清的上限
- 模拟器**没有官方热更新**, 刷新粒度 = 增量 xcodebuild 时长(秒级), 不是敲字毫秒级。用户说"实时更新"时先对齐这条, 否则会被纠正(本轮就因给手动方案被纠正了一次: "可是这样子弄的话就不能实时更新和显示画面了啊")。
- **默认交付自动监听循环, 不要手动三连**。用户拒绝任何需要他手动触发的"构建→安装→启动"流程。

## 三件套
1. **Device Hub 常显**: `xcrun simctl boot <UDID>` + `open -a /Applications/Xcode-beta.app/Contents/Applications/DeviceHub.app`。Xcode 27 无独立 Simulator.app, 模拟器画面只在 Device Hub 窗口里(内嵌实时, 非示意图)。窗口要一直开着。
2. **监听循环**: 后台跑 `scripts/sim-live-watch.sh`(本 skill 目录自带):
   ```bash
   sim-live-watch.sh <项目目录> <scheme> <app-bundle-id> <sim-UDID> [warm-DerivedData 目录]
   ```
   - macOS 自带 `find -newer marker` 2s 轮询, **零依赖**(fswatch 常装不了: brew 走死代理 127.0.0.1:1082, 本环境直接放弃第三方监听器)。
   - 源码落盘 → 增量 xcodebuild → simctl terminate+install+launch, 全程自动; 事件日志 `<项目>/.live-review-events.log` 可查每轮结果。
   - **构建失败不更新 marker**, 10s 后自动重试(自愈); 成功才 touch marker。
   - 用后台进程跑(terminal background=true, **不**要 notify_on_complete——这是常驻 daemon)。
3. **AI 自审**: 每轮改动后 `xcrun simctl io <UDID> screenshot /tmp/x.png` + vision_analyze, 自动对比改动前后界面, 不靠用户口头报。

## 本轮踩过的坑(2026-09-25)
- **Metal Toolchain 缺失**: 全新 DerivedData 全量构建含 .metal 的工程报 `error: cannot execute tool 'metal' due to missing Metal Toolchain`。修法: `xcodebuild -downloadComponent MetalToolchain`(Apple CDN 直连, 国内免代理, 装完即用), 验证 `xcrun --toolchain MetalToolchain metal --version`。已有热缓存的增量构建不碰 metal, 老缓存目录能一直过——别误以为没事。
- **用 warm DerivedData 启动循环**(第 5 个参数): 指向 `build/dd-*` 等已有模拟器缓存目录可跳过全量重编, 首轮秒级完成; 冷启动全量构建要 1-3 分钟, 期间循环空转是正常现象, 看 events.log 判断。
- **App 的 bundle id 可能与产物名不同**(如伪装 MHA 的 `com.apple.mobile.MobileHouseArrest`): 循环的 app-bundle-id 参数取自 project.yml 的 PRODUCT_BUNDLE_IDENTIFIER, 别拿 scheme 名当 bundle id。
- **临时产物 git 忽略**: `.live-review-dd/ .live-review-marker .live-review-events.log .live-review-build.log` 加进项目 .gitignore, 本地提交即可, 不必推公开仓库。
- 演示改法: 改一处醒目 UI(如导航大标题)→ 等 2-4s 循环自动刷 → 截图 vision 验证 → **再改回去**验证双向闭环 → 确认 `git diff` 干净。
