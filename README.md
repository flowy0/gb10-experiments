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

## Current Active Setup

| Role | Model | Context | Memory | Group |
|---|---|---|---|---|
| **pi (coding agent)** | `unsloth-qwen36-35b-a3b-mtp-iq4-256k-think-code` | 256k | 30 GB | `mtp-test` |
| **Hermes main** | `unsloth-gemma4-26b-a4b-qat-256k-think` | 256k | 46 GB | `hermes` |
| **Hermes aux** | `unsloth-gemma4-e4b-qat-q4-256k` | 256k | 17 GB | `summary` |
| **Total** (3 loaded) | | | **93 GB** ✅ 29 GB free | |

All at 256k with matching context windows for deterministic compaction. The Qwen 35B MTP IQ4_NL (18 GB file, 2 KV heads) is the pi coding model. The E4B QAT (4 GB file, 2 KV heads) replaces the 12B QAT for aux tasks — saves 38 GB at 256k while handling summarization, search, and compression.

---

## Historical Default Setups

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

### Custom vLLM Build for Gemma4 (spark-vllm-docker)

The stock `vllm/vllm-openai` images don't support Gemma4 on Blackwell (GB10) due to:
- Missing `TRITON_ATTN` backend fallback (CUTLASS crashes on SM121)
- Outdated Transformers (no `gemma4` architecture recognition)
- Missing Blackwell-specific patches

A working image was built using [spark-vllm-docker](https://github.com/eugr/spark-vllm-docker):

```bash
# Build the image (requires ~2.6 TB free, takes 1-2 hours)
cd build/spark-vllm-docker
./build-and-copy.sh -t vllm-node-tf5 --tf5
```

**Result:** `vllm-node-tf5:latest` (19 GB) with:
- Transformers v5 (Gemma4 architecture support)
- Blackwell SM121 compilation (`TORCH_CUDA_ARCH_LIST="12.1a"`)
- `TRITON_ATTN` backend (no CUTLASS crash)
- NVFP4 support with `VLLM_CUTLASS` NvFp4 MoE backend

**Usage with NVFP4 model:**
```bash
docker run --gpus all --network host --ipc=host \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  --entrypoint vllm \
  -v /opt/atom/models/nvidia-gemma-4-26b-a4b-nvfp4:/model:ro \
  vllm-node-tf5:latest serve /model \
  --host 0.0.0.0 --port 8000 \
  --max-model-len 65536 --gpu-memory-utilization 0.4 \
  --tensor-parallel-size 1 \
  --load-format safetensors \
  --kv-cache-dtype fp8 --enforce-eager
```

**Performance on GB10:**
| Metric | vLLM NVFP4 | llama-swap QAT |
|---|---|---|
| Decode | 26 tok/s | **82 tok/s** (non-MTP) / **108 tok/s** (MTP) |
| Models | 1 at a time | **3 simultaneously** |
| Multi-session | PagedAttention | 4-slot KV pool |
| MTP support | ❌ | ✅ |

**Benchmark command:**
```bash
curl -X POST http://localhost:8022/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"/model","messages":[{"role":"user","content":"Write a paragraph"}],"max_tokens":200}'
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
