# /opt/atom — Local AI Stack

## Critical Rules

### Config File Integrity
- **Never delete model definitions** in `llama-swap/config.yaml` — comment them out instead with `# `
- Always validate YAML after edits: `python3 -c "import yaml; yaml.safe_load(open('llama-swap/config.yaml'))"`
- Restart llama-swap after config changes: `docker compose restart llama-swap`
- Use `sed -i` for group member changes, not whole-file Python scripts
- When adding entries near existing ones, use exact text match, not line numbers
- **docker-compose.yml indent rules:**
  - **Service key:** column **7** (6 spaces), e.g. `      aeon-qwen36-35b:`
  - **`container_name:`:** column **9** (8 spaces), same as other properties
  - **Properties:** 8 spaces indent (`image:`, `runtime:`, `ports:`, etc.)
  - **Nested items:** 12 spaces indent (`- "8000:8000"`, `- /model`, etc.)
  - **Comment marker `#`** takes column 1, then add the indent

### Git Workflow
- Always commit and push after config changes: `git add -A && git commit -m "message" && git push`
- Check `git diff --stat` before committing to verify no unintended changes
- If a model definition gets corrupted, restore with `git checkout HEAD -- llama-swap/config.yaml`
- **Update `CHANGELOG.md`** for every change — new models, config changes, benchmarks, doc updates

### Model Management
- **Naming convention:** Use the HuggingFace repo owner as the model ID prefix.
  - `unsloth-` for Unsloth models (Gemma4, Qwen3.6)
  - `deepreinforce-` for DeepReinforce models (Ornith)
  - `s-batman-` for s-batman models
  - `anbeeld-` for Anbeeld models (GGUF conversions)
  - Never use `unsloth-` prefix for models from other providers.
- Fully on llama-swap (no vLLM):

| Group | Model | Context | TTL | Purpose |
|---|---|---|---|---|
| **hermes** | 26B QAT MTP γ=2 | 128k | 24h | Main agent |
| **code** | Ornith-1.0-35B MoE Q4_K_M | 64k | 24h | Coding agent (100/100 tool-eval) |
| **aux** | 12B QAT + TQ | 64k | 1h | Compression, web, titles, search, vision |
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

### Avoiding Crashes (OOM & Cascade Failure)

#### Cascade Failure Pattern
GPU OOM doesn't just kill a container — it can **lock up the entire system.**

1. GPU runs out of memory → NVIDIA UVM tries swapping GPU memory to system RAM
2. System RAM fills up → journald/dockerd/sshd all stall
3. llama-server processes block on NVIDIA driver locks (122s+)
4. SSH becomes unresponsive → hard reboot required

#### Signs of Cascade
- `NVRM: Xid ... Graphics Exception` in `dmesg` (GPU hardware error)
- `NV_ERR_NO_MEMORY` in kernel logs
- `Under memory pressure, flushing caches` in journald
- `task:llama-server blocked for more than 122 seconds`
- SSH connection drops despite machine being powered on

#### Prevention
- **vLLM at 0.35 utilization** (~46 GB) — don't increase this
- **Load one llama.cpp model at a time** — let it cold start (~5-30s) before requesting another
- **Don't run tool-eval-bench with multiple models loaded** — it makes concurrent requests
- **If system feels sluggish, stop unused containers immediately:**
  ```bash
  docker ps --filter name=ls- --format '{{.Names}}' | xargs docker rm -f
  ```
- **GPU health monitor**: `/opt/atom/scripts/gpu-health.sh` checks for Xid errors

#### If Locked Out
- Hard power cycle (hold power button)
- After reboot, check `journalctl -k | grep NVRM` for Xid errors
- Don't restart the same workload — the GPU driver may need a cold boot

#### Memory Scenarios (vLLM @ 0.35 = ~46 GB reserved)

| Scenario | Total | Free |
|---|---|---|
| Hermes only | 46 GB | **85 GB** ✅ |
| + one llama.cpp model | 56-79 GB | **52-75 GB** ✅ |
| + two llama.cpp models | 79-112 GB | **19-52 GB** ⚠️ |
| + three or more | 112+ GB | ❌ crash risk |

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

### KV Cache Convention
- Always set explicit `--cache-type-k q8_0 --cache-type-v q8_0` on non-TurboQuant models.
- Without explicit KV type, llama.cpp defaults to **f16 (2 bytes)**, doubling memory.
- TurboQuant models use `turbo4` (4-bit = 0.5 bytes) — cheapest option.

### Speculative Decoding
- `--spec-type draft-mtp` with `--spec-draft-n-max 2` is the default for models with MTP heads.
- DFlash (`--spec-type draft-dflash`) requires a separate DFlash draft GGUF file.
- BeeLlama.cpp (Anbeeld fork, 718 stars) combines DFlash + TurboQuant in one build.
- Current DFlash status: Docker images don't support `dflash-draft` architecture yet.
- **MTP + mmproj compatible** — tested on 12B QAT MTP: draft acceptance 63% (text) and 53% (image). No need to split entries.

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
