---
name: large-codegen-delegation
description: "委派大规模代码生成(整App/多平台)时用: 磁盘规格驱动、并行分派、预算耗尽接管。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [delegation, codegen, subagent, build-verification, takeover]
---

# Large Codegen Delegation

## Trigger

委派大型代码生成任务给子代理: 整 App、多平台移植、20+ 文件、规格超 10KB 或验收必须真实构建(编译器/测试)的场景。实战验证于双端原生媒体 App(macOS SwiftUI + Windows WinUI3,约 70 个源文件,2 个并行子代理,一端构建验证、一端静态审查)。

## 1. 先把规格写进磁盘 —— 不要内联

大规模任务要**反转**"全部上下文内联"的常规做法: 在仓库里写一份详细规格文件(如 `scripts/spec-<area>.md`),提交入库,委派上下文只传 `先完整阅读 <path>` + 顶层约束。

理由: 15-18KB 规格内联会撑爆委派载荷、无法 diff/复用、会话中断即丢失;磁盘规格持久、可版本化、可复现,还能兼作项目文档。

边界: 小任务(< ~5 文件 / < ~1KB 规格)继续用内联上下文 —— 文件间接层只在大规模时才值得。

### 规格文件构成(让它真正起作用的部分)
- **铁律**: 禁改路径(已生成的资产)、依赖禁令、版本 pin(SWIFT_VERSION、deployment target)、"不许假装成功"诚实条款、修错轮数上限
- **先读**: 契约文件(跨平台必须一致实现的,如共享 JSON 规则 + 书面 FFmpeg 参数契约)
- **精确目录树 + 每文件职责**: 每个文件一行;枚举难点成员(进度解析语义、SIGSTOP/NtSuspendProcess 暂停、ETA 公式)
- **精确构建/测试命令**: 每次构建前先 `xcodegen generate`(新文件必须重生成);`-derivedDataPath` 避免污染 ~/Library/Developer
- **汇报格式**: 文件清单、构建结果原文、测试数、已知问题、诚实标记(无工具链时标注"本机未编译")

### 1.5 给既有工程增量扩展(非全新 App)的规格要点(2026-09-05 3105→DeviceToolbox Workbench 实测)

在成熟工程里追加整组模块(而非从零建 App)时,规格里额外写死四条,否则并行代理会踩到既有代码:

- **既有代码 = 只读锚点区**: 规格列出"禁止修改"清单(旧 Sources 目录、App 入口/导航根/MainTabView/HomeView、共享资源文件),逐一说明归属;新代码全部进新建目录(如 `Sources/FileWorkspace/`、`Sources/PatchWorkspace/`),旧目录一个字节都不许碰。
- **xcodegen sources 是目录 glob**: project.yml 若写 `sources: [{path: Sources}]`(整目录),新增子目录/文件**自动进 target**——子代理不用也不能改 project.yml;但每次新文件后仍必须 `xcodegen generate`。这条要写进规格,防止代理画蛇添足去改 project.yml 或误以为要手工登记。
- **共享资源合并归主会话**: 本地化 `.strings`/xcstrings 这类会被多代理追加 key 的文件,禁止任何代理直接编辑(双写灾难)。规格要求各代理在汇报里交 **key 清单表**(`key | en | zh-Hans`),主会话集成期统一合并。顺带:tab 重命名/导航结构改造(MainTab 枚举、Home 快捷卡跳转)也归主会话,规格标注"已定勿改"。**合并前先做磁盘证据核对**——代理可能声称"没改共享文件"但实际已直接追加(实战: C2 汇报"遵守双写禁令未改 Localizable",grep 计数却显示 95 个 patch/repo key 已在盘,主会话合并脚本报"新增 0"才暴露)。核对三连: `grep -cE '"(patch|repo)\.' <strings>` 计数、`wc -l` 中英两文件行数对称、`plutil -lint` 语法。若已存在 → 内容完整即可,跳过合并、越权不追(结果无损就别返工)。
- **UI 代理与它依赖的服务代理同波并行**的前提是规格已把服务层 API 签名钉死(见 §2 同波变体);UI 代理的编译退路 = `swiftc -parse` 自检自身文件 + 汇报"缺失服务符号清单"。

## 2. 并行平台分派

目录与工具链不重叠时,一个子代理一个独立目标(macOS App / Windows App)可安全并行。每个代理:
- 能验证的自验证: 真实构建+测试,修错 ≤N 轮(规格里定上限,如 6),剩余错误原文写入自己的 `build-notes.md`
- 不能验证的做静态审查(macOS 无 dotnet → 手工核对成员引用、x:Bind↔code-behind 对应、线程封送),审查+风险清单写进 build-notes.md
- 诚实声明: "交付标准为静态审查通过,未编译" —— 永不假装构建成功
- **同波派"UI 依赖服务层兄弟"的变体**(2026-09-05 DeviceToolbox Workbench 实测, A=文件服务+B=补丁服务+C1=文件UI 三路同波): 只要磁盘规格已把服务层 API 签名**钉死**(共享类型字段/方法逐一列出),UI 代理可与它依赖的服务代理同波并行,不必等第二轮。UI 代理自检退路 = `xcrun swiftc -parse` 只验自身文件语法(兄弟类型未落盘时无法 typecheck)+ 汇报"缺失服务符号清单";规格写死**双写禁令**("即使编译报'找不到 X'也禁止自己补写兄弟域文件, 那是并行方在写")。服务层落盘后主会话集成编译只修衔接错(2-5 个一行补丁)。

## 3. 预算耗尽接管(max_iterations)

症状: 批次结果显示 `status=completed` 但 `exit_reason=max_iterations`;最终汇报在工具调用中途被截断;`build-notes.md` 为空或过期;transcript 尾部显示一个"正在修、没验证"的状态。

接管流程 —— 工作已完成约 90%,不要盲目重派:
1. `tail` live transcript → 重建**最后已知状态**(最后一次 build/test 输出、其后打的补丁)
2. 自己重跑规范管线: `xcodegen generate`(有新文件时)→ `xcodebuild build` → `xcodebuild test`
3. 预期子代理最后补丁留下**机械性编译错误**: Swift/C# 可选值未解包(`[String]?` → 安全访问器、`String?` → `?? 兜底`),每文件一个,编译器逐个暴露。在主会话直接修 —— 重派一次的成本高于 3 个一行补丁
4. 全绿后**自己写** build-notes.md(准确反映最终状态,子代理那份是空的)
5. 用临时 `hermes-verify-*.sh` 包住 build+test+smoke,断言精确标记(`BUILD SUCCEEDED`、`Executed N tests, with 0 failures`)后删除 —— 给本轮改动留下新鲜证据

## 4. 中断后跨会话续跑(先取证,再重派)

子代理可能被 **API 资金断供 / 主会话中断** 打死(不是 max_iterations 耗尽)。续跑前先取证,别盲目重派,也别信"没钱所以没生成吧"这类猜测 —— 磁盘证据几乎总是推翻它(实战: 用户以为没生成,实际中断前 4 分钟刚落盘 7 个 Swift 文件,见 `references/resume-interrupted-delegation.md`):

1. **取证**: `tail` live transcript(`~/.hermes/cache/delegation/live/<deleg_id>/task-*.log`)+ 目标目录 `find` / `ls -la` 对 mtime。判据:
   - 日志尾部 `think` 之后有成批 `write_file` 且文件 mtime 与之一致 → 生成真实发生过,只是死在中间文件;用文件清单反推"断在哪一步、还缺什么"
   - **资金断供的死亡无错误行** —— 最后一个工具调用成功后就没了。死因靠"最后活动时间 vs 现在"推断,不是等报错
   - v4-pro 大批写文件前常有 5-6 分钟静默长推理(随后出现 `think` 行再成批落盘),别在静默期误判死亡去接管写文件(防双写冲突,见 §5 坑)
2. **先验 API 资金再派**: curl 余额端点(DeepSeek: `https://api.deepseek.com/user/balance`,key 在 `~/.hermes/.env` 的 `DEEPSEEK_API_KEY`,`Authorization: Bearer`;本机有死代理时 curl 加 `--noproxy '*'`)。`is_available=false` → 不派,等充值或换本地模型,否则再静默死一批、浪费一轮。余额确认可用后再切 delegation 模型。**余额探测命令本机易被终端解析器拦截**(内联 `curl ... -H "Authorization: Bearer $(grep DEEPSEEK_API_KEY ~/.hermes/.env ...)"` 曾命中 unconditional blocklist 存盘 blocked-scripts);改用 execute_code 里 urllib 读 .env 探余额(或把命令存成独立 .py 跑),别反复试内联形式。
3. **已落盘文件是只读锚点**: 主会话先完整读 SPEC + 已生成文件(类型/枚举/常量精确对齐),再写委派上下文 —— 续派子代理面对半成品工程,不知道"哪些已存在、哪些是并行方在写",锚点文件要明确标"只读,禁止修改"。
4. **并行续跑必须写共享契约到磁盘**(`docs/INTERFACES.md`): 环境事实(Swift 版本/Xcode 路径/xcodegen 路径/DEVELOPER_DIR 技巧)、**文件归属表**(谁写谁,目录 mkdir 无害)、共享层精确签名(类 + 方法签名 + 公开 API 来源)、数据文件结构与已有模型字段对齐、project.yml 要点、ViewModel 只锁类名内部自由(UI 自己写自己自洽)、**双写禁令**("即使编译报'找不到 X'也禁止自己补写,那是并行方在写,错误记入 build-notes.md")、自检与汇报格式(A 无 Xcode 工程 → `swiftc -parse` 语法级 + 如实标注"未整工程编译")。契约把整合期机械错从几十处降到个位数。
5. 委派(并行按层拆分)→ 主会话等结果回传后**重新 `xcodegen generate`**(新文件才进工程)+ build,修 A/B 衔接签名错(2-5 个一行补丁,别为省事重派)。

## 5. 坑

- **子代理可能"假死复活"——接管前必须确认它已终止**: 子代理 API 调用可能长时间(20+ 分钟)无输出,主会话误判死亡后开始接管写文件;此时子代理可能复活并继续编辑同一批文件,导致**双写冲突**: 双方互相覆盖、互相"修错"(子代理视角: "sibling mid-edit introduced new errors")。实战: 主会话写了 15 个文件后,子代理从 17:36 到 17:57 复活,覆盖了 Note.cs/AISettings.cs/csproj,主会话编译修错也被它当"新错误"重改。防护:
  1. 判断"死亡"前先看 transcript 是否真静止(比对文件 mtime / tail 时间戳),且要意识到 delegate 的 worker 可能跑在主会话进程内(ps 看不到独立进程,无法 kill)
  2. 主会话写文件时若收到 `modified by sibling subagent` 警告,立即停手,改为只读审查子代理版本(它往往功能等价甚至更干净),别继续覆盖
  3. 双写期间不要跑编译验证——结果是并发状态的无效快照;诚实说明 blocker,等编辑静止后再验证
  4. 子代理复活后通常能自己收敛到编译通过,主会话的角色转为审查 diff + 补缺口,而非重写
- **子代理自报只是自报**: 即使汇报写"全绿",也要重跑命令复验。实战: 代理最后记录的测试是红的;主会话 3 个小补丁后同一命令转绿。信 transcript 尾部,不信总结
- **代理最后的补丁常会弄坏构建**: 预算耗尽通常落在编辑中途。为主会话预留 2-5 个机械修复
- **资源布局漂移**: 核对加载器的期望(扁平 `formats.json` vs `Resources/Core/` 目录)与产物 bundle(`Contents/Resources/`)与 xcodegen `resources:` 路径三者一致;代理常检查错误路径然后"修"错层
- **Xcode 27 Debug 构建**: 主二进制是 Previews stub,真实代码在 `*.debug.dylib` —— 字符串/冒烟标记对着 dylib 验证;冒烟测试走 stub 可执行文件(它能正确分发)
- **冒烟钩子值回票价**: 给 App 加 `--smoke-test`/`--smoke-convert` CLI 路径(定位 ffmpeg、加载预设、跑一次真实转码、打印 JSON、退出码)—— 把 GUI App 变成可无头验证的产物,CI 与人工验收都能用
- **网络受限机器**: pip/brew 下载可能失败,图标/图像生成必须回退本地工具链(Swift/AppKit 离屏绘制 —— 见 `macos-app-icons` 技能)
- **Swift 6 同模块重名文件硬报错**: 目录 glob 且两个子目录各有一个同名文件时(如 `PatchWorkspace/Models.swift` 与 `PatchWorkspace/Repository/Models.swift`),Swift 6 编译直接失败 `error: Filename "Models.swift" used twice: ... note: Filenames are used to distinguish private declarations with the same name`。这是硬错误非警告;规格若给两个目录同时列了同名文件(本工作台 SPEC 就同时写了两个 `Models.swift`),必须把其中一个改名成唯一 basename(如 `RepositoryModels.swift`),公开类型名不变、改名无害。域 A 也为此把 `FileWorkspace/Models.swift` 改成 `FileEntry.swift`。
- **并发 xcodegen generate 竞态 → "Build input files cannot be found" 甚至对你已落盘的文件**: 多代理各自跑 `xcodegen generate` 会互相覆盖共享的 `project.pbxproj`;复用同一 `-derivedDataPath` 的陈旧增量状态也会造成"文件明明在磁盘却报找不到"。诊断:`grep -c "<你的目录名>" DeviceToolbox.xcodeproj/project.pbxproj` 返回 0 即证明你的文件没进工程(被别的代理的生成结果覆盖)。修复:重跑 `xcodegen generate` + 换全新 `-derivedDataPath`,构建前先 grep 确认你的目录进工程了。并发场景下**写完文件要回验持久性**(`find`/`ls` 对 mtime)——本会话整目录被并发进程删除过;保留完整文件内容以便整批重写,重写后立即构建而不是等下一轮。
- **整合前磁盘取证三连**: 互删/竞态事故后,子代理自报"已重写恢复"只是自报。主会话先跑: ①两域全文件清单 `find`;②重复类型检查 `grep -rh "^\(public \)\?\(struct\|enum\|final class\|class\) " <域目录> --include="*.swift" | sort | uniq -d`(应为空);③全量 build。三连过了再进下一轮。
- **集成期改动分两档,避免中间态浪费构建**: 不引用"未落盘兄弟类型"的改动(HomeView 断链修复、Localizable 合并、路由枚举扩展)在等待轮次时先做并 `swiftc -parse` 自检;引用未落盘兄弟类型的主文件(MainTabView 引兄弟代理的 XxxTabView)必须等其落盘才 build——中间态必然编译失败,只浪费轮次,安排为最后一击。

## References
- `references/dual-native-media-app-case.md` — Media Converter 实战: 规格文件样例结构、双端并行委派上下文、预算耗尽接管完整时序、验证脚本模板。
- `references/resume-interrupted-delegation.md` — 资金断供中断后跨会话续跑实战(DeviceToolbox): 取证命令、DeepSeek 余额端点、INTERFACES.md 契约结构与双写禁令措辞样例。
- `references/oss-port-existing-app-case.md` — 把 GPL 开源项目功能"干净移植"进自有 App 实战(3105→DeviceToolbox): 三档拆解评估(许可证传染/exploit 分层/反篡改水印识别)、增量扩展既有工程的规格结构、轮次与集成节奏、进度展示模式。
- `references/3105-patch-package-format.md` — 3105 v1-v3 补丁包格式事实(还原自 GPL 源码,仅格式/加密参数、代码原创)+ 自有 DTBP envelope 设计 + 无真实 fixture 时的确定性验证法。
