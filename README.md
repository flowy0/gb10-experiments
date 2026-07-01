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

### Gemma 4 — LibreChat Agent / Tool-Calling

Gemma 4 models (`12b`, `26b`) support tool calling in their chat template (`supports_tool_calls: true`)
but LibreChat's agent system may reject tool calls with:

```
[ON_TOOL_EXECUTE] Tool web_search error: Received tool input did not match expected schema
```

**Root cause:** Gemma 4 formats tool calls differently than what LibreChat's tool schemas expect.
The model generates valid tool calls per its own template, but LibreChat's validation
fails to parse them.

**Status:** Unresolved. Use the Qwen3.6 27B through the `code` group for agentic workflows
that require web search and tool execution.

### LibreChat — RAG API Warning

```
RAG API is either not running or not reachable at undefined
```

LibreChat's RAG API is not deployed. File upload features may have issues.
This does not affect chat or agent tool execution.

### MTP + TurboQuant Incompatible (llama-cpp-turboquant fork)

MTP speculative decoding and TurboQuant KV cache cannot be used together on the same
model. The MTP context fails to initialize with turbo4 cache types.

**Resolution:** Models use either MTP (Qwen 27B, 35B for speed) or TurboQuant (12B QAT,
E4B for memory), not both on the same model.

### llama.cpp SHA Digest — Reference

llama.cpp image SHAs are pinned in `config.yaml` using `@sha256:` format.
When updating, use the manifest digest from `docker image inspect`, not the
Docker image ID.

---


See [docs/HISTORICAL.md](docs/HISTORICAL.md) for previous stack configurations.


## Current Active Setup — llama-swap only

| Group | Model | Context | -np | Memory | Model ID |
|---|---|---|---|---|---|
| **hermes** | 12B QAT MTP | 128k | 2 -kvu | ~19 GB | `unsloth-gemma4-12b-qat-128k-mtp` |
| **research** | 26B QAT MTP γ=2 | 128k | 1 | ~33 GB | `unsloth-gemma4-26b-a4b-qat-mtp2-128k-think` |
| **code** | Qwen3.6-27B UD-Q3 MTP γ=2 | 64k | 1 | ~25 GB | `unsloth-qwen36-27b-mtp2-ud-q3-64k-think-code` |
| **subagent** | 12B QAT MTP | 64k | 2 -kvu | ~14 GB | `unsloth-gemma4-12b-qat-64k-mtp-np2` |
| **compression** | E4B QAT TQ | 128k | 1 | ~9 GB | `unsloth-gemma4-e4b-qat-tq-128k-compression` |
| **test** | Ornith-35B Q4 @ 128k, Qwen3-Coder-Next | 64-128k | 1 | varies | multiple |
| **Total** | | | | **~100 GB** ✅ 31 GB free | |

> Test group not included in active memory calc. Ornith 35B at 128k adds ~27 GB when loaded.
> Hermes at 128k with -kvu gives 2 sessions sharing a 256k unified KV pool.


Start with:
```bash
docker compose up -d llama-swap
```

---

## Quick Reference

- **llama-swap API:** `http://localhost:8088/v1`
- **LibreChat UI:** `http://localhost:3080`
- **Open WebUI:** `http://localhost:3000`
- **MongoDB:** `localhost:27017`

## Model Groups

Models are organized by group in `llama-swap/config.yaml`. See `llama-swap/docs/MEMORY.md` for memory planning.


## vLLM (inactive)

vLLM is currently disabled. All models run on llama-swap.
Previous vLLM configurations are preserved in `docs/VLLM.md` and `docs/HISTORICAL.md`.
Docker-compose entries for vLLM (Gemma4 FP8, DiffusionGemma, Qwen NVFP4) kept as
commented backups for future reference.
