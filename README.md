# /opt/atom — Local AI Stack

Self-hosted LLM serving stack on an NVIDIA GB10 (122 GB unified VRAM).

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

**Status:** Unresolved. Use a Qwen model (`unsloth-qwen36-35b-a3b-q2-256k`) for agentic
workflows that require web search and tool execution.

### LibreChat — RAG API Warning

```
RAG API is either not running or not reachable at undefined
```

LibreChat's RAG API is not deployed. File upload features may have issues.
This does not affect chat or agent tool execution.

### E4B MTP — Segfault on b9585 (Blackwell GB10)

The E4B MTP spec decoding variant (`unsloth-gemma4-e4b-qat-q4-256k-mtp`) crashes with exit code 139 (segfault) at context sizes ≥128k on NVIDIA GB10.

- **Works:** small contexts (<64k) with `--flash-attn off` + `-fit off`
- **Fails:** 128k+ → CUDA flash attention crash + segfault
- **26B MTP** works fine with same flags — likely a b9585 build bug specific to E4B MTP
- **Workaround:** Use non-MTP E4B QAT variant instead

### llama.cpp SHA Digest — Wrong Image ID Used

When updating b9544 → b9585, the SHA was incorrectly set to the Docker image ID instead of the registry manifest digest. The image ID is a content hash, not a valid `@sha256:` pin. Fixed by using the repo digest from `docker image inspect`.

### Gemma4 12B — Dense KV Cache at 256k

The 12B (48 layers × 8 KV heads) uses 48 GB for KV cache alone at 256k with q8_0, limiting concurrent sessions. Solution: use E4B (2 KV heads, 10 GB KV cache at 256k) for aux tasks.

---

## Current Active Setup — llama-swap Only

| Role | Model | Context | Memory | Group |
|---|---|---|---|---|
| **pi (coding agent)** | `unsloth-qwen36-35b-a3b-mtp-iq4-256k-think-code` | 256k | 30 GB | `mtp-test` |
| **Hermes main** | `unsloth-gemma4-26b-a4b-qat-256k-think` | 256k | 46 GB | `hermes` |
| **Hermes aux** | `unsloth-gemma4-e4b-qat-q4-256k` | 256k | 17 GB | `summary` |
| **Total** (3 loaded) | | | **93 GB** ✅ 29 GB free | |

All at 256k with matching context windows. 26B QAT at 82 tok/s (non-MTP) or 108 tok/s (MTP).

## Current Active Setup — vLLM + llama-swap

| Service | Model | Context | Memory | Tok/s |
|---|---|---|---|---|
| **vLLM** | Qwen3.6 35B FP8 + MTP γ=2 | 256k | 45 GB | 55 |
| **llama-swap** | Gemma4 26B QAT think | 128k | 31 GB | ~80 |
| **llama-swap** | Gemma4 E4B QAT | 256k | 17 GB | ~60 |
| **Total** | | | **93 GB** ✅ 29 GB free | |

vLLM serves the Qwen 35B with built-in MTP and PagedAttention (isolated per-session KV cache). llama-swap handles the 26B for thinking tasks and E4B for aux. Start with:

```bash
docker compose up -d vllm-qwen35 llama-swap
```

### Model IDs

| Endpoint | Model ID |
|---|---|
| Port 8000 (vLLM) | `unsloth-qwen36-35b-a3b-fp8-256k-think-mtp` |
| Port 8088 (llama-swap) | `unsloth-gemma4-26b-a4b-qat-128k-think` |
| Port 8088 (llama-swap) | `unsloth-gemma4-e4b-qat-q4-256k` |

### Note on vLLM Reasoning Format

vLLM's `--reasoning-parser qwen3` puts thinking content in `message.reasoning` (not `message.reasoning_content` like llama-swap). If your agent expects a different format, remove `--reasoning-parser qwen3` from the vLLM config.

### vLLM Alternatives

The compose file also includes a disabled `vllm-gemma4` service (Gemma4 26B FP8 + separate MTP assistant). Uncomment it and comment `vllm-qwen35` to switch back.

See [docs/VLLM.md](docs/VLLM.md) for build, benchmarking, and multi-session details.

---pt/atom — Local AI Stack

Self-hosted LLM serving stack on an NVIDIA GB10 (122 GB unified VRAM).

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

**Status:** Unresolved. Use a Qwen model (`unsloth-qwen36-35b-a3b-q2-256k`) for agentic
workflows that require web search and tool execution.

### LibreChat — RAG API Warning

```
RAG API is either not running or not reachable at undefined
```

LibreChat's RAG API is not deployed. File upload features may have issues.
This does not affect chat or agent tool execution.

### E4B MTP — Segfault on b9585 (Blackwell GB10)

The E4B MTP spec decoding variant (`unsloth-gemma4-e4b-qat-q4-256k-mtp`) crashes with exit code 139 (segfault) at context sizes ≥128k on NVIDIA GB10.

- **Works:** small contexts (<64k) with `--flash-attn off` + `-fit off`
- **Fails:** 128k+ → CUDA flash attention crash + segfault
- **26B MTP** works fine with same flags — likely a b9585 build bug specific to E4B MTP
- **Workaround:** Use non-MTP E4B QAT variant instead

### llama.cpp SHA Digest — Wrong Image ID Used

When updating b9544 → b9585, the SHA was incorrectly set to the Docker image ID instead of the registry manifest digest. The image ID is a content hash, not a valid `@sha256:` pin. Fixed by using the repo digest from `docker image inspect`.

### Gemma4 12B — Dense KV Cache at 256k

The 12B (48 layers × 8 KV heads) uses 48 GB for KV cache alone at 256k with q8_0, limiting concurrent sessions. Solution: use E4B (2 KV heads, 10 GB KV cache at 256k) for aux tasks.

---

## Current Active Setup — llama-swap Only

| Role | Model | Context | Memory | Group |
|---|---|---|---|---|
| **pi (coding agent)** | `unsloth-qwen36-35b-a3b-mtp-iq4-256k-think-code` | 256k | 30 GB | `mtp-test` |
| **Hermes main** | `unsloth-gemma4-26b-a4b-qat-256k-think` | 256k | 46 GB | `hermes` |
| **Hermes aux** | `unsloth-gemma4-e4b-qat-q4-256k` | 256k | 17 GB | `summary` |
| **Total** (3 loaded) | | | **93 GB** ✅ 29 GB free | |

All at 256k with matching context windows. 26B QAT at 82 tok/s (non-MTP) or 108 tok/s (MTP).

## Current Active Setup — vLLM + llama-swap

| Service | Model | Context | Memory | Tok/s |
|---|---|---|---|---|
| **vLLM** | Gemma4 26B FP8 + MTP γ=4 | 256k | 67 GB | 55 |
| **llama-swap** | Qwen3.6 35B IQ4 MTP | 256k | 30 GB | ~80 |
| **llama-swap** | Gemma4 E4B QAT | 256k | 17 GB | ~60 |
| **Total** | | | **114 GB** ✅ 8 GB free | |

vLLM handles the 26B main with MTP speculative decoding and PagedAttention (isolated per-session KV cache, no compaction). llama-swap serves Qwen 35B for pi coding and E4B for aux tasks. Start with:

```bash
docker compose up -d vllm-gemma4 llama-swap
```

### MTP Performance (vLLM)

Tested with 2 concurrent sessions, 256k context:

| Metric | Value |
|---|---|
| Mean acceptance length | 2.65 / 4 drafted |
| Per-position acceptance | 71%, 46%, 30%, 17% |
| Avg draft acceptance rate | 41.2% |
| Generation throughput | 70.5 tok/s (2 sessions) |
| Single session decode | 54-60 tok/s |

### Model ID

```
unsloth-gemma4-26b-a4b-fp8-256k-mtp  (port 8000)
```

See [docs/VLLM.md](docs/VLLM.md) for build, benchmarking, and multi-session details.

---## Historical Default Setups

### v6 — Gemma4-Only Stack

| Role | Model | Context | Memory | Group | Speed |
|---|---|---|---|---|---|
| **pi (coding agent)** | `unsloth-gemma4-26b-a4b-qat-256k-think` | 256k | 46 GB | `code` | ~82 tok/s |
| **Hermes main** | `unsloth-gemma4-26b-a4b-qat-128k-think` | 128k | 31 GB | `hermes` | ~83 tok/s |
| **Hermes aux** | `unsloth-gemma4-12b-qat-128k` | 128k | 32 GB | `summary` | ~46 tok/s |
| **Long context** (on-demand) | `unsloth-qwen36-35b-a3b-q2-512k-think` | 512k | 49 GB | `code` | ~15 tok/s |
| **Total** (3 loaded) | | | **110 GB** ✅ | | |

### v5 — Qwen 35B Q2 Defaults

| Role | Model | Context | Memory | Group |
|---|---|---|---|---|
| **pi (coding agent)** | `unsloth-qwen36-35b-a3b-q2-256k` | 256k | 39 GB | `code` |
| **Hermes main** | `unsloth-qwen36-35b-a3b-q2-128k` | 128k | 34 GB | `hermes` |
| **Hermes aux** | `unsloth-gemma4-12b-qat-128k` | 128k | 32 GB | `hermes` |
| **Total** | | | **105 GB** | ✅ 17 GB free |

### Session Notes

- All setups use q8_0 KV cache (full precision)
- Matching context windows for deterministic compaction
- Based on 1,931 tracked sessions: 78.7% fit in 128k, 86.7% fit in 256k
- 512k YaRN variant swaps in on-demand for sessions exceeding 256k

## Quick Reference

- **llama-swap API:** `http://localhost:8088/v1`
- **LibreChat UI:** `http://localhost:3080`
- **Open WebUI:** `http://localhost:3000`
- **MongoDB:** `localhost:27017`

## Model Groups

Models are organized by group in `llama-swap/config.yaml`. See `llama-swap/docs/MEMORY.md` for memory planning.


## vLLM

See [docs/VLLM.md](docs/VLLM.md) for vLLM setup, benchmarking, and investigation history.
