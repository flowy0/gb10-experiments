# vLLM Reference (HISTORICAL — not currently used)

> **vLLM is NOT used on this box.** The main model runs on SGLang. Stock vLLM caused two
> independent GPU-driver OOMs (`NV_ERR_NO_MEMORY`) on 2026-08-17 at the recipe's gpu-memory-utilization 0.85
> (FP8 @ c16, NVFP4 @ gates) — see the CHANGELOG. The AEON vLLM service (Qwen3.6-35B-A3B) is retired
> (commented in docker-compose.yml, never deleted). This page keeps the knowledge for reference only.
> **Do not resurrect vLLM without re-qualifying it on this hardware.**

## Naming convention (vLLM era)

- Model ID format: `unsloth-{family}-{arch}-{quant}-mtp-{ctx}-{mode}`
- Compose service format: `vllm-{family}`
- Always set `--served-model-name` explicitly — never rely on defaults.
- When swapping models, comment out the old service, add the new one — never delete.
- Validate: `docker compose -f docker-compose.yml config`. Test: `curl http://localhost:8888/v1/models` (port 8000 in the vLLM era).

## Known pitfalls (vLLM era)

- `--reasoning-parser` puts thinking in `message.reasoning`, not `message.reasoning_content`.
- Stock vLLM images crash on Blackwell (CUTLASS error) — the AEON fork (`spark-vllm-docker`/`vllm-node-tf5`) was the workaround. AEON was an independently maintained fork of vLLM tuned for GB10/SM121.
- MTP needs `--speculative-config` with the correct method name (`mtp`, `qwen3_next_mtp`, etc.).
- Qwen3.6 NVFP4 had built-in MTP — no separate draft model needed.
- `--gpu-memory-utilization` caps reserved memory and affects concurrent sessions; each instance reserves upfront — two instances cannot share one GPU.
- Force-recreate after config changes: `docker compose up -d --force-recreate`.
- Tool parsers (v0.23.1rc1.dev309+): `qwen3_coder`, `qwen3_xml` via `--tool-call-parser`.
- V2 model runner (`VLLM_USE_V2_MODEL_RUNNER=1`) improved DiffusionGemma only.

## Memory numbers (vLLM era — reference only)

Reserve was `gpu-memory-utilization 0.35` ≈ 46 GB (AEON at 0.45 ≈ 53–58 GB). The old guidance:

| Scenario (vLLM @ 0.35 = 46 GB) | Total | Free |
|---|---|---|
| Hermes only | 46 GB | 85 GB ✅ |
| + one llama.cpp model | 56–79 GB | 52–75 GB ✅ |
| + two llama.cpp models | 79–112 GB | 19–52 GB ⚠️ |
| + three or more | 112+ GB | ❌ crash risk |

These are superseded by the SGLang-era numbers in [crash-avoidance.md](crash-avoidance.md).

## Failure history (why it was retired)

- **2026-08-11:** AEON DFlash spec-decode deadlock — 38h outage, zero completions. DFlash disabled across the stack.
- **2026-08-17:** stock vLLM (v0.27.1-aarch64) driver OOMs — FP8 + DSpark k7 at gmu 0.85 crashed at c16; NVFP4 at gmu 0.85 crashed during gates. Session C (candidate C) disqualified.
- The r0b0tlab tuned-vLLM variant (custom source-built v0.27.2rc0-sm121 wheel + bespoke NVFP4 checkpoint) was scored too risky to adopt (1-day-old build, publication bugs).

## Metrics (not scrapeable now)

`vllm:spec_decode_num_draft_tokens_total`, `vllm:spec_decode_num_accepted_tokens_total`, `vllm:num_requests_running`, `vllm:num_requests_waiting`.
