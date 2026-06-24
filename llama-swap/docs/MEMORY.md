# Memory Planning — GB10 (NVIDIA GB10, 122 GB unified VRAM)

## Hardware
- **GPU:** NVIDIA GB10, 122 GB unified VRAM
- **System RAM:** 121 GB (117 GB available)
- **llama.cpp server:** `ghcr.io/ggml-org/llama.cpp:server-cuda13-b9294`

## Model Architectures (for KV cache calculations)

| Model | Architecture | KV per token (q8_0) |
|---|---|---|
| Qwen3.6 27B (dense) | 65 layers, 4 KV heads, hd=256 | 65×4×256×2 = 133,120 elem |
| Qwen3.6 35B-A3B (MoE) | 40 layers, 2 KV heads, hd=256 | 40×2×256×2 = 40,960 elem |
| Qwen3-Coder-Next 80B (hybrid) | 12 attn layers, 2 KV heads, hd=256 | 12×2×256×2 = 12,288 elem |
| Gemma4 26B-A4B (MoE) | 30 layers, 8 KV heads, hd=256 | 30×8×256×2 = 122,880 elem |
| Gemma4 E4B (dense) | 42 layers, 2 KV heads, hd=256 | 42×2×256×2 = 43,008 elem |
| Gemma4 26B NVFP4 (vLLM) | 30 layers, 8 KV heads, hd=256 | 30×8×256×2 = 122,880 elem |

> **Note:** vLLM uses fp8 KV cache (1 byte/elem). llama.cpp uses q8_0 (1 byte/elem).
> Same byte footprint, but fp8 is hardware-accelerated on Blackwell.

## KV Cache Size by Context Length

KV cache in GB for each cache type at each context length:

| Model | 32k (q8_0) | 64k (q8_0) | 128k (q8_0) | 256k (q8_0) | 256k (q5_1) |
|---|---|---|---|---|---|
| Qwen3.6 27B | 4.2 | 8.5 | 17.0 | 34.0 | 25.5 |
| Qwen3.6 35B-A3B | 1.3 | 2.5 | 5.0 | 10.0 | 7.5 |
| Qwen3-Coder-Next | 0.4 | 0.8 | 1.5 | 3.0 | 2.3 |
| Gemma4 26B-A4B | 3.8 | 7.5 | 15.0 | 30.0 | 22.5 |
| Gemma4 E4B | 1.3 | 2.7 | 5.4 | 10.8 | 8.1 |

## Total Memory per Model at 256k

| Model | Quant | File | KV (256k) | +OH | Total |
|---|---|---|---|---|---|
| Qwen3.6 35B-A3B | UD-Q2_K_XL | 26.8 GB | 10.0 GB | 2 GB | **39 GB** |
| Qwen3.6 35B-A3B MTP | UD-Q2_K_XL | 26.8 GB | 10.0 GB | 3 GB | **40 GB** |
| Qwen3.6 27B | Q4_K_M | 16.0 GB | 34.0 GB | 2 GB | **52 GB** |
| Qwen3-Coder-Next | UD-IQ2_M | 24.0 GB | 3.0 GB | 2 GB | **29 GB** |
| Gemma4 26B-A4B | UD-Q4_K_M | 16.9 GB | 30.0 GB | 2 GB | **49 GB** |
| Gemma4 26B-A4B | UD-Q5_K_M | 20.0 GB | 30.0 GB | 2 GB | **52 GB** |
| Gemma4 26B-A4B (q5_1 cache) | UD-Q4_K_M | 16.9 GB | 22.5 GB | 2 GB | **41 GB** |
| Gemma4 E4B | Q4_K_M | 4.7 GB | 10.8 GB | 2 GB | **17 GB** |

### vLLM Models (HuggingFace format)

| Model | Format | File | KV (128k, fp8) | +OH | Total (estimate) |
|---|---|---|---|---|---|
| Gemma4 26B NVFP4 | NVFP4 + Marlin | 15.3 GB | ~15 GB | ~16 GB | **~46 GB**¹ |

¹ vLLM reserves memory upfront via `--gpu-memory-utilization 0.35`. Actual usage
  depends on KV cache fill. The 15.3 GB checkpoint is NVFP4 weights stored in GPU
  memory; Marlin decompresses to BF16 tile-by-tile during GEMM.

## Group Configuration

| Group | swap | exclusive | Members |
|---|---|---|---|
| test-models | true | false | All new/experimental models (64 models) |
| code | true | false | Devstral, Qwen3-Coder, Qwen3-Coder-Next, Qwen3.5 27B (8 models) |
| research | true | false | Qwen3.6 35B MTP 128k, Qwen3.6 35B Q2 256k (2 models) |
| stable | true | false | Gemma4 26B variants (64k/128k/256k) (5 models) |
| summary | true | false | Granite 8B 128k (1 model) |
| hermes | true | false | Qwen3.5 35B 128k FA (1 model) |

Models in different groups can run simultaneously. Within a group, `swap: true` means requesting a different model in the same group swaps the active one.

## Common Pairings

### Research + Stable (default research pair)
- `research`: Qwen3.6 35B-A3B Q2 @ 256k — **39 GB**
- `stable`: Gemma4 26B-A4B Q4 @ 256k (q5_1 cache) — **41 GB**
- **Total: ~80 GB** ✅ (42 GB free)

### Code + Hermes
- `code`: Qwen3-Coder-Next @ 256k — **29 GB**
- `hermes`: Qwen3.5 35B @ 128k — **27 GB**
- **Total: ~56 GB** ✅ (66 GB free)

### Research + Code + Stable
- All three simultaneously at 256k
- **Total: ~108 GB** ✅ (14 GB free, tight)

## Current Active Stack (vLLM + llama-swap hybrid)

| Service | Model | Context | Memory | Model ID |
|---|---|---|---|---|
| **vLLM** | Gemma4 26B NVFP4 + Marlin | 128k | ~46 GB | `unsloth-gemma4-26b-a4b-nvfp4-128k-think` |
| **llama-swap** | Qwen3.6 27B MTP think | 128k | ~34 GB | `unsloth-qwen36-27b-mtp-q4-128k-think` |
| **llama-swap** | Gemma4 12B QAT + TurboQuant | 128k | ~26 GB | `unsloth-gemma4-12b-qat-128k-tq` |
| **Total** | | | **~106 GB** ✅ 25 GB free | |

**Savings vs previous FP8 stack:** NVFP4 saves ~18 GB over FP8 (46 GB vs 64 GB
with MTP assistant), enabling the 3-model configuration at 128k with comfortable
headroom for session scaling.

## KV Cache Best Practices

- **q8_0** — best quality, used by default
- **q5_1** — good for 256k context (0.75× size of q8_0, minimal quality loss)
- **q4_0** — aggressive, only if needed for fitting very large contexts
- Flash attention (`--flash-attn on`) reduces compute but does not reduce KV cache memory
- `--no-warmup` skips the warmup pass on load, saving minutes on 128k/256k models

## Session Scaling

To increase parallel sessions without reducing per-slot context, increase the KV pool:

```
New KV pool = current pool × (desired slots / current slots)
```

For Qwen3.6 35B-A3B (40 layers, 2 KV heads, 256 hd — 40,960 elem/token):

| Sessions | Context | Cache | KV pool | Per slot max |
|---|---|---|---|---|
| 3 | 256k | q5_1 | 8 GB | 256k |
| 6 | 256k | q5_1 | 16 GB | 256k |
| 4 | 512k (YaRN) | q5_1 | 22 GB | 512k |
| 6 | 512k (YaRN) | q5_1 | 32 GB | 512k |
| 6 | 512k (YaRN) | q4_0 | 22 GB | 512k |

To scale: increase `--parallel N` and proportionally increase `-c` or reduce cache quantization.
The MoE's tiny KV (2 heads) makes this much cheaper than dense models.

For Gemma 4 26B-A4B (30 layers, 8 KV heads — 122,880 elem/token):

| Sessions | Context | Cache | KV pool | Per slot max |
|---|---|---|---|---|
| 3 | 256k | q5_1 | 23 GB | 256k |
| 4 | 256k | q5_1 | 30 GB | 256k |

Gemma 4's larger KV heads make session scaling more expensive.
