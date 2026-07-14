# Memory Planning — GB10 (NVIDIA GB10, 131 GB unified VRAM)

## Hardware
- **GPU:** NVIDIA GB10, 131 GB unified VRAM
- **System RAM:** 121 GB (117 GB available)

## Model Architectures (KV cache size)

KV per token at q8_0 (1 byte/element): layers × KV heads × hd × 2 (K+V)

| Model | Layers | KV heads | hd | Elements/token |
|---|---|---|---|---|
| Qwen3.6-27B | 65 | 4 | 256 | 133,120 |
| Qwen3.6-35B MoE | 40 | 2 | 256 | 40,960 |
| Qwen3-Coder-Next (hybrid) | 12 attn | 2 | 256 | **12,288** |
| Ornith-1.0-35B MoE (Qwen3.5) | 40 | 2 | 256 | 40,960 |
| Ornith-1.0-9B (Qwen3.5 dense) | 32 | 8 | 128 | 65,536 |
| Gemma4 12B (E4B dense) | 42 | 2 | 256 | 43,008 |
| Gemma4 26B-A4B (MoE) | 30 | **8** | 256 | **122,880** |
| Gemma4 31B (dense) | ~48 | 8 | 256 | ~196,608 |

## KV Cache by Context

| Model | 64k | 128k | 256k |
|---|---|---|---|
| Qwen3.6-27B | 8.5 GB | 17.0 GB | 34.0 GB |
| Qwen3.6-35B MoE | 2.5 GB | 5.0 GB | 10.0 GB |
| Qwen3-Coder-Next | **0.8 GB** | 1.5 GB | 3.0 GB |
| Ornith-1.0-35B MoE | 2.5 GB | 5.0 GB | 10.0 GB |
| Ornith-1.0-9B | 4.3 GB | 8.6 GB | — |
| Gemma4 12B | 2.8 GB | 5.6 GB | 11.2 GB |
| Gemma4 26B | 7.5 GB | 15.0 GB | 30.0 GB |
| Gemma4 31B (dense) | ~25 GB | — | — |

## Total Memory per Model

Includes weights + KV cache + overhead. MTP adds ~0.2-0.5 GB for draft model.

| Model | Quant | File | Context | KV | OH | **Total** |
|---|---|---|---|---|---|---|
| **Hermes** | | | | | | |
| Gemma4 26B QAT MTP γ=2 | QAT UD-Q4_K_XL | 16 GB | 128k | 15 GB | 2 GB | **~33 GB** |
| + -np 2 (2 slots) | | | 128k | 30 GB | 2 GB | **~48 GB** |
| **Code** | | | | | | |
| Qwen3.6-27B MTP γ=2 | UD-Q3_K_XL | 14 GB | 64k | 8.5 GB | 2 GB | **~24 GB** |
| Ornith-1.0-35B MoE | Q4_K_M | 20 GB | 64k | 2.7 GB | 2 GB | **~25 GB** |
| Ornith-1.0-35B MoE | Q4_K_M | 20 GB | 128k | 5.4 GB | 2 GB | **~27 GB** |
| Qwen3-Coder-Next 80B | UD-Q3_K_M | 34 GB | 64k | 0.8 GB | 2 GB | **~37 GB** |
| **Aux / Compression** | | | | | | |
| Gemma4 12B QAT MTP | QAT UD-Q4_K_XL | 6.3 GB | 128k | 5.6 GB | 2 GB | **~14 GB** |
| Gemma4 12B QAT MTP | QAT UD-Q4_K_XL | 6.3 GB | 64k | 2.8 GB | 2 GB | **~11 GB** |
| Gemma4 E4B QAT TQ | QAT UD-Q4_K_XL | 4.7 GB | 128k | 2.8 GB | 2 GB | **~9 GB** |
| **Subagent** | | | | | | |
| Gemma4 12B QAT MTP -np 3 | QAT UD-Q4_K_XL | 6.3 GB | 64k | 8.4 GB | 2 GB | **~17 GB** |
| **Other** | | | | | | |
| Ornith-1.0-9B | Q4_K_M | 5.3 GB | 64k | 4.3 GB | 1 GB | **~11 GB** |
| Gemma4 31B (dense) | UD-Q4_K_XL | 18 GB | 64k | ~25 GB | 2 GB | **~45 GB** ⚠️ |
| Qwen3.6-35B MoE | IQ4_NL | 18 GB | 64k | 2.5 GB | 2 GB | **~23 GB** |

## Current Active Stack (v11 — vLLM hermes)

### Services
| Service | Role | Port | Memory |
|---|---|---|---|
| vLLM | hermes (Qwen3.6-35B-A3B NVFP4, 256k) | 8000 | **~52 GB** (40% reservation) |
| llama-swap | code, research, subagent, aux, test | 8088 | models loaded on demand |
| LiteLLM | unified router | 4000 | ~0.2 GB |

### llama-swap models (loaded on demand)

| Group | Model | Context | Weights | KV | OH | **Total** |
|---|---|---|---|---|---|---|
| code (MTP) | Qwen3.6-27B UD-Q3 MTP γ=2 | 64k | 14 GB | 8.5 GB | 2 GB | **~24 GB** |
| code (DFlash) | Qwen3.6-27B Q4_K_M + DFlash | 64k | 16+1 GB | 8.5 GB | 2 GB | **~27.5 GB** |
| research (MTP) | Gemma4 26B QAT MTP γ=2 | 128k | 16 GB | 15 GB | 2 GB | **~33 GB** |
| research (DFlash) | Gemma4 26B UD-Q4_K_M + DFlash | 128k | 16+0.25 GB | 15 GB | 2 GB | **~33.25 GB** |
| subagent (MTP) | Gemma4 12B QAT MTP -np 2 | 64k | 6.5 GB | 5.6 GB | 2 GB | **~14 GB** |
| subagent (DFlash) | Gemma4 12B Q4_K_M + DFlash | 64k | 6.7+0.4 GB | 2.8 GB | 1 GB | **~11 GB** |
| embed | BGE-M3 Q4_K_M | 32k | 0.4 GB | — | 0.5 GB | **~1 GB** |
| compression | Gemma4 12B QAT MTP (unused) | 256k | 6.5 GB | 11.2 GB | 2 GB | **~20 GB** |

### DFlash Speed Benchmarks

| Model | Target | Engine | Speculation | Acceptance | Speed |
|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | NVFP4 | vLLM | DFlash γ=15 | high | **270 tok/s** 🚀 |
| Gemma4 26B | UD-Q4_K_M | llama.cpp | DFlash γ=15 | 23% | **80 tok/s** |
| Gemma4 12B | Q4_K_M | llama.cpp | DFlash γ=15 | 60% | **76 tok/s** |

### Memory Scenarios

All scenarios include vLLM reservation (52 GB). llama-swap models load on demand.
Hermes handles all vision+agent tasks. **Load only one llama.cpp model at a time** to avoid OOM.

| Scenario | vLLM | + models | **Total** | **Free** |
|---|---|---|---|---|
| **Hermes only** (most common) | 52 GB | — | **52 GB** | **79 GB** ✅ |
| **+ embed** | 52 GB | 1 GB | **53 GB** | **78 GB** ✅ |
| **+ subagent (DFlash)** | 52 GB | 11 GB | **63 GB** | **68 GB** ✅ |
| **+ subagent (MTP)** | 52 GB | 14 GB | **66 GB** | **65 GB** ✅ |
| **+ code (MTP/DFlash)** | 52 GB | 24-27.5 GB | **76-79.5 GB** | **51.5-55 GB** ✅ |
| **+ research (MTP/DFlash)** | 52 GB | 33-33.25 GB | **85-85.25 GB** | **45.75-46 GB** ✅ |
| **+ code + sub (DFlash)** | 52 GB | 38.5 GB | **90.5 GB** | **40.5 GB** ✅ |
| **+ code + research (DFlash)** | 52 GB | 60.75 GB | **112.75 GB** | **18.25 GB** ✅ |
| **+ research + sub (DFlash)** | 52 GB | 44.25 GB | **96.25 GB** | **34.75 GB** ✅ |
| **+ all three (DFlash)** | 52 GB | 71.75 GB | **123.75 GB** | **7.25 GB** ✅ |
| **+ all + compression (worst)** | 52 GB | 91.75 GB | **143.75 GB** | **-12.75 GB** ❌ |

> All three DFlash models (71.75 GB) fit alongside vLLM in 131 GB (123.75 GB used).

## Previous Configurations

### v10 — 5-group llama-swap stack (replaced)
- hermes: Ornith 35B Q4_K_M (27 GB)
- code: Qwen3.6 27B UD-Q3 (24 GB)
- aux: 12B MTP 128k (14 GB)
- compression: E4B TQ 128k (9 GB)
- subagent: 12B MTP 64k -np 2 (14 GB)

### v9 — vLLM + llama-swap hybrid
- vLLM: Gemma4 26B FP8 + MTP 256k (52 GB)
- llama-swap (code): Qwen3.6 27B MTP (34 GB)
- llama-swap (summary): 12B QAT + TQ 256k (20 GB)

### v8 — DiffusionGemma test
- DiffusionGemma 26B NVFP4 on port 8001 (127 tok/s)
- FP8 26B on port 8000 (50 tok/s)
