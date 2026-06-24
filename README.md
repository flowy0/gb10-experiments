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

### Gemma4 26B on vLLM — TurboQuant Incompatible

Gemma4 26B on vLLM forces `TRITON_ATTN` attention backend due to heterogeneous head
dimensions (`head_dim=256`, `global_head_dim=512`). TRITON_ATTN does not support
turboquant KV cache types, so `--kv-cache-dtype turboquant_k8v4` fails.

**Status:** Upstream vLLM issue. No fix available. Gemma4 vLLM uses fp8 KV cache.
TurboQuant works on llama-swap models via the llama-cpp-turboquant fork.

### llama-swap — MTP + TurboQuant Incompatible

MTP speculative decoding and TurboQuant KV cache cannot be used together on the same
model in the llama-cpp-turboquant fork. The MTP context fails to initialize with
turbo4 cache types.

**Resolution:** Models use either MTP (Qwen 27B for speed) or TurboQuant (12B QAT
for memory), not both on the same model.

### llama.cpp SHA Digest — Reference

llama.cpp image SHAs are pinned in `config.yaml` using `@sha256:` format.
When updating, use the manifest digest from `docker image inspect`, not the
Docker image ID.

---


See [docs/HISTORICAL.md](docs/HISTORICAL.md) for previous stack configurations.


## Current Active Setup — vLLM + llama-swap

| Service | Model | Context | Memory | Model ID |
|---|---|---|---|---|
| **vLLM** | Gemma4 26B NVFP4 + Marlin | 128k | ~46 GB¹ | ~50 tok/s | `unsloth-gemma4-26b-a4b-nvfp4-128k-think` |
| **llama-swap** | Qwen3.6 27B dense MTP think | 128k | ~34 GB | ~21 tok/s | `unsloth-qwen36-27b-mtp-q4-128k-think` |
| **llama-swap** | Gemma4 12B QAT + TurboQuant | 128k | ~26 GB | ~25 tok/s | `unsloth-gemma4-12b-qat-128k-tq` |
| **Total** | | | **~106 GB** ✅ 25 GB free | | |

¹ vLLM reserves via `--gpu-memory-utilization 0.35`. Model weights are 15.3 GB;
  remainder is KV cache pool and PagedAttention overhead.

Gemma4 via vLLM with PagedAttention. Qwen3.6 27B dense for coding with thinking. 12B QAT with TurboQuant for aux, vision, and compaction.

Start with:
```bash
docker compose up -d vllm-gemma4 llama-swap
```

### Model IDs

| Endpoint | Model ID |
|---|---|
| Port 8000 (vLLM) | `unsloth-gemma4-26b-a4b-nvfp4-128k-think` |
| Port 8088 (llama-swap) | `unsloth-qwen36-27b-mtp-q4-128k-think` |
| Port 8088 (llama-swap) | `unsloth-gemma4-12b-qat-128k-tq` |

---

## Quick Reference

- **llama-swap API:** `http://localhost:8088/v1`
- **LibreChat UI:** `http://localhost:3080`
- **Open WebUI:** `http://localhost:3000`
- **MongoDB:** `localhost:27017`

## Model Groups

Models are organized by group in `llama-swap/config.yaml`. See `llama-swap/docs/MEMORY.md` for memory planning.


## vLLM

See [docs/VLLM.md](docs/VLLM.md) for vLLM setup, benchmarking, and debugging history.
