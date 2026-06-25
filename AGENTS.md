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
- **Update `CHANGELOG.md`** for every change — new models, config changes, benchmarks, doc updates

### Model Management
- Fully on llama-swap (no vLLM):

| Group | Model | Context | TTL | Purpose |
|---|---|---|---|---|
| **hermes** | 26B QAT MTP γ=2 | 128k | 24h | Main agent |
| **code** | 27B UD-Q3 MTP γ=2 | 64k | 1h | Coding |
| **compression** | E4B QAT + TQ | 128k | 30min | Summaries |
| **aux** | 12B QAT + TQ | 64k | 1h | Web, titles, search, vision |
| **subagent** | 35B IQ4 MTP | 64k | 30min | Quick sub-tasks |
| **research** | 26B QAT MTP γ=2 | 64k | 1h | Fallback |

- Models load on first request per group
- Max simultaneous when all loaded: ~112 GB ✅ 19 GB free

### vLLM Naming Convention
- Model ID format: `unsloth-{family}-{arch}-{quant}-mtp-{ctx}-{mode}`
  - Example: `unsloth-qwen36-35b-a3b-fp8-256k-think-mtp`
- Compose service format: `vllm-{family}` (e.g., `vllm-gemma4`, `vllm-qwen36`)
- Always set `--served-model-name` explicitly — never rely on defaults
- When swapping models, comment out the old service, add the new one — never delete
- Validate compose YAML after edits: `docker compose -f docker-compose.yml config`
- Test the endpoint after changes: `curl http://localhost:8000/v1/models`
- Ports: 8000 (primary), 8001 (DiffusionGemma test), 8002 (Qwen NVFP4 test)

### vLLM Known Pitfalls
- `--reasoning-parser` puts thinking in `message.reasoning` not `message.reasoning_content`
- Stock vLLM images crash on Blackwell (CUTLASS error) — use spark-vllm-docker (`vllm-node-tf5`)
- Official `vllm/vllm-openai:gemma` image works for DiffusionGemma (different architecture)
- MTP needs `--speculative-config` with correct method name (`mtp`, `qwen3_next_mtp`, etc.)
- Qwen3.6 NVFP4 has built-in MTP — no separate draft model needed (`--speculative-config '{"method":"mtp","num_speculative_tokens":2}'`)
- `--gpu-memory-utilization` caps total reserved memory, affects concurrent sessions
- Each vLLM instance reserves memory upfront — can't run 2 instances on 1 GPU
- Container must be force-recreated after config changes: `docker compose up -d --force-recreate`
- New tool parsers (v0.23.1rc1.dev309+): `qwen3_coder`, `qwen3_xml` via `--tool-call-parser`
- The V2 model runner (`VLLM_USE_V2_MODEL_RUNNER=1`) improves performance on DiffusionGemma

### New Model Testing
1. Add definition to `llama-swap/config.yaml`
2. Add to a test group (e.g., `mtp-test`)
3. Restart llama-swap
4. Test with: `curl -X POST http://localhost:8088/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"<name>","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'`
5. If it fails: remove from group, comment out definition, note in CHANGELOG

### Benchmark Recording
- When testing a new model/quant, add a row to `docs/BENCHMARKS.md`.
- Format: model ID, engine, quant, context, tok/s, notes.
- Speed: measured with minimal prompt ("hi"), 100 output tokens, all models loaded.
- vLLM speeds use enforce-eager (CUDA graphs disabled on Blackwell for standard models).
- See `docs/BENCHMARKS.md` for full results table.

### Key Files
| File | Purpose |
|---|---|
| `llama-swap/config.yaml` | Model definitions and groups — **most important file** |
| `README.md` | Documentation |
| `CHANGELOG.md` | Change history |
| `docker-compose.yml` | Service orchestration |
| `AGENTS.md` | This file — project rules |
| `PI.md` | Project overview for pi |
| `docs/BENCHMARKS.md` | Benchmark results (tok/s, tool-eval scores) |
| `docs/CUDA_GRAPHS.md` | CUDA graphs explanation |
| `docs/QUICK_CMDS.md` | Common commands reference |
| `docs/VLLM.md` | vLLM build, setup, debugging history |
| `docs/HISTORICAL.md` | Previous stack configurations |
