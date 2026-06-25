# /opt/atom — Local AI Stack

## Critical Rules

### Config File Integrity
- **Never delete model definitions** in `llama-swap/config.yaml` — comment them out instead with `# `
- Always validate YAML after edits: `python3 -c "import yaml; yaml.safe_load(open('llama-swap/config.yaml'))"`
- Restart llama-swap after config changes: `docker compose restart llama-swap`
- Use `sed -i` for group member changes, not whole-file Python scripts
- When adding entries near existing ones, use exact text match, not line numbers

### Git Workflow
- Always commit and push after config changes: `git add -A && git commit -m "message" && git push`
- Check `git diff --stat` before committing to verify no unintended changes
- If a model definition gets corrupted, restore with `git checkout HEAD -- llama-swap/config.yaml`

### Model Management
- Active stack (vLLM FP8 256k + 12B TQ 256k):
  - `unsloth-gemma4-26b-a4b-fp8-256k-think-mtp` (vLLM, port 8000)
  - `unsloth-gemma4-12b-qat-256k-tq` (llama-swap, summary group)
  - `unsloth-qwen36-27b-mtp-q4-think` (llama-swap, code group, 64k)
- Models load on first request
- llama-swap TTL: 3600s (1h) for most, 86400s (24h) for sticky models

### vLLM Naming Convention
- Model ID format: `unsloth-{family}-{arch}-{quant}-mtp-{ctx}-{mode}`
  - Example: `unsloth-qwen36-35b-a3b-fp8-256k-think-mtp`
- Compose service format: `vllm-{family}` (e.g., `vllm-qwen35`, `vllm-gemma4`)
- Always set `--served-model-name` explicitly — never rely on defaults
- When swapping models, comment out the old service, add the new one — never delete
- Validate compose YAML after edits: `docker compose -f docker-compose.yml config`
- Test the endpoint after changes: `curl http://localhost:8000/v1/models`

### vLLM Known Pitfalls
- `--reasoning-parser` puts thinking in `message.reasoning` not `message.reasoning_content`
- Stock vLLM images crash on Blackwell (CUTLASS error) — use spark-vllm-docker (`vllm-node-tf5`)
- MTP needs `--speculative-config` with correct method name (`mtp`, `qwen3_next_mtp`, etc.)
- `--gpu-memory-utilization` caps total reserved memory, affects concurrent sessions
- Each vLLM instance reserves memory upfront — can't run 2 instances on 1 GPU
- Container must be force-recreated after config changes: `docker compose up -d --force-recreate`

### New Model Testing
1. Add definition to `llama-swap/config.yaml`
2. Add to a test group (e.g., `mtp-test`)
3. Restart llama-swap
4. Test with: `curl -X POST http://localhost:8088/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"<name>","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'`
5. If it fails: remove from group, comment out definition, note in CHANGELOG

## Benchmark Notes (tok/s)

### Qwen3.6 27B (llama.cpp, MTP γ=2)
| Quant | Size | Speed | Notes |
|---|---|---|---|
| UD-Q3_K_XL | 14 GB | **31 tok/s** | Best speed/quality balance |
| UD-Q2_K_XL | 12 GB | 30 tok/s | Fastest but 2-bit lossy |
| Q4_K_M | 16 GB | 28 tok/s | Baseline |
| IQ4_NL | 16 GB | 26 tok/s | Same size as Q4, slower |
| UD-Q4_K_XL | 17 GB | 21 tok/s | Highest quality, slowest |
| NVFP4 (vLLM) | 25 GB | 17 tok/s | Heaviest, slowest — skip |
| PRISM PRO DQ | 13 GB | 15 tok/s | llama.cpp baseline |

### Gemma4 26B
| Engine | Quant | Context | Speed | Notes |
|---|---|---|---|---|
| **vLLM** | FP8 + MTP γ=1 | 256k | **50 tok/s** | enforce-eager (no CUDA graphs) |
| **vLLM** | NVFP4 + Marlin | 128k | 72-75 tok/s | CUDA graphs work, quality issues |
| llm.cpp | QAT Q4 + MTP γ=1 | 128k | ~19 tok/s | CUDA graphs work |

### Gemma4 12B
| Engine | Variant | Context | Speed |
|---|---|---|---|
| llm.cpp | QAT + TurboQuant | 256k | **13 tok/s** | With vLLM loaded concurrently |
| llm.cpp | Agentic v2 Q4 | 128k | ~15 tok/s | Fine-tuned for agentic tasks |

### DiffusionGemma 26B NVFP4 (vLLM v0.22.1)
| Setup | Speed | Notes |
|---|---|---|
| Single request, long output | **127-135 tok/s** | 256-token canvas filled |
| tool-eval-bench score | **85/100** | 53/69 passed |
| CUDA graphs | ✅ | VLLM_USE_V2_MODEL_RUNNER=1, TRITON_ATTN |

### Tool calling quality (tool-eval-bench)
| Model | Score | Rating |
|---|---|---|
| DiffusionGemma 26B NVFP4 | **85/100** | ★★★★ Good |
| FP8 26B (June 14 baseline) | **~91/100** | ★★★★ |

> Speed measured with minimal prompt ("hi"), 100 output tokens, all models loaded simultaneously unless noted.
> vLLM speeds with enforce-eager (CUDA graphs disabled on Blackwell SM121 for standard models).

### Key Files
| File | Purpose |
|---|---|
| `llama-swap/config.yaml` | Model definitions and groups — **most important file** |
| `README.md` | Documentation |
| `CHANGELOG.md` | Change history |
| `docker-compose.yml` | Service orchestration |
| `AGENTS.md` | This file — project rules |
| `PI.md` | Project overview for pi |
