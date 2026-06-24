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


## Historical

See [docs/HISTORICAL.md](docs/HISTORICAL.md) for previous stack configurations.

## Quick Reference

- **llama-swap API:** `http://localhost:8088/v1`
- **LibreChat UI:** `http://localhost:3080`
- **Open WebUI:** `http://localhost:3000`
- **MongoDB:** `localhost:27017`

## Model Groups

Models are organized by group in `llama-swap/config.yaml`. See `llama-swap/docs/MEMORY.md` for memory planning.


## vLLM
