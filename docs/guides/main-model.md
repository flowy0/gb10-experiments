# Main Model — radixark-qwen38-27b-nvfp4-dflash2-262k-think

Qwen3.8-27B (RadixArk NVFP4) served by SGLang on port 8888, exposed via litellm on port 4000. Draft: DFlash2 (`z-lab/Qwen3.8-27B-DFlash2`). Image: `weschera/qwen38-27b-dflash2:2026-08-19`.

## Serving config (compose service `sglang-qwen38`)

- `--mem-fraction-static 0.50` — **the GB10-safe value.** SGLang's memory accounting misses 25–40 GB of transient allocations (flashinfer autotuner, cuda-graph capture) on unified memory; values above 0.50 risk a hard freeze (hasso5703 field report). Docker `--memory 100g --memory-swap 100g` caps the container as a safety net.
- `--speculative-algorithm DFLASH` + `--speculative-num-draft-tokens 8`, draft `z-lab/Qwen3.8-27B-DFlash2`
- `--max-running-requests 4`, `--max-mamba-cache-size 16` (= concurrency × 4 state slots)
- `--kv-cache-dtype fp8_e4m3`, `--mamba-ssm-dtype bfloat16`, `--mamba-radix-cache-strategy extra_buffer`, `--max-prefill-tokens 16384`
- `cpuset: "5-9,15-19"` (GB10 X5 cores; keeps scheduler/tokenizer off the efficiency cores)
- `--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder`, `--sampling-defaults model`
- Context: native 262,144 (YaRN > 262K not enabled; DFlash2 + YaRN is incompatible on this build)

## Request rules

- **Thinking is ON by default** at `xhigh` effort. `max_tokens` below ~500 with thinking ON returns EMPTY content (the whole budget goes to reasoning). Budget ≥1000–2000, or set `reasoning_effort: low|medium|xhigh`. Recommended: agents 4096, chat 1024 (`low`), long-form 8192–16384.
- **Vision is native** (the model is a VLM). Vision works with thinking ON. Image tokens are input-side. The vision 12B aux is redundant.
- **Tool calling** uses native OpenAI `role:tool` semantics (qwen3_coder parser) — drop-in for agents. (Only llama.cpp-based models need the `<tool_response>` user-message protocol — see llama-swap-models.md.)
- **litellm pass-through:** only `reasoning_effort` is allowed through litellm for this model (`allowed_openai_params`). Do NOT send `chat_template_kwargs` or `max_reasoning_tokens` through litellm — the OpenAI-SDK path rejects them.

## Concurrency & context capacity

- **4 running requests max** (scheduler + mamba pool 16 slots). The 5th+ request queues (FCFS) — it never fails, just waits.
- KV pool = 637,649 tokens → 2 full-262K sessions, or 4 sessions at ~100K each.
- To raise concurrency: `--max-mamba-cache-size` = concurrency × 4, plus `--max-running-requests` (costs ~6.4 GB per 4 slots, still inside the 0.50 envelope).

## Co-residency

- **One** large llama.cpp model fits alongside (91/121 GB used, ~30 GB free). A second large model crosses the ~110 GB danger line.
- Load big llama-swap models only when SGLang is idle (past the boot autotuner window). `NV_ERR_NO_MEMORY` transients may appear during co-load — they recover, but watch `journalctl -k`.
- 12B and smaller llama-swap models coexist freely.

## Operational rules (SGLang)

- **`/v1/models` is not a readiness signal** — it answers before the engine is ready. The stall monitor uses a generation probe instead. On manual checks, send a real `max_tokens:1`+ request and verify content.
- **Recovery:** graceful `docker compose restart sglang-qwen38` works (~3 min boot). SIGKILL / manual `docker kill` does NOT auto-restart (docker manual-stop semantics). Natural crashes DO auto-restart.
- **The stall monitor** targets this service by default (port 8888, model name above, generation probe).
- **Draft method switch:** DFlash2 is the default (promoted after soak PASS 200/200; beats MTP on code). MTP is a one-flag alternative (`--speculative-algorithm EAGLE --speculative-num-steps 3 --speculative-eagle-topk 1 --speculative-num-draft-tokens 4`) that measured ~20% faster on fresh codegen but ~40% slower on thinking-heavy chat; both need the weschera image variant for DFlash2 support.

## Testing harness

Identical methodology for any future model/checkpoint test:
- `scripts/bench-qwen38.py` (solo, short, ladder, prefix, prefill, think)
- `scripts/qwen38-gates.sh` (correctness G1–G9)
- `scripts/qwen38-niah.py` (needle probes @ 262K)
- `scripts/qwen38-soak.sh` (stability soak)
- `scripts/monitor-sglang-toks.sh` (continuous tok/s sampling)

Reference docs: `docs/QWEN38_RESEARCH.md`, `docs/QWEN38_TESTPLAN.md`, `docs/qwen38-test-runs/FLIP-WINNER.md`.
