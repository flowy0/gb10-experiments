# Benchmark Results

Speed measured with minimal prompt ("hi"), 100 output tokens, all models loaded simultaneously unless noted.
vLLM speeds use enforce-eager (CUDA graphs disabled on Blackwell SM121 for standard models).

## Ornith-1.0-35B MoE (llama.cpp)
| Quant | File | tok/s | tool-eval | Notes |
|---|---|---|---|---|
| Q4_K_M | 20 GB | 77 | **100/100** ★★★★★ | Best coding model tested. Flash attention on. |

## Qwen3.6 27B (llama.cpp, MTP γ=2)

| Quant | File | tok/s | Notes |
|---|---|---|---|
| UD-Q3_K_XL | 14 GB | 31 | Best speed/quality balance |
| UD-Q2_K_XL | 12 GB | 30 | Fast, 2-bit lossy |
| Q4_K_M | 16 GB | 28 | Baseline |
| IQ4_NL | 16 GB | 26 | Same size as Q4, slower |
| UD-Q4_K_XL | 17 GB | 21 | Best quality |
| NVFP4 (vLLM) | 25 GB | 17 | Too heavy — skip |
| PRISM PRO DQ | 13 GB | 15 | llama.cpp baseline |

## Gemma4 26B

| Engine | Variant | Context | tok/s | Notes |
|---|---|---|---|---|
| vLLM | FP8 + MTP γ=1 | 256k | 50 | enforce-eager (no CUDA graphs) |
| vLLM | FP8 + MTP γ=3 | 256k | — | Same config, γ=3 |
| vLLM | NVFP4 + Marlin | 128k | 72-75 | CUDA graphs work, quality regressed |
| llama.cpp | QAT Q4 + MTP γ=1 | 128k | ~19 | CUDA graphs work |

## Gemma4 12B

| Engine | Variant | Context | tok/s | Notes |
|---|---|---|---|---|
| llama.cpp | QAT + TurboQuant | 256k | 13 | With vLLM loaded concurrently |
| llama.cpp | Agentic v2 Q4 | 128k | ~15 | Fine-tuned for agentic tasks |

## Gemma4 31B

| Engine | Variant | Context | tok/s | Notes |
|---|---|---|---|---|
| llama.cpp | UD-Q4_K_XL + TQ | 128k | — | Not tested |
| llama.cpp | UD-Q4_K_XL + MTP | 128k | — | Not tested |

## DiffusionGemma 26B NVFP4 (vLLM v0.22.1)

| Setup | tok/s | Notes |
|---|---|---|
| Single request, long output | 127-135 | 256-token canvas filled |
| tool-eval-bench score | 85/100 | 53/69 passed |
| CUDA graphs | ✅ | VLLM_USE_V2_MODEL_RUNNER=1, TRITON_ATTN |

## Tool Calling Quality (tool-eval-bench)

| Model | Score | Rating |
|---|---|---|
| **Ornith-1.0-35B MoE Q4_K_M** | **100/100** | **★★★★★ Excellent** |
| Qwen3.6 27B UD-Q3_K_XL | 97/100 | ★★★★★ Excellent |
| DiffusionGemma 26B NVFP4 | 85/100 | ★★★★ Good |
| FP8 26B (June 14 baseline) | ~91/100 | ★★★★ |
| FP8 26B (128k) | ~73/100 | ★★★ Adequate |
