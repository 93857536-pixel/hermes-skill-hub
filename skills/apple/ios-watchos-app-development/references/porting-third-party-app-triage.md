# 第三方 iOS 项目搬运评估 (porting triage)

2026-09-05 实测案例: 用户要求把 GitHub YangJiiii/3105(577★ iOS「应用容器工作台」)功能"全部搬到"自家 app(DeviceToolbox)。产出三档拆解报告后用户选择干净移植。本文件是该方法论的浓缩。

## 为什么先做可行性拆解, 而不是直接搬

1. **许可证先查**: 3105 topics 含 gplv3、LICENSE 35KB=GPLv3 全文。逐行复制 → 目标工程整体 GPLv3 传染(含其反检测/exploit 姿态)。结论: 全部"读设计→原创重写", 只按互操作还原格式事实(magic/字段布局/加密参数), 不抄表达。
2. **能力地基分层**: 3105 的独特功能(浏览/改任意 app 容器、跨设备补丁、清他人缓存)100% 依赖沙盒逃逸——**没有 exploit 时它就退化成"只能管自己沙盒的文件管理器"**。iOS 沙盒是平台硬边界, "零 hack 前提下 1:1 全搬"数学上不成立。向用户摆这个事实比闷头搬重要。
3. **模拟器矛盾**: 漏洞利用代码按真机固件版本逐版 offsets(kexploit_opa334 等), 模拟器无内核漏洞可言 → 移植物在本机无法验证, 真机有变砖/数据损坏风险。

## 三档拆解(报告结构, 可直接复用)

- **第一档 可直接学**(纯逻辑/公开 API): 编解码格式层(PatchPackageCodec 的 AES-GCM envelope 思路)、事务/journal 回滚引擎、文件操作错误/冲突策略枚举、自写 ZIP(防 zip-slip)、项目库状态机、仓库/市场(URLSession)、UI 设计系统。
- **第二档 须重写**(3105 用特权/私有实现, 概念保留、数据层换公开 API): 容器浏览→只能列自己沙盒(Documents/Caches/tmp); Patch 目标→只能自己文件; Cleaner→只分析自己容器; 壁纸安装→系统无公开 API, 只能做预览器。
- **第三档 不可搬**(exploit/私有/对抗): kexploit 目录(krw/kutils/offsets/vnode/xpaci/sandbox_escape)、私有框架桥(mcm_bridge=MobileContainerManager)、AntiDetection、伪装系统 bundle ID + enterprise 证书、混淆归因水印(见下)。
- 每档给模块名+源码依据文件+行数+干净复刻要点; 末尾给分范围工时(最小文件浏览器 0.5-1 天 / 完整工作台 1.5-2.5 天)+ 建议路径。

## 依赖指纹 grep(快速判定"私有/exploit 依赖有多深")

```bash
# 1) import 全景 — Swift 层全公开框架 => 私有能力必在 ObjC/C bridge
grep -rh "^import" --include="*.swift" . | sort | uniq -c | sort -rn
# 2) 私有框架/系统路径特征
grep -rliE "MobileContainerManager|MobileHouseArrest|MCM|LSApplicationWorkspace|containerURLFor|LBApplication|SBSApplication|mcm_" .
# 3) exploit 特征 + 运行时手法
grep -rliE "krw_|kread|vnode_|sandbox_escape|KernelExploit|xpc" .
grep -rlnE "NSClassFromString|respondsToSelector|iconDataForVariant|dlopen|dlsym|NSSelectorFromString" .
```

Swift 层只 import 公开框架(Foundation/SwiftUI/CryptoKit…)通常意味着作者把私有能力收敛在少量 bridge 文件里 → 拆解边界清晰, Swift 上层多为可借鉴设计。

## 反搬运水印警告(容易被忽略)

3105 的 DisplayIdentity.m 含**混淆归因/启动校验**(kAttributionSeed 字节数组 ^ (0x5A+i*7) 解出作者 URL; 注释明言"removing this file breaks launch checks")——作者故意对抗直接搬运, 二进制里无明文 github 字段。复制此类文件 = 把作者的校验/归因逻辑带进自家 app。拆解时专门 grep 混淆字节/自异或解密模式, 归入第三档。

## 干净移植的工程组织(本案落地)

磁盘规格 WORKBENCH-SPEC.md(12KB)驱动并行: 铁律(全公开 API/零依赖/禁逐行复制/只读锚点)、文件归属表(谁写谁, 防双写)、跨域契约精确签名(共享类型字段逐一列出)、兄弟域缺失→"记录缺失符号清单, 不许补写兄弟域"(UI 代理 swiftc -parse 自检兜底)、测试归属(Codec 往返/事务回滚/ZIP 安全)、汇报格式(含新增本地化 key 清单, Localizable.strings 由主会话统一合并防双写)。关键互操作决策: 兼容格式解码(读原码理解 → 自写), 导出可用自家格式降级。
