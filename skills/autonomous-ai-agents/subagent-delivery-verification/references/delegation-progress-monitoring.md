# 委派等待期的进度监控 & 「假成功」批次识别

实测于 2026-10-22 WeChatExporter 三端审计批次(`deleg_2b4aaa99` / `deleg_a944e561`)。

## 1. 怎么看一个正在跑的 delegation

`delegate_task` 的结果会自动回传,但用户在等的时候**不能静默干等**——用户明确期望「等待子代理时主会话周期性展示实时进度（正在做什么/日志尾）」。

```bash
D=~/.hermes/cache/delegation/live/<DELEG_ID>

# 状态机 + 体量(增长 = 还在干活;status: running|completed)
python3 -c "import json,os,sys;d=json.load(open('$D/manifest.json'));[print(f\"task-{i}: {t['status']}, log_size={os.path.getsize(t['log'])}\") for i,t in enumerate(d['tasks'])]"

# 正在做什么:日志尾部就是 tool 调用流水 -> read_file(X.swift) / terminal(git log ...)
tail -3 $D/task-0.log

# 完成后的完整 summary(批次摘要被截断时必读这个文件)
ls -t ~/.hermes/cache/delegation/subagent-summary-*.txt | head -1
```

判读要点:
- 同一 task 的 `log_size` **连续多轮不变** = 没有新 tool 调用,通常是在生成最终 JSON(正常),不是挂死。真挂了先看 `status` 再决定重派。
- `manifest.json` 的 `status` 只在对话结束时翻成 `completed`;想更早判断质量看日志尾部有没有 `final | status=completed ... exit_reason=...`。
- 播报格式:「task-0 已读到 ImageExporter,日志尾 `read_file(...)`;还剩 2 running」——不要只写「等待中」。

## 2. ⚠️ process 工具监控不了 delegation

`process(action='poll', session_id='deleg_xxx')` 必报 `not_found`:delegation 批次 ID 不是 terminal 后台进程 ID,process 工具只认 `proc_xxx`。同一参数反复重试还会触发 loop warning。要监控走上面的 `live/<DELEG_ID>/` 目录。

## 3. ⚠️ 「✓ TASK n/N (status=completed)」可能是假成功

批次汇报里每条都带 `✓ TASK n/N ... (status=completed, api_calls=..)`，但这只表示**对话结束**，正文可能是:

```
Billing or credits exhausted: HTTP 402: Insufficient Balance (request_id: ...)
```

即 provider 计费/鉴权失败,该子代理**零产出**(通常 `api_calls` 很小,如 7~13 次就「完成」)。

- **可能部分失败**:同一批里先跑够的任务正常出结果,后启动的被掐掉——实测 3 任务中 Linux 正常、macOS/Windows 双双 402。**必须逐条看正文,不能看批次整体。**
- **处置**:这是配置问题不是任务问题。`hermes config unset delegation.provider delegation.model` 回到继承父模型(免费)后重派;同 provider 换便宜的型号无效(402 是账户级)。
- 重派前先把「已知台账/已修项」写进 prompt 要求去重,否则新批次会把旧问题再报一遍。

## 4. 子代理 summary 被截断时

批次摘要会被压到 `head + tail`(中间省略)。完整版在 `~/.hermes/cache/delegation/subagent-summary-<n>-<ts>.txt`,`read_file` 带 offset 翻。若某条 summary 文件缺失,改读 `live/<ID>/task-N.log` 的 `final | ... summary:` 行——信息都在,不必重派。
