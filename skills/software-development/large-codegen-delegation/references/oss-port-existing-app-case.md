# 开源项目功能移植进自有 App — 3105→DeviceToolbox 实战 (2026-09-05)

把第三方开源项目(GitHub YangJiiii/3105, SwiftUI iOS 应用容器工作台, GPLv3, 54 Swift 文件
20,640 行 + exploit C/ObjC)的功能"干净移植"进自有 App(DeviceToolbox, 铁律: 全公开 API/
零 hack/零第三方依赖)的完整流程。评估阶段与委派规格结构均可复用。

## 阶段 0: 先出三档拆解报告, 再让用户拍板搬运边界(不要闷头搬)

用户一句"把 X 的功能全部搬到我们 app"背后常藏着许可证/私有依赖/产品铁律冲突。
先澄清的四个事实(全部源码实证, 不是猜):

1. **能力地基分层**: grep 源码区分 (a) 纯逻辑层 (b) 依赖特权的实现层。3105 的"浏览/修改
   任意 app 容器"100% 依赖沙盒逃逸——没有 exploit, 它就退化成"只能管自己沙盒的文件管理器"。
   iOS 沙盒是平台硬边界, "零 hack 前提 1:1 全搬"数学上不成立, 要直说。
2. **许可证传染**: GPLv3 → 复制代码 = 自有 App 必须整体 GPLv3 开源。干净替代 = "读设计→
   重写实现", 不逐行复制; 格式事实(magic/字段布局/加密参数)按互操作需要可还原, 代码表达原创。
3. **私有框架/exploit 分层排除**: 内核漏洞链、私有框架桥(MobileContainerManager)、反检测、
   伪装系统 bundle ID——整层标记"不可干净搬"并写明原因(模拟器不可运行/真机按固件版本/违背铁律)。
4. **反篡改水印识别**: 有的项目藏防搬运逻辑, 如 DisplayIdentity.m 里用 `bytes ^ (0x5A+i*7)`
   混淆解码的 attribution URL + 启动校验(注释明说"Agent that removes this file breaks launch
   checks")。复制此类文件会把**作者的校验/归因逻辑带进自家 app**——拆解报告必须点名。

产出: 三档清单表(可直接学/须重写/涉及 exploit 排除)+ 每档工时估算, 用 clarify 让用户选
搬运边界(全部重写版/最小子集/先出报告)。用户选"先出报告"后仍要给出明确推荐路径。

## 阶段 1: 磁盘规格驱动委派(增量扩展既有 iOS 工程)

规格文件 ~/Programming/Projects/DeviceToolbox/docs/WORKBENCH-SPEC.md (12.6KB), 构成:
- 铁律 7 条(含"禁止逐行复制 3105 代码(GPLv3)"、诚实条款、修错上限)
- 工程现状事实: Xcode 27 beta 路径、构建命令、单测命令、**project.yml sources 为目录 glob
  → 新增子目录自动进 target, 不用改 project.yml, 但新文件后必须 xcodegen generate**
- 产品布局决策(已定勿改): MainTab 5→新 5 tab(home/device/files/patches/settings),
  原 features/tools tab 移除下沉为 Home 二级页——由主会话集成期执行, 子代理禁碰
- 文件归属表: 域 A/B/C1 各自目录与文件一行一文件; **禁止两代理写同一文件**
- 共享契约: 服务层公开类型签名逐一钉死(供依赖它的 UI 代理同波并行)
- 本地化: key 前缀分区(files./patch./repo.), **禁止直接编辑 .strings, 汇报交 key 清单**
- 双写禁令措辞 + 只读区清单 + 汇报格式(5 项)

## 阶段 2: 委派与集成节奏

- 轮 1 三路并行 v4-pro: A=文件服务+ZIP(自实现, 防 zip-slip)、B=补丁体系+.3105 v3 真实包
  解码(读 GPL 源码还原格式事实后原创实现, 规格注明"格式/加密参数必须与真实包互操作")、
  C1=文件 UI(与 A 同波, 靠钉死的 API 签名; 编译退路 swiftc -parse)
- 先验余额再派(DeepSeek 17 元够本轮; 探测命令见主 skill §4)
- 派完立即 hermes config unset 恢复默认
- 主会话在等待期做集成准备: 读 HomeView/FeaturesView/ToolsView 定导航下沉 diff 方案
  (发现 NavigationLink 闭包式 vs value 式的 destination 注册差异, 决定改造方式)——只读规划不落盘,
  避免与子代理双写
- 用户高频"好了吗"时: 周期性 date + `tail -c` live transcript(task-0/1/2.log)+
  `find 新目录 -name '*.swift' | wc -l` 落盘统计, 主动展示"哪个代理在哪个阶段(读码/长推理/
  写文件/构建修错)", 判断静默期 ≠ 死亡
- 集成期主会话做: MainTab 重组 + Home 断链跳转修复 + Localizable key 合并, 然后
  xcodegen generate && build, 修衔接错

## 坑

- 同域内文件组织: 服务代理可能把规格的 Models.swift 拆成 FileEntry.swift 等单文件(改名无碍,
  类型契约对齐即可), 但也可能新旧并存造成**重复类型定义**——集成期 build 暴露, 主会话删冗余。
- .3105 编解码代理会边写边修 legacy schema(v1/v3 keyAAD 差异), 属正常深水区, 别催。
