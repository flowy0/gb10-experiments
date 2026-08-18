# /opt/atom — Local AI Stack

## Critical Rules

### Config File Integrity
- **Never delete model definitions** in `llama-swap/config.yaml` — comment them out instead with `# `
- Always validate YAML after edits: `python3 -c "import yaml; yaml.safe_load(open('llama-swap/config.yaml'))"`
- Restart llama-swap after config changes: `docker compose restart llama-swap`
- Use `sed -i` for group member changes, not whole-file Python scripts
- When adding entries near existing ones, use exact text match, not line numbers
### YAML Indentation by File

#### `docker-compose.yml`
| Element | Indent | Column | Example |
|---|---|---|---|
| Service key | 6 spaces | **7** | `      sglang-qwen38:` |
| Properties (`image:`, `runtime:`, `ports:`, `container_name:`) | 8 spaces | **9** | `        container_name:` |
| Nested items (`- "8888:8888"`, `- /model`) | 12 spaces | **13** | `            - "8888:8888"` |
| `command:` entries | 12 spaces | **13** | `            - /model` |
| `environment:` vars | 12 spaces | **13** | `            - VLLM_USE=0` |
| Comment `#` + proper indent | 4+ spaces | varies | `    # commented service` |

#### `llama-swap/config.yaml`
| Element | Indent | Example |
|---|---|---|
| Top-level keys (`models:`, `groups:`) | 0 spaces | `models:` |
| Model keys | 4 spaces | `    unsloth-qwen36-27b-mtp2:` |
| Model properties (`name:`, `ttl:`, `cmd:`) | 8 spaces | `        name: "My Model"` |
| Block scalar `cmd:` content | 12 spaces | `            docker run --rm \` |
| Groups (`code:`, `research:`) | 4 spaces | `    code:` |
| Group properties (`swap:`, `exclusive:`) | 8 spaces | `        swap: true` |
| Group members | 12 spaces | `            - unsloth-qwen36-27b:` |

#### `litellm/config.yaml`
| Element | Indent | Example |
|---|---|---|
| `model_list:` | 0 spaces | `model_list:` |
| Model entries (`- model_name:`) | 2 spaces | `  - model_name:` |
| `litellm_params:` | 4 spaces | `    litellm_params:` |
| Sub-properties (`model:`, `api_base:`) | 6 spaces | `      model: openai/...` |
| `api_key:` | 6 spaces | `      api_key: dummy` |

### Git Workflow
- Always commit and push after config changes: `git add -A && git commit -m "message" && git push`
- Check `git diff --stat` before committing to verify no unintended changes
- If a model definition gets corrupted, restore with `git checkout HEAD -- llama-swap/config.yaml`
- **Update `CHANGELOG.md`** for every change — new models, config changes, benchmarks, doc updates

### Model Management
- **2026-08-17 migration:** MAIN MODEL is now `radixark-qwen38-27b-nvfp4-dspark-262k-think` — Qwen3.8-27B (RadixArk NVFP4) served by SGLang on port 8888 (mem-fraction 0.50 + 100g docker caps — the GB10-safe config per hasso5703; >0.50 risks hard freeze from untracked flashinfer/autotuner allocations). Exposed via litellm (4000). aeon-qwen36-35b retired. **OOM hardening done 2026-08-17:** old large llama-swap models commented out (qwen3.6 27B/35B, qwen3-coder, ornith-35B, gemma4-31B, 26B DFlash) — do NOT re-enable without re-testing memory co-residency with the SGLang main model. See docs/QWEN38_RESEARCH.md + docs/QWEN38_TESTPLAN.md.
- **SGLang operational rules:** /v1/models answers before engine ready — stall monitor uses a generation probe; graceful `docker compose restart` recovers, SIGKILL/manual `docker kill` does NOT auto-restart (docker semantics). DSpark (default) beats MTP on math/eval; MTP ~20% faster on fresh codegen (one-flag switch).
- **Main model request rules (radixark-qwen38-27b-nvfp4-dspark-262k-think):**
  - Thinking is ON by default at `xhigh` effort. `max_tokens` < ~500 + thinking ON returns EMPTY content (all budget spent reasoning). Budget ≥1000–2000, or set `reasoning_effort: low|medium|xhigh`, or cap with SGLang's `max_reasoning_tokens`. Recommended: agents 4096 (xhigh, max_reasoning_tokens 2048), chat 1024 (low), long-form 8192–16384.
  - Vision is native (Qwen3.8-27B is a VLM). Vision works WITH thinking ON. Image tokens are input-side. The vision 12B aux is redundant.
  - Tool calling: native OpenAI `role:tool` semantics (qwen3_coder parser) — drop-in for agents. (llama.cpp/qwen38-test entries need the `<tool_response>` user-message protocol instead.)
  - Concurrency: **4 running requests max** (scheduler + DSpark mamba pool 48 slots = 12/request). 5th+ requests queue. KV pool = 637,649 tokens → 2 full-262K sessions. To raise: `--max-mamba-cache-size 96 --max-running-requests 8` (~6.4 GB more, still inside 0.50 envelope).
  - Co-residency: **one** large llama.cpp model fits (91/121 GB used, ~30 GB free). Load big models only when SGLang is idle (past the boot autotuner window). NV_ERR_NO_MEMORY transients may appear during co-load (recovered 2026-08-17 — see CHANGELOG). Keep total host usage < ~110 GB.
  - **vLLM is disqualified on this box — do NOT resurrect.** Two independent NV_ERR_NO_MEMORY driver OOMs at the recipe's gmu 0.85 (FP8 @ c16, NVFP4 @ gates). Confirms the standing "stock vLLM crashes on Blackwell" rule.
  - Benchmark harness exists for future tests (identical methodology): `scripts/bench-qwen38.py`, `scripts/qwen38-gates.sh`, `scripts/qwen38-niah.py`, `scripts/qwen38-soak.sh`. Docs: docs/QWEN38_RESEARCH.md, docs/QWEN38_TESTPLAN.md, docs/qwen38-test-runs/FLIP-WINNER.md.
- **Naming convention:** Use the HuggingFace repo owner as the model ID prefix.
  - `radixark-` for RadixArk checkpoints (Qwen3.8 NVFP4 — current main)
  - `unsloth-` for Unsloth models (Gemma4, Qwen3.6)
  - `deepreinforce-` for DeepReinforce models (Ornith)
  - `s-batman-` for s-batman models
  - `anbeeld-` for Anbeeld models (GGUF conversions)
  - Never use `unsloth-` prefix for models from other providers.
- Fully on llama-swap (no vLLM):

| Group | Model | Context | TTL | Purpose |
|---|---|---|---|---|
| **hermes** | (retired — main model now SGLang: radixark-qwen38-27b) | — | — | — |
| **code** | (commented 2026-08-17 — old Qwen3.6/Ornith members removed) | — | — | — |
| **aux** | 12B QAT + TQ | 64k | 1h | Compression, web, titles, search (vision now on main model) |
| **subagent** | 35B IQ4 MTP | 64k | 30min | Quick sub-tasks |
| **research** | 26B QAT MTP γ=2 | 262k | 1h | Fallback — verified loads alongside SGLang main (~30 GB headroom) |

- Models load on first request per group
- Co-residency with SGLang main: **one** large llama.cpp model fits (91/121 GB used); a second would cross the ~110 GB danger line (NV_ERR pressure seen 2026-08-17)

### vLLM Naming Convention
- Model ID format: `unsloth-{family}-{arch}-{quant}-mtp-{ctx}-{mode}`
  - Example: `unsloth-qwen36-35b-a3b-fp8-256k-think-mtp`
- Compose service format: `vllm-{family}` (e.g., `vllm-gemma4`, `vllm-qwen36`)
- Always set `--served-model-name` explicitly — never rely on defaults
- When swapping models, comment out the old service, add the new one — never delete
- Validate compose YAML after edits: `docker compose -f docker-compose.yml config`
- Test the endpoint after changes: `curl http://localhost:8888/v1/models`
- Ports: 8888 (SGLang main), 8088 (llama-swap), 4000 (litellm), 8000 (freed — AEON retired)

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

### Monitoring
- **Prometheus** (port 9090) — scrapes vLLM, llama-swap, self. No auth.
- **Grafana** (port 3001) — login required. Service account key in `.env` as `GRAFANA_SA_KEY`.
- **Dashboard management:** Use `POST /api/dashboards/db` with `"overwrite": true` to create/update.
  To update an existing dashboard, first get its UID via `GET /api/search`, then `PUT /api/dashboards/uid/<uid>`.
- **Available vLLM metrics:** `vllm:spec_decode_num_draft_tokens_total`, `vllm:spec_decode_num_accepted_tokens_total`,
  `vllm:num_requests_running`, `vllm:num_requests_waiting`
- **Available llama-swap metrics:** `llamaswap_memory_used_bytes`, `llamaswap_memory_free_bytes`,
  `llamaswap_cpu_util_percent` (per core), `llamaswap_load_average`

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
