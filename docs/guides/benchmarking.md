# Benchmarking

## Recording convention

- When testing a new model/quant, add a row to `docs/BENCHMARKS.md`:
  `model ID | engine | quant | context | tok/s | notes`
- Speed convention: measured with a minimal prompt ("hi"), 100 output tokens, all models loaded.
- Note vLLM-era records used `--enforce-eager` (CUDA graphs disabled on Blackwell) — historical, see vllm-reference.md.

## Harness (main-model comparisons — identical methodology required)

Use the same scripts and the same prompts for any comparison; do not mix your numbers with published ones.

- `scripts/bench-qwen38.py` — solo decode (512-in/1024-out ×3 median + 256-out prefill-drag control), concurrency ladder c1–c16, cold/warm 19K prefix, prefill TTFT 8K/32K/100K, thinking-on cost. Thinking OFF for throughput; `chat_template_kwargs` where supported.
- `scripts/qwen38-gates.sh` — correctness gates G1–G9 (arith think on/off, exact string, code, tool call, multi-turn, vision, reasoning effort, sampling). Same script, all engines.
- `scripts/qwen38-niah.py` — needle-in-a-haystack at 262K (12 probes: 3 needles × 4 positions). Pass = ≥11/12.
- `scripts/qwen38-soak.sh` — stability soak (default 45 min; env `BASE_URL`/`SOAK_MODEL` for test targets). Checks: every request completes, no hangs, memory flat, zero kernel errors.
- `scripts/monitor-sglang-toks.sh` — continuous tok/s sampling to `/tmp/sglang-toks.csv`.

## Methodology traps (learned — violating these invalidates results)

1. Decode throughput on ≥400 output tokens — short outputs are prefill-drag dominated.
2. Thinking OFF for throughput numbers (temp 0, `enable_thinking: false`). Qwen3.8 defaults thinking ON at xhigh — a benchmark that forgets this measures nothing.
3. Thinking ON tested separately (verify `reasoning_content` and measure the cost).
4. Distinct prompts per concurrency level (avoid prefix-cache effects on the ladder).
5. Cold vs warm prefix measured on a ~19K shared prefix (agent system prompts).
6. One candidate owns the box during its session; never compare across co-resident engines.
7. Draft acceptance (tokens/step) is the honest cross-drafter signal; published headline tok/s values often come from high-acceptance (edit-heavy or repetitive) prompts and do not transfer to fresh-codegen workloads.
8. Beware background downloads/IO during a run — page-cache pressure distorts memory-bound measurements (a 22 GB download contributed to a driver OOM during one ladder).

## Run cards

Per-session evidence (bench JSON, gates JSON, NIAH JSON, run cards) goes in `docs/qwen38-test-runs/` — git-ignored locally, summarized in the CHANGELOG. Key decision records: `docs/qwen38-test-runs/FLIP-WINNER.md` (Qwen3.8 flip), `DFLASH2-TEST.md`.
