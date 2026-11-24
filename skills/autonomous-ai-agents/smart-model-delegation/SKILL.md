---
name: smart-model-delegation
description: "委派/后台任务自动选最优模型。Use when delegating or spawning agents."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [delegation, model-selection, subagent, multi-agent, hermes]
---

# 智能模型委派 (smart-model-delegation)

**用途**: 代替硬编码的 `delegation.provider/model` 单模型配置。每次委派子代理或启动后台任务前，按任务特征从用户模型池自动挑选最优模型，再走对应执行路径。

**触发时机**: 任何需要 delegate_task、spawn `hermes chat` 独立进程、或评估"这个任务该用什么模型跑"的场景。

**执行前方案简报(强制,每次指令)**: 收到用户指令后、执行前,先简短说明执行方案：
1. **用什么模型**（主会话模型、子代理模型、辅助/视觉模型,数量+名称）
2. **用不用子代理**（不用则说明直接主模型执行;用则说明几个、哪几个模型）
3. **为什么选它**（每个模型一行理由,来自决策规则）

示例：
> 📋 执行方案：
> - 主模型: deepseek-v4-flash(继承) — 负责检索与汇总;选它:搜索/整理类任务,快且成本低
> - 子代理: 不用 — 任务可单模型完成,无需并行
> - 执行: 先 web_search 多角度查询,再核对命中页面

## 1. 用户模型池 (2026-08-09 盘点)

| 模型 | provider 名 | 速度 | 能力 | 成本 | 最佳用途 |
|---|---|---|---|---|---|
| agnes-3.0-flash | agnes | 快 (~6s 起, 252 tok/s) | 强, Agent/工具调用优化, 512K 上下文 | **免费** | **默认**：几乎所有任务的第一选择 |
| agnes-2.5-flash | agnes | 快 | 通用, 支持工具调用 | **免费** | 免费备选（也做 MoA 参考模型） |
| agnes-3.0-flash | agnes-cn | 快 | 同上, 国内直连 `api.agnes-ai.cn` | **免费** | 国际站慢/不通时的首选兜底（现为 fallback 第 1 条） |
| agnes-2.5-flash | agnes-cn | 快 | 通用 | **免费** | 中国站轻量兜底 |
| agnes-2.5-pro | agnes | 中 | 推理更强 (AA Intelligence 39) | 付费 (¥3/M in, ¥6/M out) | 只有在必须时; 付费, 少用 |
| agnes-2.5-pro-beta | agnes | 中 | 打榜版 | 付费 (¥0.7/¥2.1) | 同上, 少用 |
| deepseek-v4-flash | deepseek | 快 | 通用 | 便宜 | **免费额度不够/agnes 失败时的第一付费兜底** |
| deepseek-v4-pro | deepseek | 中 | 推理强(reasoning_content) | 较贵 | 复杂难的推理/架构/代码, 免费模型顶不住时才用 |
| glm-5.2 | zai | 快 | 通用强 | - | z.ai 首选：通用/中文 |
| glm-5.1 | zai | 快 | 通用强 | - | 通用/中文 |
| glm-5 | zai | 中 | 通用 | - | 通用 |
| glm-5v-turbo | zai | 快 | 视觉类 | - | 注意：z.ai 主接口视觉输入报 1210，看图仍走 vision_analyze |
| glm-5-turbo | zai | 快 | 通用 | - | 快速替代 |
| glm-4.7 | zai | 中 | 通用 | - | 通用 |
| glm-4.5 | zai | 中 | 通用 | - | 通用 |
| glm-4.5-flash | zai | 快 | 轻量 | - | 快速/便宜 |
| glm-4.5v | zai (仅 auxiliary 视觉通道) | 中 | 视觉 | - | 图片/截图理解(经 vision_analyze)，不能当主模型 |
| qwen3:4b | qwen4b (本地 Ollama) | 慢 (~2.5min/简单任务) | 中等 | 免费 | 隐私敏感、离线、免费跑批 |
| qwen3:1.7b | qwen17 (本地 Ollama) | 快 (~1.7min) | 弱 | 免费 | 极简任务、隐私、无 API 额度时 |

## 2. 决策规则 (按优先级从上到下匹配)

**总原则（2026-09-12 起）：默认全部走免费的 agnes；只有免费模型顶不住时才升到付费 deepseek。**

1. **任务需要看图** → 用 `vision_analyze` 工具（auxiliary 通道 zai/glm-4v-flash），不要把图片喂给 agnes 主接口（只收公网图片 URL，不收 base64）
2. **隐私敏感 / 必须离线 / 完全不想出网** → 本地 qwen3:4b（极简任务可 qwen3:1.7b）
3. **默认一切任务** → agnes-3.0-flash（免费，512K 上下文，Agent/工具调用优化）
4. **复杂任务**（多步推理、架构/设计、代码生成与 review、长文分析）→ 先试 agnes-3.0-flash；实测顶不住（反复出错/无法完成）才切 deepseek-v4-pro（付费，需向用户说明）
5. **需要不同视角做 MoA** → 免费组合：参考 qwen3:4b + agnes-2.5-flash，聚合 agnes-3.0-flash（config 里的 preset "team"）
6. **当前 /model 恰好合适** → 路径 A（零开销继承父模型）

## 3. 执行路径 (三选一)

### A. 继承父模型（默认，零开销）
**默认行为**：delegation 未配置 provider/model 时（当前就是此状态），子代理自动继承父会话模型（`/model` 显示的那个）。直接 `delegate_task(goal, context)` 即可，什么都不配置。

### B. 全局临时切换 delegation（需要并行/回传 + 指定模型）
delegate_task 工具本身**没有 per-task 模型参数**，只能通过全局配置注入。流程（必须成对执行）：

```bash
# 1. 记录当前值（默认状态应为无 provider/model 两键）
grep -A4 '^delegation:' ~/.hermes/config.yaml
# 2. 切换
hermes config set delegation.provider deepseek
hermes config set delegation.model deepseek-v4-flash
# 3. delegate_task(...)  ← 此时子代理用新模型
# 4. 完成后立即恢复默认（必须！否则污染后续所有子代理）
hermes config unset delegation.provider
hermes config unset delegation.model
```

### C. spawn 独立进程（任意模型、后台长任务、fire-and-forget）
每次可指定任意模型，不影响主会话和 delegation 配置：

```bash
# 前台单次
hermes chat -q "任务描述" --provider deepseek -m deepseek-v4-pro -t terminal,file
# 后台长任务（推荐）
hermes chat -q "任务描述" --provider qwen4b -m qwen3:4b --background # 或 terminal(background=true, notify_on_complete=true)
```

## 4. 坑位 (pitfalls)

- **agnes 有国际站/中国站两个网关，key 不通用**：国际站 `https://apihub.agnes-ai.com/v1`（用户 key 在这里），中国站 `https://api.agnes-ai.cn/v1`（把国际站 key 发过去会 401 "无效的令牌"）。改 key 前先确认是哪一站，别被文档里的 api.agnes-ai.cn 带偏。
- **agnes 只接受公网图片 URL**：不支持 base64 图片输入，所以 `supports_vision=False`，看图统一走 auxiliary.vision（zai/glm-4v-flash，免费）。
- **delegate_task 无 per-task 模型参数**：schema 只有 goal/context/tasks/role/output_schema/background；子代理模型 = delegation 配置或父会话继承，二选一
- **路径 B 必须恢复**：忘记恢复会污染后续所有子代理（全部跑错模型）；并发/中断场景优先考虑路径 C
- **模型名带冒号**（`qwen3:4b`）：写进 yaml 会被拆成嵌套结构，必须用 `hermes config set` 而不是手改 yaml
- **本地模型慢**：qwen3:4b 简单任务约 2.5 分钟，长任务用 background + notify_on_complete，别用前台 timeout 死等
- **deepseek-r1 无 function calling**：不能用于任何需要工具调用的子代理
- **换 provider 自动带 base_url/mode**：deepseek → chat_completions；自定义 provider 按 config.yaml 的 providers.* 定义走，无需手动指定 base_url

## 5. 验证

- **delegation 结果验证**：委托完成后检查结果里的 `Model: xxx` 字段，确认等于预期模型
- **spawn 验证**：查 live transcript / 日志开头的模型行，或让任务自报 `--provider` 生效情况
- **配置恢复验证**：路径 B 结束后 `grep -A4 '^delegation:' ~/.hermes/config.yaml` 确认 provider/model 两键已 unset（恢复默认继承状态）

## 6. 模型池更新

新增/更换模型后同步更新第 1 节表格；provider 名以 `config.yaml` 的 `providers.*` 和内置 provider 为准（`/model` 命令可看全部可用项）。
