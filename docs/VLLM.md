# vLLM on DGX Spark (GB10) — AEON vLLM Ultimate

> **RETIRED 2026-08-17** — the AEON vLLM service was replaced by SGLang + Qwen3.8-27B
> (`radixark-qwen38-27b-nvfp4-dspark-262k-think`) as the main model. This doc is kept as
> historical reference. Key reasons: stock/AEON vLLM on this box repeatedly OOM'd the NVIDIA
> driver (NV_ERR_NO_MEMORY) at the recipe's gpu-memory-utilization; the AEON config is commented
> out in docker-compose.yml (never deleted). See docs/QWEN38_RESEARCH.md for the full comparison.

## Current Status

| Item | Value |
|---|---|
| **Image** | `ghcr.io/aeon-7/aeon-vllm-ultimate:2026-07-16-v0.25.1` |
| **Model** | `redhatai/gemma-4-26B-A4B-it-NVFP4` (16 GB) |
| **DFlash draft** | `z-lab/gemma-4-26B-A4B-it-DFlash` (820 MB) |
| **Version** | vLLM v0.25.1+aeon.sm121a.dflash |
| **Speed** | **309 tok/s** 🚀 |
| **Build source** | [AEON-7/vllm-ultimate-dgx-spark](https://github.com/AEON-7/vllm-ultimate-dgx-spark) |

## Key Features

- **DFlash** γ=12 with Triton attention backend
- **FP8 KV cache** (fp8_e4m3) — 2× KV capacity
- **UMA hardened** — no cascade crash (vLLM spark build was prone to this)
- **Gemma4 NVFP4** loading fixed (was crashing on spark build)
- **Vision** — image input supported out of box
- **Tool calling** — working with auto-tool-choice
- **Persistent cache** — second restart warms in ~2 min (vs ~13 min cold)

## Usage

```bash
# Start
docker compose up -d aeon-gemma4-26b

# Test
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"aeon-gemma4-26b-nvfp4-dflash-131k-think","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'

# Speed test
time curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"aeon-gemma4-26b-nvfp4-dflash-131k-think","messages":[{"role":"user","content":"Count 1 to 100"}],"max_tokens":300}' | jq '.usage.completion_tokens'
```

## Key Flags

| Flag | Value | Why |
|---|---|---|
| `--quantization` | `compressed-tensors` | NVFP4 format from RedHatAI |
| `--kv-cache-dtype` | `fp8_e4m3` | FP8 KV cache for DFlash (NVFP4 KV not compatible) |
| `--attention-backend` | `TRITON_ATTN` | Required for DFlash on Spark |
| `--speculative-config` | `dflash` γ=12 | Must include `"attention_backend":"TRITON_ATTN"` inside JSON |
| `--gpu-memory-utilization` | `0.60` | Leaves room for llama-swap models |
| `VLLM_USE_V2_MODEL_RUNNER` | `0` | Pin to V1 runner (V2 has lm_head bug) |

## DFlash Config

```json
{"method":"dflash","model":"/dflash","num_speculative_tokens":12,"attention_backend":"TRITON_ATTN"}
```

Must set `attention_backend` both in the main flags AND inside the speculative-config JSON — vLLM doesn't inherit the target's backend into the speculative drafter.

## Performance

| Model | AEON vLLM | Previous (spark build) | Improvement |
|---|---|---|---|
| **Gemma4 26B NVFP4** | **309 tok/s** | 50-73 tok/s | 4-6× 🚀 |
| **Qwen3.6-35B-A3B NVFP4** | **222 tok/s** | 73 tok/s | 3× 🚀 |

## Build History

### 2026-07-28 — Switched to AEON vLLM Ultimate
- Pulled `ghcr.io/aeon-7/aeon-vllm-ultimate:2026-07-16-v0.25.1`
- Gemma4 26B reached **309 tok/s** with DFlash + FP8 KV
- Old `vllm-node-tf5` image commented out

### Previous — spark-vllm-docker (deprecated)
- Custom build from `build/spark-vllm-docker/`
- vLLM v0.23.1rc1 with MTP speculation
- Prone to GPU cascade crashes (NVRM Xid errors → system lockup)
- ~73 tok/s on Qwen35B, ~50 tok/s on Gemma4 26B FP8
