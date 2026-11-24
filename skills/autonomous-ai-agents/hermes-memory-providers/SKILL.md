---
name: hermes-memory-providers
description: "Use when 配置/扩容/压缩 Hermes 记忆(内置存储 + 外部 provider)。"
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
---

# Hermes Memory Providers

Class: configuring Hermes' external memory providers beyond the always-on built-in MEMORY.md/USER.md. External providers add semantic / knowledge-graph memory via plugins under `plugins/memory/`.

## Provider landscape (checked 2026-08)
- Fully local, zero deps: **holographic** (SQLite + FTS5 + trust scoring + HRR retrieval)
- Local but needs a component: **hindsight** local_embedded (knowledge graph + entity resolution + multi-strategy retrieval; embedded PostgreSQL; an LLM endpoint for fact extraction — Ollama works), **openviking** (openviking-server), **byterover** (brv CLI)
- Cloud / API-key: mem0, honcho, retaindb, supermemory

## Commands
- `hermes memory status` | `setup [provider]` | `off` | `reset`
- `hermes config set memory.provider hindsight`

## Hindsight local_embedded + Ollama (verified end-to-end recipe)
Deps: `uv pip install --python <hermes venv>/bin/python3 hindsight-all` (pulls hindsight_embed + sentence_transformers; their imports must succeed or `is_available()` reports false).
The wizard `hermes memory setup hindsight` is curses-interactive and dies in non-TTY (prints "Cancelled. No changes saved.") — configure manually instead:
1. Write `~/.hermes/hindsight/config.json` (profile-scoped, chmod 600):
   - mode=`local_embedded`, llm_provider=`ollama`, llm_model=`qwen3:8b`,
   - llm_base_url=`http://127.0.0.1:11434` — NEVER `localhost` (IPv6 pitfall, see macos-local-llm)
   - bank_id=hermes, memory_mode=hybrid, idle_timeout=60
2. `hermes config set memory.provider hindsight`
3. Verify: `hermes memory status` → Provider: hindsight, available ✓

## Key behaviors (verified)
- **recall / prefetch(recall) = pure local vector+graph search → works even when the LLM/Ollama is OFF**
- **retain / reflect = LLM fact extraction → fails (500/503) when Ollama is OFF**
- For on-demand local models: set `auto_recall: false, auto_retain: false` so every turn doesn't silently fail; stored memories stay queryable whenever the daemon is up
- Daemon auto-stops after `idle_timeout`; daemon + embedded Postgres ≈ 850 MB resident while up
- Tools in hybrid mode: `hindsight_retain` / `hindsight_recall` / `hindsight_reflect`
- Logs: `~/.hermes/logs/hindsight-embed.log` (startup), `~/.hindsight/profiles/<profile>.log` (runtime); Postgres data under `~/.pg0/instances/hindsight-embed-hermes`

## Where the daemon actually reads its LLM config (verified 2026-09-12)
Runtime source of truth is `~/.hindsight/profiles/<profile>.env` (e.g. `hermes.env`), keys `HINDSIGHT_API_LLM_PROVIDER / LLM_API_KEY / LLM_MODEL / LLM_BASE_URL`. `~/.hermes/hindsight/config.json` is only the plugin-side config (mode/bank/recall/idle) that the plugin materializes into that env file — editing ONLY config.json may not take effect for the running/next daemon, so change BOTH when swapping the extraction LLM. To stop paying for a cloud model, point it at any OpenAI-compatible free endpoint (here: provider `openai`, base_url `https://api.agnes-ai.cn/v1`, model `agnes-3.0-flash`).

## Symptom: `Failed to start daemon for profile '<profile>'` (2026-09-12)
`hindsight_retain` / `hindsight_recall` fail with that message. `~/.hindsight/profiles/<profile>.log` shows `Database migration failed`, caused by `psycopg2.OperationalError: connection to server at "127.0.0.1", port 5432 failed: Connection refused` — the embedded PostgreSQL simply was not running (nothing listening on 5432, no `postmaster.pid` in the instance dir). Fix: start the bundled PG directly with its own `pg_ctl`; it comes up clean:

```bash
PG=$HOME/.pg0/installation/*/bin          # e.g. ~/.pg0/installation/18.1.0/bin
$PG/pg_ctl -D ~/.pg0/instances/hindsight-embed-hermes/data -l /tmp/pg_hindsight.log start
lsof -nP -iTCP:5432                       # verify: postgres LISTEN on 5432
```

Start PG before the daemon needs it, then retry the retain. Honest status: in the 2026-09-12 session PG did start successfully, but daemon recovery was not re-verified end-to-end — treat "PG is up" as necessary-not-sufficient and confirm with a real `hindsight_retain` (its failure message routes to `~/.hindsight/profiles/<profile>.log`, always read the tail there).

## References
- references/hindsight-local-embedded.md — working config.json, manual test harness, debug path, daemon lifecycle
