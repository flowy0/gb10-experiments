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
| code | Qwen3.6-27B UD-Q3 MTP γ=2 | 64k | 14 GB | 8.5 GB | 2 GB | **~24 GB** |
| research | Gemma4 26B QAT MTP γ=2 | 128k | 16 GB | 15 GB | 2 GB | **~33 GB** |
| subagent | Gemma4 12B QAT MTP -np 2 | 64k | 6.5 GB | 5.6 GB | 2 GB | **~14 GB** |
| compression (12B) | Gemma4 12B QAT MTP (vision+compression) | 256k | 6.5 GB | 11.2 GB | 2 GB | **~20 GB** |

### Memory Scenarios

All scenarios include vLLM reservation (52 GB). llama-swap models load on demand.
Hermes handles all vision+agent tasks — compression model only loads for compression.

| Scenario | vLLM | + models | **Total** | **Free** |
|---|---|---|---|---|
| **Hermes only** | 52 GB | — | **52 GB** | **79 GB** ✅ |
| **Hermes + compression** | 52 GB | 20 GB | **72 GB** | **59 GB** ✅ |
| **Hermes + code** | 52 GB | 24 GB | **76 GB** | **55 GB** ✅ |
| **Hermes + code + research** | 52 GB | 57 GB | **109 GB** | **22 GB** ✅ |
| **Hermes + code + subagent** | 52 GB | 35 GB | **87 GB** | **44 GB** ✅ |
| **Hermes + code + research + sub** | 52 GB | 68 GB | **120 GB** | **11 GB** ✅ |
| **Hermes + compression + code** | 52 GB | 44 GB | **96 GB** | **35 GB** ✅ |
| **Hermes + all (worst case)** | 52 GB | 88 GB | **140 GB** | **-9 GB** ❌ |

> Most common: hermes alone (~52 GB). Compression loads only for compression tasks (~5s).
> Code/research/subagent load on demand. Worst case exceeds by 9 GB — models swap naturally.

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
