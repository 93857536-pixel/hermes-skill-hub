# Agnes AI 双站网关 —— 实测事实表 (2026-09-12)

Hermes 里 `agnes` 是**内置 provider 名**(不在 `providers:` 自定义段里),key 从 `.env` 的
`AGNES_API_KEY` 读;中国站按自定义 provider 方式接(`providers.agnes-cn.key_env: AGNES_CN_API_KEY`)。
参照 `hermes-agent`/supplier 文档容易搞混域名,下面是四组实测矩阵。

## 域名 × key 矩阵(全部用 `GET /v1/models` 实测)

| 域名 | 国际站 key (`AGNES_API_KEY`) | 中国站 key (`AGNES_CN_API_KEY`) |
|---|---|---|
| `https://apihub.agnes-ai.com/v1` (国际站) | **200** — 12 个模型 | — |
| `https://apihub.agnes-ai.cn/v1` | **200** | **401** `Invalid token` |
| `https://api.agnes-ai.cn/v1` (**真正的中国站**) | **401** `无效的令牌` | **200** — 11 个模型 |

结论:
- `apihub.agnes-ai.cn` 只是国际站的国内加速入口,**认国际站 key**;它不是中国站。
- 真正中国站 API 域名 = `api.agnes-ai.cn`,**独立账号体系**(key 不互通)。
- 两站的 key 归属必须分开存:`AGNES_API_KEY`(国际)与 `AGNES_CN_API_KEY`(中国)。
- 别把 `api.agnes-ai.cn` 和 `apihub.agnes-ai.cn` 互相当成同一个站 —— 401 时第一反应是查域名对不对,
  而不是换 key。

## 模型清单(实测 `/v1/models`)

- 国际站(12): `agnes-3.0-flash`, `agnes-2.5-flash`, `agnes-2.5-pro`, `agnes-2.5-pro-alpha`,
  `agnes-2.5-pro-beta`, `agnes-image-2.5-flash`, `agnes-image-2.1-flash`,
  `agnes-image-2.0-flash`, `agnes-video-2.5`, `agnes-video-2.5-flash`, `agnes-video-v2.0`
- 中国站(11): 上述文本模型 + image/video 少一个 `agnes-image-2.0-flash`

> **退役提示（官方公告 2026-09-14）**: `agnes-2.0-flash` 于 2026-09-20 正式下线,
> 过渡期发往 `agnes-2.0-flash` 的流量自动路由到 `agnes-2.5-flash`。新配置/别名请直接用
> `agnes-2.5-flash`(或免费的 `agnes-3.0-flash`),不要再 pin 2.0。

## 能力实测

- **文本**: `POST /v1/chat/completions` 正常(两站 `agnes-3.0-flash` 都返回正常回复)。
- **视觉(base64 图像输入)**: 两站都**支持** —— 发一张纯红 64×64 PNG 的 `data:image/png;base64,…`
  作为 `image_url`,两站都正确回答"红色",`usage.prompt_tokens_details.image_tokens` 有值。
  **旧笔记里"agnes 只收公网图片 URL / supports_vision=False"的结论作废。**
- **图像生成**: 支持,`POST /v1/images/generations`(`{"model":"agnes-image-2.5-flash","prompt":...}`)
  返回 `data[0].url`(COS 域名)+ `task_id`。注意 Hermes 的 `image_gen.provider` 只认
  `plugins/image_gen/<name>/` 里注册的后端(内置:deepinfra, fal, krea, openai, openai-codex,
  openrouter, xai),**没有**通用 OpenAI 兼容后端 —— 想走 agnes 出图需要自己写一个 image_gen 插件。

## 在 Hermes 里的接线(本次落地形态)

```yaml
model:
  provider: agnes            # 国际站为主
  base_url: https://apihub.agnes-ai.com/v1
  default: agnes-3.0-flash
providers:
  agnes-cn:                  # 中国站走自定义 provider(内置列表里没有 agnes-cn)
    base_url: https://api.agnes-ai.cn/v1
    api_mode: openai
    key_env: AGNES_CN_API_KEY
    context_length: 512000
    model: agnes-3.0-flash
fallback_providers:          # 免费优先,付费 deepseek 只压最后
  - {provider: agnes-cn, model: agnes-3.0-flash, base_url: https://api.agnes-ai.cn/v1}
  - {provider: agnes-cn, model: agnes-2.5-flash, base_url: https://api.agnes-ai.cn/v1}
  - {provider: agnes,    model: agnes-2.5-flash, base_url: https://apihub.agnes-ai.com/v1}
  - {provider: agnes,    model: agnes-2.5-pro,   base_url: https://apihub.agnes-ai.com/v1}
  - {provider: deepseek, model: deepseek-v4-flash, base_url: https://api.deepseek.com/v1}
  - {provider: deepseek, model: deepseek-v4-pro,   base_url: https://api.deepseek.com/v1}
```

- 视觉辅助通道: `auxiliary.vision` → provider `agnes-cn`、model `agnes-3.0-flash`、key_env `AGNES_CN_API_KEY`。
- 记忆抽取(hindsight)也指向同一免费端点(`~/.hindsight/profiles/<profile>.env`)。
- 别名: `agnescn` = `agnes-cn/agnes-3.0-flash`,方便 `/model` 会话级切换。
- `fallback_providers` 是列表,`hermes config set` 存不了 → 见 SKILL.md §3 的 ruamel 写法。

## 验证命令(自己复核用)

```bash
K=$(grep '^AGNES_CN_API_KEY=' ~/.hermes/.env | cut -d= -f2-)
env -u HTTPS_PROXY -u HTTP_PROXY curl -sS -m 20 https://api.agnes-ai.cn/v1/models -H "Authorization: Bearer $K" \
  | python3 -c "import json,sys; print([m['id'] for m in json.load(sys.stdin)['data']])"
hermes fallback list      # 复核真实生效顺序
```
