---
name: skill-library-maintenance
description: "盘点/去重/清理 Hermes 技能库。Use when checking for duplicate skills."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [skills, dedup, cleanup, maintenance, curator]
---

# 技能库维护 (skill-library-maintenance)

**用途**: 盘点已安装技能、检测重复组、合并/清理冗余技能。2026-08 实战验证(205 个技能中发现 4 个重复的 Ollama 集成技能 + 2 个重复的安装类技能,全部合并清理)。

**触发时机**: 用户问"有什么重复的 skill 吗"、"清理一下技能"、"技能太多了"。

## 1. 盘点

```bash
cd ~/.hermes/skills && find . -name "SKILL.md" | while read f; do
  dir=$(dirname "$f"); name=$(basename "$dir")
  desc=$(grep -m1 "^description:" "$f" | cut -c1-80)
  echo "$name | $desc"
done | sort
# 总数
find . -name "SKILL.md" | wc -l
```

## 2. 去重检测(按功能域分组)

按 description 的关键词/功能域聚类,找出高度重叠的技能。真实案例:
- **Ollama/本地 LLM 接入 Hermes ×4**: `hermes-local-llm-integration`、`hermes-local-model-integration`、`hermes-ollama-integration`、`ollama-hermes-integration`(后者作者是 curator——多会话/curator 会重复造技能)
- **zip/URL 技能安装 ×2**: `third-party-skill-install`、`vendor-skill-install`

判断标准: description 语义相同 + 触发场景相同 = 重复。不同引擎/不同产品(如 duckduckgo-search vs searxng-search、codex vs claude-code)不算重复。

## 3. 处理(保留主版本,合并其余)

- **保留**: 记忆引用的版本 / 内容最全的版本 / 用户惯用的版本
- **删除**: `skill_manage(action='delete', name=..., absorbed_into='<主版本名>')`
- 删除前先 cat 对比各版本内容,确认主版本包含关键信息
- `absorbed_into` 必须填主版本名(已存在),不能为空字符串除非纯清理
- 删除后验证: `find . -name "SKILL.md" -path "*<name>*"` 确认消失

## 4. 异常技能检测(重要)

盘点时注意**非本会话创建但时间戳在本会话进行中**的技能:
```bash
find ~/.hermes/skills -name "SKILL.md" -newer ~/.hermes/SOUL.md -exec ls -la {} \;
```
- 可能是并行进程/另一会话/用户在别的窗口创建的
- 内容质量高但来源不明 → 先向用户报告,由用户决定保留或删除
- 删除前必须用户确认(不可逆)

## 5. 坑位

- **Protected 技能不可动**: bundled(hermes-agent)、hub 安装(quarkclouddrive)、pinned、用户所有技能——后台 curator 编辑会被拒。只能处理 `created_by: agent` 的(curator-managed)
- **创建新技能前先查重**: `skills_list` 或 grep description,避免再造第四个 ollama 技能
- **社区技能安装先审查**: `hermes skills inspect <id>` 预览(重点看有没有 scripts/install.sh、有没有恶意内容);确认安全后 `hermes skills install <id> -y`(非交互必须 -y,否则自动取消)
- **delegate/curator 会重复造技能**: 发现 curator 创建的同类技能时,用 absorbed_into 合并到用户惯用版本

## 6. 验证

- 删除后: `find . -name "SKILL.md" | wc -l` 数量减少,且 `hermes skills list` 正常
- 被合并技能的用户记忆引用(如"详见技能 X")必须指向保留的主版本
