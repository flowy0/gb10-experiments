# Historical Configurations

Previous stack configurations for reference.

## v10 — llama-swap only, multi-group stack

Replaced the vLLM + llama-swap hybrid with a pure llama-swap setup.
6 groups with different context windows and TTLs.

| Group | Model | Context | TTL |
|---|---|---|---|
| hermes | 26B QAT MTP γ=2 | 128k | 24h |
| code | 27B UD-Q3 MTP γ=2 | 64k | 1h |
| compression | E4B QAT + TQ | 128k | 30min |
| aux | 12B QAT + TQ | 64k | 1h |
| subagent | 35B IQ4 MTP | 64k | 30min |
| research | 26B QAT MTP γ=2 | 64k | 1h |

**Removed:** vLLM Gemma4 26B FP8 (was on port 8000)
**Removed:** DiffusionGemma 26B NVFP4 test (was on port 8001)
**Kept:** docker-compose entries preserved as commented backups.

## v9 — vLLM + llama-swap hybrid (replaced)

| Service | Model | Context |
|---|---|---|
| **vLLM** (port 8000) | Gemma4 26B FP8 + MTP γ=1 | 256k |
| **llama-swap** (code) | Qwen3.6 27B MTP Q4 think | 64k |
| **llama-swap** (summary) | Gemma4 12B QAT + TurboQuant | 256k |
| **Total** | | **~107 GB** |

## Archived: llama-swap Only (v6 — Gemma4 stack, replaced)

| Role | Model | Context | Memory | Group | Model ID |
|---|---|---|---|---|---|---|
| **pi (coding agent)** | Qwen3.6 35B IQ4 MTP think-code | 256k | 30 GB | `mtp-test` | `unsloth-qwen36-35b-a3b-mtp-iq4-256k-think-code` |
| **Hermes main** | Gemma4 26B QAT think | 256k | 46 GB | `hermes` | `unsloth-gemma4-26b-a4b-qat-256k-think` |
| **Hermes aux** | Gemma4 E4B QAT | 256k | 17 GB | `summary` | `unsloth-gemma4-e4b-qat-q4-256k` |
| **Total** (3 loaded) | | | **93 GB** ✅ 29 GB free | | |

All at 256k with matching context windows. 26B QAT at 82 tok/s (non-MTP) or 108 tok/s (MTP).

## Current Active Setup — vLLM + llama-swap

| Service | Model | Context | Memory | Model ID |
|---|---|---|---|---|
| **vLLM** | Gemma4 26B FP8 + MTP γ=1 | 128k | 44 GB | `unsloth-gemma4-26b-a4b-fp8-128k-think-mtp` |
| **llama-swap** | Qwen3.6 27B dense MTP | 128k | 34 GB | `unsloth-qwen36-27b-mtp-q4-128k` |
| **llama-swap** | Gemma4 12B QAT + TurboQuant | 128k | 26 GB | `unsloth-gemma4-12b-qat-128k-tq` |
| **Total** | | | **104 GB** ✅ 18 GB free | | |

Gemma4 served via vLLM with PagedAttention for multi-session reasoning at 128k. Qwen3.6 27B dense replaces the 35B MoE for coding (slower but all 27B params active). 12B QAT with TurboQuant handles aux, vision, and compaction tasks.

Start with:
```bash
docker compose up -d vllm-gemma4 llama-swap
```

### Model IDs

| Endpoint | Model ID |
|---|---|
| Port 8000 (vLLM) | `unsloth-gemma4-26b-a4b-fp8-128k-think-mtp` |
| Port 8088 (llama-swap) | `unsloth-qwen36-27b-mtp-q4-128k` |
| Port 8088 (llama-swap) | `unsloth-gemma4-12b-qat-128k-tq` |

### vLLM Configuration Notes

- Context reduced to 128k for lower memory footprint
- Chat template: `tool_chat_template_gemma4.jinja` (June 16, PR #45553)
- Reasoning enabled by default
- Single-slot baseline (`--max-num-seqs 2`)

### vLLM Alternatives

The compose file includes a disabled `vllm-gemma4` section. Uncomment to switch between models.

See [docs/VLLM.md](docs/VLLM.md) for build, benchmarking, and debugging history.

---
## Archived: llama-swap Only (v6 — Gemma4 stack, replaced)

| Role | Model | Context | Memory | Group | Model ID |
|---|---|---|---|---|---|---|
| **pi (coding agent)** | Qwen3.6 35B IQ4 MTP think-code | 256k | 30 GB | `mtp-test` | `unsloth-qwen36-35b-a3b-mtp-iq4-256k-think-code` |
| **Hermes main** | Gemma4 26B QAT think | 256k | 46 GB | `hermes` | `unsloth-gemma4-26b-a4b-qat-256k-think` |
| **Hermes aux** | Gemma4 E4B QAT | 256k | 17 GB | `summary` | `unsloth-gemma4-e4b-qat-q4-256k` |
| **Total** (3 loaded) | | | **93 GB** ✅ 29 GB free | | |

All at 256k with matching context windows. 26B QAT at 82 tok/s (non-MTP) or 108 tok/s (MTP).

## Current Active Setup — vLLM + llama-swap

| Service | Model | Context | Memory | Tok/s | Model ID |
|---|---|---|---|---|---|
| **vLLM** | Gemma4 26B FP8 + MTP γ=1 | 256k | 59 GB | 55 | `unsloth-gemma4-26b-a4b-fp8-256k-think-mtp` |
| **llama-swap** | Qwen3.6 35B IQ4 MTP think | 256k | 30 GB | ~80 | `unsloth-qwen36-35b-a3b-mtp-iq4-256k-think` |
| **llama-swap** | Gemma4 E4B QAT | 256k | 17 GB | ~60 | `unsloth-gemma4-e4b-qat-q4-256k` |
| **llama-swap** | Gemma3 12B vision | 64k | 14 GB | ~60 | `unsloth-gemma3-12b-q4-64k` |
| **Total** | | | **120 GB** ✅ 2 GB free | | |

Gemma4 served via vLLM with MTP and PagedAttention for multi-session reasoning. Qwen via llama-swap for coding. Gemma3 12B for vision/image tasks (loaded on demand). Start with:

```bash
docker compose up -d vllm-gemma4 llama-swap
```

### Model IDs

| Endpoint | Model ID |
|---|---|
| Port 8000 (vLLM) | `unsloth-gemma4-26b-a4b-fp8-256k-think-mtp` |
| Port 8088 (llama-swap) | `unsloth-qwen36-35b-a3b-mtp-iq4-256k-think` |
| Port 8088 (llama-swap) | `unsloth-gemma4-e4b-qat-q4-256k` |
| Port 8088 (llama-swap) | `unsloth-gemma3-12b-q4-64k` |

### vLLM Configuration Notes

- Chat template: `tool_chat_template_gemma4.jinja` (June 16 version with PR #45553 fixes)
- Reasoning: enabled by default via `--default-chat-template-kwargs {"enable_thinking":true}`
- BOS token: included natively in chat template
- Max context: 256k with fp8 KV cache
- Single-slot baseline (`--max-num-seqs 2`) for reliable tool testing

See [docs/VLLM.md](docs/VLLM.md) for build, benchmarking, and debugging history.

---## Historical Default Setups

### v8 — vLLM + Qwen3.6 35B @ 256k + E4B (replaced)

| Service | Model | Context | Memory |
|---|---|---|---|
| **vLLM** | Gemma4 26B FP8 + MTP | 256k | 59 GB |
| **llama-swap** | Qwen3.6 35B MoE IQ4 MTP | 256k | 30 GB |
| **llama-swap** | Gemma4 E4B QAT + vision | 256k | 18 GB |
| **Total** | | | **107 GB** ✅ |

Replaced by v9: all models at 128k with 27B dense and 12B QAT TQ.

### v7 — vLLM + Gemma4 26B @ 256k + llama-swap (previous)

| Service | Model | Context | Memory | Tok/s | Model ID |
|---|---|---|---|---|---|---|
| **vLLM** | Gemma4 26B FP8 + MTP γ=4 | 256k | 71 GB | 55 | `unsloth-gemma4-26b-a4b-fp8-256k-think-mtp` |
| **llama-swap** | Qwen3.6 35B IQ4 MTP | 256k | 30 GB | ~80 | `unsloth-qwen36-35b-a3b-mtp-iq4-256k` |
| **llama-swap** | Gemma4 E4B QAT | 256k | 17 GB | ~60 | `unsloth-gemma4-e4b-qat-q4-256k` |
| **Total** | | | **118 GB** ✅ 4 GB free | | |

vLLM served the 26B main with PagedAttention. Replaced by Qwen 35B FP8 (45 GB, frees 26 GB).

### v6 — Gemma4-Only Stack (llama-swap)



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
