# 中断续跑实战:资金断供后的跨会话接续(DeviceToolbox, 2026-09)

## 场景
两个 v4-pro 子代理(服务层 A + UI 层 B)并行生成 iOS App,因 DeepSeek API 余额耗尽**静默死亡**:
- A 日志最后活动 19:05:29(写完 Models 3 文件后下一次 API 调用失败),B 停在 18:58:52(环境侦察后首次长推理的请求就失败)
- transcript 无任何错误行 —— 资金断供的死亡特征
- 次会话用户问:"那时候我的 api 没钱了,所以他应该没有生成项目吧?" → **猜错**: 磁盘有 7 个 Swift 文件(mtime 19:05)真实落盘

## 取证命令(先于一切动作)
```bash
# 1) 子代理还活着吗(live transcript 尾部 + mtime)
ls -la ~/.hermes/cache/delegation/live/<deleg_id>/          # task-*.log 的 mtime = 最后活动
tail -30 ~/.hermes/cache/delegation/live/<deleg_id>/task-0.log | cut -c1-200
# 判读: "think" 行 → 推理中;think 后成批 write_file → 正在产出;长时间只有 result 无 tool → 疑似死
# 2) 落盘证据(别信猜测)
find <proj> -name '*.swift' | wc -l && ls -la <proj>/Sources/**/
# 3) 进程残留(注意: delegate worker 可能跑在主会话进程内,ps 看不到 —— 以日志静止为准)
ps aux | grep -iE 'hermes|deleg' | grep -v grep
```

## 验证 API 资金(重派前必做,防二次静默死亡)
```bash
KEY=$(grep '^DEEPSEEK_API_KEY=' ~/.hermes/.env | cut -d= -f2)   # key 在 .env 不在 config.yaml
curl -s --noproxy '*' -m 15 https://api.deepseek.com/user/balance -H "Authorization: Bearer $KEY"
# → {"is_available":true,"balance_infos":[{"currency":"CNY","total_balance":"27.53",...}]}
```
注意: 本机 HTTPS_PROXY=127.0.0.1:1082 是死代理,curl 必须 `--noproxy '*'`。
余额充足是"主会话此刻能响应"之外的硬证据(主会话跑 flash 便宜,不代表 pro 的大请求不触发欠费)。

## 续跑配方(主会话编排)
1. 完整读磁盘上规格 + **已生成文件**(类型锚点: 模型字段/枚举 raw value/常量名,续派子代理绝不猜)
2. 主会话写 `docs/INTERFACES.md`(~12KB)作为两并行子代理的共享契约,结构:
   - 环境事实: Swift 版本 / Xcode 路径(`DEVELOPER_DIR` 切换技巧,勿 sudo xcode-select) / xcodegen 路径
   - **文件归属表**: A 写哪些、B 写哪些、谁也别碰谁;目录 mkdir 无害
   - **共享层精确签名**: 每个 Service 类 + 方法签名 + 参数/返回,方法旁注公开 API 来源(防子代理瞎编私有 API 或签名漂移)
   - 数据文件结构 ↔ 已有模型字段逐一对齐(如 compatibility_db.json ↔ CompatibilityItem,status 直接 decode 枚举)
   - project.yml 要点(权限 usage 描述 / developmentLanguage / resources 目录引用)
   - ViewModel 只锁类名,内部自由(UI 与 VM 同一子代理写,自洽即可)
   - **双写禁令措辞样例**: "服务层由并行子代理 A 正在写 Sources/Services/——你只能按契约 §2 签名调用,绝对禁止自己创建或修改该目录任何文件(双写冲突会毁掉并行任务);若 xcodegen/xcodebuild 因 A 文件未落盘而报找不到类,如实记入 build-notes.md,不要自己补写。"
   - 自检/汇报: 无 Xcode 工程的子代理用 `xcrun swiftc -parse <file>` 做语法级自检,如实标注"语法解析通过,未整工程编译"
3. `hermes config set delegation.provider deepseek` + `delegation.model deepseek-v4-pro` → `delegate_task(tasks:[A,B])` → **立即 unset**(三连)
4. 等结果回传 → 主会话重新 `xcodegen generate`(新文件才进工程)+ `xcodebuild` → 修 A/B 衔接的签名机械错

## 关键教训
- 静默中断的子代理日志**没有错误行** —— 判断死因靠"最后活动时间 + 余额端点",不是等报错
- v4-pro 大批写文件前 5-6 分钟静默 = 长推理(18:58:59 → 19:04:37 才出 think),随后成批落盘;静默≠死亡,误判死亡去接管 = 双写冲突(见 SKILL §5)
- 用户直觉("没生成")常错 —— 先摆磁盘证据再决定"重派 vs 续派"(续派 = 保留已落盘文件 + 只补缺口)

---

## 第二批: 续跑执行中又死一个(死亡判定 + 安全重派, 2026-09)

同一任务重派 A/B 后,B(UI 层)19 分钟交付 20+ 文件;**重派的 A 又静默**:
- 19:14 读完锚点文件后 mtime 静止,16-19 分钟 0 文件落盘;同期 sibling B 猛写(19:19-19:30 落盘 20+ 文件)
- 对照判据成立(同系统同 API:sibling 产出 vs A 静止)→ 判 A 真死,不是"长推理";给 3 分钟窗口仍无动静后重派
- 死因事后由批次回传确认: `API call failed after 3 retries: Non-streaming API call timed out after 600s with no response` —— 大请求 600s 无响应,3 次重试全灭,worker 静默退出

### 死亡判定 checklist(第二次不再纠结)
1. `ls -la` 看 live transcript mtime + 尾部时间戳(不是只看内容)
2. **对比 sibling 产出**: 同期并行方写了 20+ 文件而你 0 文件、mtime 静止 >10-15 分钟 → 真死
3. 死因无需现场查 —— 批次回传 note 会带超时信息;现场判断只回答"死没死"

### 安全重派配方(0 落盘 = 无双写风险,直接重派)
- 重派前确认死者 **0 文件落盘**(本次 Services 目录为空)→ 无双写冲突
- 重派 context 加**进度标记条款**: "需要长时间推理时先写进度标记文件(如 `echo working > /tmp/progress-<名>`),无工具输出不超过 5 分钟" —— 把"静默=慢还是死"变成可观测信号
- 重派子代理会自己读**下游已完成代码**(本次新 A 主动 read B 的 HomeView/DeviceView 等)反向核对调用签名 —— 下游已 typecheck 通过 = 上游签名成铁律,偏一个方法名全项目编译失败;鼓励这个动作
- 重派与第一批回传可能交错: 批次 deleg_id 不同,结果各自回传,按 deleg_id 区分,别把旧批次当新状态

### 下游遇只读锚点编译错误 → 修复版 stub 留档(主会话整合时照修)
B 撞到锚点文件(Sources/Models/CompatibilityItem.swift,只读无权改)的 Swift 6 编译错误:
`extension OperatingSystemVersion: @retroactive Comparable` **只实现 `<` 缺 `==`**(Swift 6 语言模式强制完整实现 Comparable)
B 的做法(好模式):
1. `cp` 锚点文件到 `build/stubs/CompatibilityItemFixed.swift`(不碰 Sources)
2. `patch` stub 补 `public static func ==`(三个分量全等比较)
3. 用 stub 替代原文件做自己的 typecheck 验证(exit 0)
4. 汇报/build-notes 写明修法与位置 → 主会话整合时照同一修法 patch 真实文件(一行补丁)
typecheck 自验命令: `SDK=$(xcrun --sdk iphonesimulator --show-sdk-path); xcrun --sdk iphonesimulator swiftc -typecheck -sdk "$SDK" <files>`
小坑: actool 编译 Assets 报错常因输出目录不存在 —— 先 `mkdir -p` 目标目录再跑。
