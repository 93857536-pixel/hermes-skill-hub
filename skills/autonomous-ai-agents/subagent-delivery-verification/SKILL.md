---
name: subagent-delivery-verification
description: "Verify subagent output via canonical checks, not summaries."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [delegation, subagent, verification, orchestration, codegen]
---

# 子代理交付复验 (subagent-delivery-verification)

**核心原则**: 子代理的最终汇报是**自述**,不是事实。`status=completed` 只代表对话结束,不代表工作完整。凡是子代理产出了可构建/可运行/可检查的工件,主代理必须亲自用规范命令复验后才能向用户交付。

触发: 任何 `delegate_task`(尤其是批量/并行)回传后、向用户报告"完成"之前。

## 为什么必须复验(实战案例 2026-08)

双平台应用并行开发,两个 v4-pro 子代理分别写 macOS/Windows 端。macOS 子代理返回 `status=completed`,但实际是**迭代预算耗尽被截断**:
- live transcript 尾部:`final | end status=completed exit_reason=max_iterations (iteration budget exhausted)`
- build-notes.md 是**空的**(没来得及写)
- 最后一次测试运行是**红色**(还有失败用例)
- 最终 summary 被**截断在工具调用中间**
- 代码停在"刚 patch 未复验"状态:3 个文件 4 处编译错误(可选数组未解包 ×2、`String?` label ×2)

主代理接手后:修复 4 处一行级编译错误 → BUILD SUCCEEDED → 19/19 测试通过 → 冒烟测试通过。**若直接信了子代理的 completed,交付的就是坏代码。**

## 复验清单(按工件类型)

1. **看 transcript 尾部**: `tail <live_transcript>` 找 `exit_reason`。`max_iterations` = 停在中间状态,必须重点复验。批量回传的 summary 可能截断在工具调用中间——看完整日志,不看摘要。
2. **代码工件**: 重跑规范命令——`xcodebuild build` / `xcodebuild test` / `dotnet build` / `pytest` 等,拿**真实输出**(BUILD SUCCEEDED、N/N tests passed),不是子代理的复述。grep 时注意 BSD grep 不支持 lookahead(`(?!...)` 报 repetition-operator operand invalid)。
3. **产物结构**(不只看源码): bundle/目录布局、Info.plist 关键键(PlistBuddy)、图标资源、`codesign -dv`、冒烟命令的真实退出码与 JSON 输出。
4. **外部副作用**(上传/推送/远端写入): 用可验证句柄反查——`git ls-remote`、`gh repo view`、HTTP GET 回读。子代理说"已推送"不算数。
5. **无工具链的平台**(如 macOS 上开发 Windows 端): 接受静态审查但要**明说**"未编译,交付标准为静态审查通过",绝不冒充编译过。
6. **summary 丢了 ≠ 工作丢了(2026-10-23 实测量级教训)**: 子代理 final summary 撞上 `API call failed / max_iterations` 被掐断时,**先别重派**——它可能已经把真正的交付物写进了仓库或 /tmp 的文件,只是回传摘要那一步挂了。处置:
   - 在 task-N.log 里 grep 子代理自己写下的最终 JSON/报告标记(本例 macOS 审计子代理把完整 8-bug 报告写进了**仓库根目录的 `audit_report.json`** 并读回验证过,只是最后生成回传摘要的 LLM 调用 402 失败)。
   - `grep -n 'audit_report\|"bugs"\|severity' task-N.log` 定位它写了哪个文件、在哪一行读回过;直接 `read_file` 那个磁盘文件拿完整结论,零重跑成本。
   - 通用法: prompt 里若要求子代理「最后写一份报告」,给它一个**固定落盘路径**(如 `<repo>/audit_report.json`),这样即使 summary 传输挂掉,主会话也能从磁盘兜底取回。写 report 的文件残留要记得在收尾时清掉(本例 `rm -f audit_report.json`)。
   - 只有磁盘也找不到交付物、且日志显示任务确未做完时,才重派;重派 prompt 里带上「已知已修项」要子代理去重。

## 自写文件同样要复验:超长工具参数会截断成字面量落盘

复验不只针对子代理——**你自己的 `patch` / `write_file` / `execute_code` 也是不可信的自述**。
这三个工具的参数都是单次流式传输,payload 过大时会在中途被截断,而截断标记会作为**字面文本写进文件**:

```tsx
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, margi...[truncated]
```

这行既不是注释也不是占位符,是坏代码。实测(2026-11,CraftCraft):给实例卡片加版本下拉时
`patch` 的 `new_string` 被截断,`InstancesPage.tsx` 第 204 行落成上面的字面量;同一会话里
`write_file` 写 release notes 落成 ``| `wizard.selectVersion`...[truncated]``,
`execute_code` 落成 `d["versi...[truncated]`(直接 SyntaxError)。

- **检测**:每次大 payload 写入后立刻 `grep -rn '\[truncated\]' src/ src-tauri/src/`(期望无输出),
  再跑规范命令。tsc/build 能抓住 .ts/.tsx 这类损坏;`.md` / 配置文件没有编译器,只能靠 grep。
- **预防**:payload 超过约 1–2KB 就拆成多次小 patch;需要写大段内容(翻译表、长文档、批量代码)时,
  把数据放进脚本的数据结构或分块的 `/tmp/*.md`,由脚本落盘——工具参数里就不携带大块文本。
- **修复**:只对坏掉的那一行做一次定向 patch,不要重跑整批、不要重写整个文件。

## 证据记录器只认裸跑的规范命令

验证证据要**在项目根目录裸跑**规范命令(`npm run build`、`tsc --noEmit`)才会被记录。
接管道(`npm run build | python3 -c …`)或由外层包装命令间接执行时,命令确实跑了、输出也确实
是绿的,但不进证据库——于是后续每轮都提示"验证已过期",看着像有未提交改动,实际没有。

- 闭合提示:在 repo 根裸跑一次 `npm run build`,让输出直接可见。
- 需要解析输出时:先裸跑拿证据,再另跑一条带管道的命令做解析,不要合并成一条。

## 规格文件驱动的并行代码生成(配合使用的模式)

大代码量任务(整 app、多平台)用这个变体,已在双平台媒体转换 App 验证:

1. 每个工作流写一份详细规格文件入仓库(`scripts/spec-<stream>.md`):目录树、逐文件职责、构建/测试命令、硬约束("零第三方依赖"、"SWIFT_VERSION 5.9"、"禁止动 Assets/")、修复迭代上限(≤6)。
   - 规格 >~8KB 时,让子代理**读文件**而不是把全文塞进 context(这是"不要把计划文件丢给子代理"规则的正当例外)。
2. 按 smart-model-delegation 决策表 pin 委派模型,`delegate_task(tasks=[...])` 一次批量并行派发,完成后立即 unset。
3. 本机有工具链的工作流,要求子代理自己构建+修错,错误原文写进 build-notes.md。
4. 回传后走本技能复验清单;残留的少量一行级编译错误直接在主会话修(比再派一轮子代理便宜,见 subagent-driven-development 的例外条款)。

## 迟到的回传不是新任务:先比对现状,别重跑

批量委派的完成通知可能晚到十几分钟甚至跨轮次,而它描述的工作**早已合入并发布**。同一会话里
三次迟到通知(`deleg_a2f2478c` / `deleg_083d8475` 等)每次都需要同一套判断,而不是直接照单重做。

判别顺序:

1. **看时间线而非看内容**。通知里带 `Dispatched: <时刻> (Nm ago)`;把它和 `git log --format='%ci %h %s'`
   的提交时刻对齐。若子代理产出时刻 **早于** 你自己的提交时刻,工作已被收录。
2. **用 git 反查文件是否已在发布点**:`git ls-tree -r --name-only v<tag> | grep <path>` —
   这比 `grep` 工作区更硬,因为工作区可能已被后续改动覆盖。
3. **查口径差异而不是文件有无**。真正会漏的往往是"数量对不上":子代理按当时的基准(如 81 键)交付,
   之后基准涨到 93 键。`grep -cE "^\s*'" f.ts` 全目录扫一遍,比读回传摘要有用。
4. 只有"磁盘/发布点确实没有该产物"时才重派——重派时带上"已知已做项"让子代理去重。

结论模板:先给"已包含在 <tag> 里"的硬证据(commit/tag/文件),再补"但我顺手发现 <真实缺口>",
不要用"收到,已重做一遍"把已发布的工作再做一次。

## 坑

- `xcodegen` 项目: 子代理新增文件后可能忘记重跑 `xcodegen generate`,构建报 "cannot find 'X' in scope" 而文件明明在盘上——复验时先重跑 generate 再 build。
- Xcode 27 Debug 构建: 主二进制是 Previews stub,真实代码在 `*.debug.dylib`;验证字符串/冒烟标记要对 dylib 做,别对主二进制做(会假阴性)。
- 复验发现的问题要写进子代理留下的 build-notes.md(空的就补上),让交付记录完整可追溯。
