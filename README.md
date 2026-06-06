# /opt/atom — Local AI Stack

Self-hosted LLM serving stack on an NVIDIA GB10 (122 GB unified VRAM).

## Core Services

| File/Dir | Purpose |
|---|---|
| `llama-swap/` | Model router config (`config.yaml`) and swap definitions |
| `llama-swap/docs/MEMORY.md` | Memory planning docs with architecture tables |
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

---

## Quick Reference

- **llama-swap API:** `http://localhost:8088/v1`
- **LibreChat UI:** `http://localhost:3080`
- **Open WebUI:** `http://localhost:3000`
- **MongoDB:** `localhost:27017`

## Model Groups

Models are organized by group in `llama-swap/config.yaml`. See `llama-swap/docs/MEMORY.md` for memory planning.

## vLLM — Not Currently Used

vLLM was attempted for Qwen3.6 35B FP8 at 512k context but has two blockers:

1. **Driver version:** NVIDIA vLLM containers require driver ≥ 590.48 (host has 580.159.03). The custom `hellohal2064/vllm-dgx-spark-gb10` image works on this driver but lacks Qwen3.5/3.6 architecture support.
2. **Transformers version:** Qwen3.6 uses `qwen3_5_moe` architecture which requires a newer transformers release than what's available in any vLLM container image currently on the system.

**Status:** On hold until vLLM/transformers releases support for Qwen3.5/3.6 architecture. Meanwhile, llama.cpp serves Qwen3.6 35B at 256k with Q2 GGUF.
