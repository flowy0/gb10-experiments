## Core Services

| File/Dir | Purpose |
|---|---|
| `llama-swap/` | Model router config (`config.yaml`) and swap definitions |
| `llama-swap/docs/MEMORY.md` | Memory planning docs with architecture tables |
| `docs/VLLM.md` | vLLM setup, benchmarking, and debugging history |
| `librechat/` | LibreChat UI config (`librechat.yml`, `data/auth.json`) |
| `open-webui/` | Open WebUI cache data |
| `docker-compose.yml` | Main compose file — launches llama-swap, LibreChat, Open WebUI, MongoDB |
| `models/` | All downloaded GGUF model files (see `llama-swap/config.yaml` for available models) |

## Supporting

| File/Dir | Purpose |
|---|---|
| `docker/` | Dockerfiles and build context |
| `.env` | Environment secrets (Mongo URI, JWT keys, API keys) |
| `secrets/` | Additional secret files |
| `archive/` | Deprecated configs (vLLM, older compose files) |
| `backups/` | Config backups |
| `data/` | Runtime data |
| `logs/` | Log files |
| `bench/` | Long-context benchmark tasks and prompts |
| `tests/` | Test scripts |
| `searxng/` | SearXNG search engine config for RAG |
| `memory-api/` | Memory/embedding API service |
| `litellm/` | LiteLLM router config (disabled) |
| `hf-cache/` | Hugging Face model cache |
| `workspace/` | Working directory |
| `inbox/` | Incoming files |
| `mode` | Mode switching script |

## Known Issues

### LibreChat — Gemma4 Tool-Calling (Stopped)

LibreChat has been **stopped** due to unresolved Gemma4 tool-calling issues.
The model generates valid tool calls per its own template, but LibreChat's validation schema fails to parse them.

```
[ON_TOOL_EXECUTE] Tool web_search error: Received tool input did not match expected schema
```

**Status:** LibreChat service is stopped. Use Open WebUI (port 3000) instead.
LibreChat config is preserved for future reference.

### Open WebUI — Browser Cache After Upgrade

After upgrading Open WebUI to v0.10.2, the UI may flash or appear broken.
This is a **browser cache issue** — old JavaScript files from the previous version are cached.

**Fix:** Hard refresh (`Ctrl+Shift+R` / `Cmd+Shift+R`) or clear browser cache for the site.

### OOM When Loading Multiple llama.cpp Models

Loading 3+ llama.cpp models alongside vLLM hermes (~52 GB reserved) risks OOM.
vLLM reserves 40% of GPU memory. Only ~79 GB remains for llama-swap models.

**Fix:** Load only 1-2 llama.cpp models at a time. They load on demand (~5-30s cold start).
If a crash occurs:
```bash
docker ps --filter name=ls- --format '{{.Names}}' | xargs docker rm -f
```

### llama.cpp SHA Digest — Reference

llama.cpp image SHAs are pinned in `config.yaml` using `@sha256:` format.
When updating, use the manifest digest from `docker image inspect`, not the
Docker image ID.

---

See [docs/HISTORICAL.md](docs/HISTORICAL.md) for previous stack configurations.

## Current Active Setup — vLLM Hermes + llama-swap

| Service | Role | Port |
|---|---|---|
| **vLLM** | Hermes (Qwen3.6-35B-A3B NVFP4, 256k, DFlash) | 8000 |
| **llama-swap** | Code, Research, Subagent, Embed, Test | 8088 |
| **LiteLLM** | Unified router for all models | 4000 |
| **Open WebUI** | Chat UI | 3000 |
| **MongoDB** | LibreChat data store (inactive) | 27017 |

See `llama-swap/docs/MEMORY.md` for full model details, memory calculations, and DFlash benchmarks.

### Quick Start

```bash
docker compose up -d llama-swap litellm open-webui
# vLLM starts separately (needs GPU memory reservation):
docker compose up -d vllm-qwen36-35b-a3b-nvfp4
```

## Quick Reference

- **LiteLLM API (recommended):** `http://localhost:4000/v1`
- **llama-swap API (direct):** `http://localhost:8088/v1`
- **vLLM API (hermes only):** `http://localhost:8000/v1`
- **Open WebUI:** `http://localhost:3000`
- **LibreChat (stopped):** `http://localhost:3080`

## Model Groups

Models are organized by group in `llama-swap/config.yaml`. See `llama-swap/docs/MEMORY.md` for memory planning and DFlash benchmarks.
