# Hermes Skill Hub

A shared, public collection of practical AI-agent skills for [Hermes Agent](https://hermes-agent.nousresearch.com) (and compatible skill formats like OpenClaw). These are battle-tested procedures distilled from real workflows — macOS/iOS development, devops, GitHub, creative tools, finance workbooks, MLOps, and more.

中文：一批经过实战验证、可直接复用的 Hermes Agent 技能（skill）合集，供更多人使用。

## What's inside

Skills are organized by category. Each skill folder contains a `SKILL.md` (YAML frontmatter + instructions) and optional `references/`, `templates/`, `scripts/`.

| Category | Skills | Highlights |
|---|---|---|
| `apple/` | 10 | macOS app build & packaging, app icons, SwiftPM menubar apps, sleep-keeper, Xcode/devicectl pitfalls, CoreText PDF |
| `devops/` | 14 | Cloudflare Tunnel ops, Tauri cross-platform CI, Docker, GitHub Actions SSH deploy, headless SPA screenshots, watchers (RSS/poll) |
| `github/` | 7 | PR workflow, code review, release publishing with artifact verification, open-source publishing checklist (privacy scan included) |
| `software-development/` | 20 | systematic debugging, subagent-driven development, TDD-adjacent review, Swift ZIP codec, Whisper local ASR, WinUI/.NET |
| `creative/` | 14 | hand-drawn diagrams, pixel art, memes, popular web design systems, video pipelines, tldraw |
| `mlops/` | 31 | training (LoRA/QLoRA/TRL/axolotl), inference (TensorRT, vLLM-adjacent), structured output, RAG (chroma/qdrant/pinecone) |
| `research/` | 12 | domain recon, OSINT, web scraping, literature search, prompt evolution |
| `finance/` | 9 | 3-statement / DCF / LBO / comps / merger models, Excel authoring, stocks |
| `media/` | 4 | B站 video download, QR machine reading, TTS voiceover, footage sourcing |
| `security/` | 7 | suspicious URL triage, web pentest (authorized), 1Password, sherlock |
| `blockchain/` | 3 | EVM wallets & gas, Hyperliquid, Solana read-only |
| `payments/` | 3 | MPP HTTP-402 agent payments, Stripe Link |
| `productivity/` | 7 | flashcards, shopify, telephony, canvas |
| `autonomous-ai-agents/` | 12 | delegation & subagent verification, model selection, hermes ops patterns |
| others | ~15 | sqlite, tauri, wpf, web crypto (E2EE), mcporter/fastmcp, gaming (modded MC servers) |

Total: **180+ skills, 800+ files**.

## Install

Option A — clone and install everything:

```bash
git clone https://github.com/93857536-pixel/hermes-skill-hub.git
cd hermes-skill-hub
./install.sh            # copies skills/ into ~/.hermes/skills/
```

Option B — pick a single skill:

```bash
# Hermes:
cp -r skills/devops/cloudflare-tunnel-ops ~/.hermes/skills/devops/
# OpenClaw:
cp -r skills/devops/cloudflare-tunnel-ops ~/.openclaw/workspace/skills/devops/
```

Option C — download the release tarball (no git needed): see Releases.

After installing, restart Hermes (or start a new session) and the skills appear in the agent's available-skills index automatically.

## Safety notes

- All personal credentials, server IPs, API keys, and proprietary project details were scrubbed from these copies before publishing. Skills are *procedures*, not secrets — they tell the agent what to do; you still supply your own keys/config.
- Skills marked for paid or vendor services (Alipay, Stripe, 1Password, etc.) require your own accounts/SDKs.
- Some skills are macOS-centric; devops/github/creative ones work cross-platform.

## Contribute

Fork, add or patch skills under `skills/<category>/<name>/` following the `SKILL.md` format (YAML frontmatter with name/description, then trigger conditions, numbered steps, pitfalls), open a PR. A maintainer will run the privacy scan before merging.

## License

MIT for this collection's curation and scripts. Individual skills may carry their own attribution notes in `NOTICE.md`.
