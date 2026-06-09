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

## Recommended Default Setup

| Role | Model | Context | Memory | Group |
|---|---|---|---|---|
| **pi (coding agent)** | `unsloth-qwen36-35b-a3b-q2-256k` | 256k | 39 GB | `code` |
| **Hermes main** | `unsloth-qwen36-35b-a3b-q2-128k` | 128k | 34 GB | `hermes` |
| **Hermes aux** | `unsloth-gemma4-12b-qat-128k` | 128k | 32 GB | `hermes` |
| **Total** | | | **105 GB** | ✅ 17 GB free |

All at q8_0 KV cache (full speed). Pi gets 256k for long coding sessions. Hermes uses the same Qwen 35B family for consistency.

---

## Session Management

Based on 1,931 tracked sessions:
- **78.7%** fit in 128k, **86.7%** fit in 256k
- 13.3% exceed 256k — use 512k YaRN variant on-demand

### Final Recommended Setup

| Role | Model | Context | Memory | Group | Speed |
|---|---|---|---|---|---|
| **pi (coding agent)** | `unsloth-gemma4-26b-a4b-qat-256k-think` | 256k | 46 GB | `code` | ~82 tok/s |
| **Hermes main** | `unsloth-gemma4-26b-a4b-qat-128k-think` | 128k | 31 GB | `hermes` | ~83 tok/s |
| **Hermes aux** | `unsloth-gemma4-12b-qat-128k` | 128k | 32 GB | `summary` | ~46 tok/s |
| **Long context** (on-demand) | `unsloth-qwen36-35b-a3b-q2-512k-think` | 512k | 49 GB | `code` | ~15 tok/s |
| **Total** (3 loaded) | | | **110 GB** ✅ | | |

All at q8_0 KV cache (full precision). Matching context windows for deterministic compaction.
The 512k variant swaps in automatically for sessions exceeding 256k, then unloads.

## Quick Reference

- **llama-swap API:** `http://localhost:8088/v1`
- **LibreChat UI:** `http://localhost:3080`
- **Open WebUI:** `http://localhost:3000`
- **MongoDB:** `localhost:27017`

## Model Groups

Models are organized by group in `llama-swap/config.yaml`. See `llama-swap/docs/MEMORY.md` for memory planning.

## vLLM — Qwen3.6 Formats & Status

### Qwen3.6 35B Formats

| Format | Size | Quality | vLLM compat | Already have | MTP | TQ |
|---|---|---|---|---|---|---|
| **FP8** (official Qwen) | 35 GB | near-lossless 🏆 | `v0.20.0+` | ✅ | ✅ | ❌ |
| **NVFP4** (NVIDIA) | 22 GB | near-lossless | `v0.22.1+` / `nightly` | ✅ | ✅ | ❌ |
| AWQ 4-bit | 18 GB | good | `v0.18.0+` | ❌ | ✅ | ❌ |
| BF16 (original) | 70 GB | reference | any | ❌ | ✅ | ❌ |

**NVFP4** is officially recommended by NVIDIA for DGX Spark GB10 with:
```bash
export VLLM_USE_FLASHINFER_MOE_FP4=0
export VLLM_FP8_MOE_BACKEND=flashinfer_cutlass
vllm serve nvidia/Qwen3.6-35B-A3B-NVFP4 --quantization modelopt --kv-cache-dtype fp8
```

### Status

vLLM has not yet been deployed successfully. Previous attempts:

| Attempt | Image | Model | Issue |
|---|---|---|---|
| 1 | `v0.18.0-cu130` | FP8 | No SM 12.1 support |
| 2 | `aeon-vllm-ultimate` (40.8 GB) | NVFP4 | Container too large → OOM |
| 3 | `v0.22.1-aarch64` | NVFP4 | `lm_head.input_scale` modelopt mismatch |
| 4 | `cu129-nightly-aarch64` | NVFP4 | Loaded model but OOM during AutoTuner compilation |
| 5 | `cu129-nightly-aarch64` (no MTP) | NVFP4 | Loaded model but stuck in infinite AutoTuner loop (69+ passes) |
| 6 | `cu129-nightly-aarch64` (FP8 model) | FP8 (35 GB) | Crashed during KV cache init — OOM |

**Root cause:** vLLM's NVFP4 AutoTuner on GB10 never completes (infinite loop).
The FP8 mode crashes during KV cache allocation due to insufficient contiguous memory.
vLLM is not viable on this 128 GB system for Qwen3.6 models.

### Latest Recommendations

- **Image:** `vllm/vllm-openai:v0.22.1-aarch64` (CUDA 12.9, forward-compatible on 13.0 driver)
- **NVFP4 model:** Already downloaded (22 GB). NVIDIA officially recommends for GB10.
- **MTP:** `--speculative-config '{"method":"qwen3_next_mtp","num_speculative_tokens":2}'` (v0.20.0+)
- **TurboQuant** (`--kv-cache-dtype tq_k8v4`) requires nightly builds with PR #39931.

### Tradeoff

vLLM reserves memory upfront (`--gpu-memory-utilization`). At 0.45, it reserves ~55 GB for Qwen,
leaving ~67 GB for llama-swap to run Gemma4 alongside. Cannot run 3 models simultaneously
with vLLM active — run vLLM solo for maximum throughput, or pair with 1 llama-swap model.

### Wshobson reference config

```yaml
image: vllm/vllm-openai:v0.20.0-aarch64-cu130-ubuntu2404
model: Qwen/Qwen3.6-35B-A3B-FP8
command:
  - "--gpu-memory-utilization" "0.7069"
  - "--kv-cache-dtype" "fp8"
  - "--attention-backend" "flashinfer"
  - "--speculative-config" '{"method":"qwen3_next_mtp","num_speculative_tokens":2}'
```

## Gemma4 MTP — Pending

Gemma4 MTP support (PR #23398) was merged into llama.cpp on June 7, 2026, adding
`gemma4-assistant` architecture for speculative decoding with up to 2× speedup.

**Status:** The drafter model is downloaded (`gemma-4-26B-A4B-it-MTP-Q8_0.gguf`, 441 MB)
and the config entry exists (`-fa-think-mtp`) but requires a llama.cpp build >9544
that includes the June 7 merge. Current latest build is 9544 (June 6).

**To use once available:**
```bash
--model-draft /models/unsloth-gemma-4-26b-a4b-it-gguf/gemma-4-26B-A4B-it-MTP-Q8_0.gguf
--spec-type draft-mtp --spec-draft-n-max 4
--flash-attn on
```
