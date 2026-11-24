# Hindsight local_embedded — config & debug (verified)

## Working config.json (`~/.hermes/hindsight/config.json`, chmod 600)
```json
{
  "mode": "local_embedded",
  "llm_provider": "ollama",
  "llm_model": "qwen3:8b",
  "llm_base_url": "http://127.0.0.1:11434",
  "bank_id": "hermes",
  "recall_budget": "mid",
  "recall_prefetch_method": "recall",
  "recall_types": "observation,world,experience",
  "auto_recall": false,
  "auto_retain": false,
  "retain_async": true,
  "retain_every_n_turns": 1,
  "retain_context": "conversation between Hermes Agent and the User",
  "retain_user_prefix": "User",
  "retain_assistant_prefix": "Assistant",
  "memory_mode": "hybrid",
  "idle_timeout": 60
}
```
- Config resolution order: `$HERMES_HOME/hindsight/config.json` → `~/.hindsight/config.json` → env vars.
- LLM key goes in `.env` as `HINDSIGHT_LLM_API_KEY` (not needed for Ollama).
- The plugin also materializes `~/.hindsight/profiles/hermes.env` for the daemon (0600) — the daemon reads `HINDSIGHT_API_LLM_*` from there.
- `recall_prefetch_method: recall` keeps auto-recall LLM-free; `reflect` would need the LLM.

## Manual test harness (no Hermes session needed)
```bash
cd ~/.hermes/hermes-agent
venv/bin/python3 -c "
from plugins.memory.hindsight import HindsightMemoryProvider
p = HindsightMemoryProvider()
p.initialize(session_id='t')
print(p.handle_tool_call('hindsight_retain', {'content': 'test fact'}))
print(p.handle_tool_call('hindsight_recall', {'query': 'test'}))
"
```
Provider API: `initialize / prefetch / queue_prefetch / sync_turn / get_tool_schemas / handle_tool_call / shutdown` — there is NO `.retain()` / `.recall()` attribute.

## Debugging
- Startup log: `~/.hermes/logs/hindsight-embed.log`; runtime log: `~/.hindsight/profiles/<profile>.log`; Postgres data: `~/.pg0/instances/hindsight-embed-hermes`.
- "Config changed, restarting daemon" in the embed log: an edit to config.json mid-run triggers a daemon restart; in-flight ops die with CancelledError / 500. Make config changes between sessions, then retry the op.
- 503 inside retain: model cold-start (prewarm) OR the localhost/IPv6 trap — see macos-local-llm references. On M2, qwen3:8b with a JSON-schema `format` works fine (200) when reached via 127.0.0.1.
- Daemon health: `curl http://127.0.0.1:9177/health`; listener check `lsof -nP -iTCP:9177 -sTCP:LISTEN`.
- Kill a stray daemon+Postgres: `pkill -f hindsight; pkill -f pg0` (frees ~850 MB).
- `is_available()` imports `hindsight`, `hindsight_embed.daemon_embed_manager`, `sentence_transformers` — any ImportError there reports unavailable.

## On-demand mode notes
- With the local LLM fully on-demand (off when unused), `auto_recall: false, auto_retain: false` prevents every turn from silently attempting a dead LLM.
- Recall still works when the daemon is up even with Ollama stopped — read path is pure local vector/graph search; only retain/reflect need the LLM.
- The daemon auto-stops after `idle_timeout` seconds (60 here), so nothing lingers when unused.
