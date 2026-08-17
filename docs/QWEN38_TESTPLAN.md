# Qwen3.8-27B — Candidate Test Plan

> **STATUS: COMPLETE (2026-08-17).** Winner: SGLang B2 (DSpark @ safe 0.50 config) — flipped as `radixark-qwen38-27b-nvfp4-dspark-262k-think`. vLLM disqualified on stability; llama.cpp strong runner-up. Final run cards: [qwen38-test-runs/FLIP-WINNER.md](qwen38-test-runs/FLIP-WINNER.md)

> Purpose: empirically decide between the deployment options for making Qwen3.8-27B the sole main model on this DGX Spark.
> Companion doc: [QWEN38_RESEARCH.md](./QWEN38_RESEARCH.md) (background, published numbers, methodology traps).

## Candidates

| ID | Engine | Checkpoint | Size | Where it runs |
|---|---|---|---|---|
| **A** | llama.cpp (existing stack, pin bumped) | AtomicChat `AD-Q5_K_M-Q4_K_M` (KL 0.00730) + `mmproj-F16` | ~19.6 GB | llama-swap/llama.cpp, same as qwen3.6 today |
| **B** | SGLang (new engine) | RadixArk `Qwen3.8-27B-NVFP4` | ~18.2 GB (+22 GB download) | standalone container, port 8888 |
| C* | vLLM stock (optional reference) | `Qwen/Qwen3.8-27B-FP8` + DSpark k=7 | 28.5 GiB | 0xBakeer recipe, port 8002 |

\* Candidate C is optional — the article's 75/256 recipe and the correctness baseline (FP8 = output-preserving). Run it only if you want the third data point.

## 0. Decision criteria (what "better" means here)

1. **Correctness** — arith, tools, thinking, vision, long-context retrieval all pass (non-negotiable bar).
2. **Stability** — no hangs, bounded memory, fast recovery, no cascade risk. Weighted highest given the box's history.
3. **Speed** — solo decode (agent latency) and c8/c16 aggregate (fleet/parallel tool calls), TTFT on long prompts.
4. **Context** — 262K native actually usable (NIAH), not just accepted by the server.
5. **Integration cost** — changes to compose/llama-swap/litellm/monitoring, rollback effort.

Minimum bar: any candidate that fails a core correctness gate with no config fix available is **disqualified**.

## ⚠️ Execution model — one candidate owns the box at a time

Only one engine can be resident (A ≈ 51 GB @262K, B ≈ 109 GB @0.85, C ≈ 90+ GB; aeon at 53 GB cannot coexist with any). **Each candidate therefore gets one contiguous session** — boot it, run *everything* (correctness → benchmark → long-context → recovery smoke), tear it down. The box is never loaded twice for the same candidate.

```
Stage 0  prep (downloads, baseline)                    — box free, aeon may stay up
Stage 1  Session A: llama.cpp + GGUF   (boot → G1–G9 → BENCH-A → NIAH → recovery → teardown)
Stage 2  Session B: SGLang + NVFP4     (boot → G1–G9 → BENCH-B → NIAH → recovery → teardown)
Stage 3  Session C: vLLM + FP8         (optional, same shape)
Stage 4  Winner: soak + integration    (winner stays loaded)
Stage 5  Decision matrix
```

Each session ≈ 2.5–3.5 h. Total wall ≈ 1 day (A+B) / 1.5 days (A+B+C), downloads parallelized overnight.

## 1. Methodology rules (violating these invalidates the comparison)

Applied identically in every session:

1. **Decode throughput measured on ≥400 output tokens.** Short outputs + prefill drag makes numbers incomparable (r0b0tlab's 1024-in/256-out ladder vs 0xBakeer's 400–3000-token runs differ by ~3×).
2. **Thinking OFF for all throughput numbers** (`temperature 0`, `enable_thinking: false`). Qwen3.8 defaults thinking ON at `xhigh` effort — a benchmark that forgets this measures nothing.
3. **Thinking ON tested separately** — verify `reasoning_content` present and measure the tok/s cost (expect a real hit).
4. **Concurrency ladder:** c1 / c4 / c8 / c16, same prompts, distinct payloads (avoid identical-prompt cache effects). Aggregate AND per-stream tok/s.
5. **Cold vs warm prefix:** agent workloads reuse a long system prompt — measure TTFT cold vs warm (prefix caching) on a ~19K shared prefix.
6. **Same gates, same prompts, same scripts in every session.** Do not mix published numbers with your own.
7. **Record config with every run** (engine, image, spec-decode, context, kv cache, concurrency, output len, thinking). See run-card template in §6.
8. **Session hygiene:** before booting a candidate, `docker ps --filter name=ls- | xargs docker rm -f`, confirm `MemAvailable ≥ 20 GB` and `journalctl -k | grep -c NVRM/Xid == 0`.

## 2. Stage 0 — prep (≈30 min, downloads overnight)

```bash
# 1. Baseline snapshot
free -g; cat /proc/meminfo | grep -E 'MemTotal|MemAvailable'
docker stats --no-stream
journalctl -k --since today | grep -cE 'NVRM|Xid'   # must be 0

# 2. Downloads (parallel, background, overnight):
# A:  AtomicChat AD-Q5_K_M-Q4_K_M (18.6 GB) + mmproj-F16 (0.93 GB) → /opt/atom/models/atomicchat-qwen38/
#     current server-cuda13 image (pin bump from v9843/2026-06-30)
# B:  docker pull lmsysorg/sglang:qwen38-27b  (RadixArk weights land in HF cache on first boot)
# C:  docker pull vllm/vllm-openai:v0.27.1-aarch64 (+ Doopeworld/Qwen3.8-27B-DSpark-vLLM drafter)

# 3. Ports (avoid prod): A → 8090 standalone · B → 8888 · C → 8002
```

**Go/no-go:** downloads complete, zero Xid lines, MemAvailable ≥ 20 GB.

---

## 3. Stage 1 — Session A: llama.cpp + AtomicChat GGUF (≈2.5–3 h)

### 1a. Boot
Standalone on 8090 with the **bumped** image pin, `-c 262144 --cache-type-k q8_0 --cache-type-v q8_0 -ngl 99 --spec-type draft-mtp --spec-draft-n-max 2 --mmproj mmproj-F16.gguf`.
Record: cold-start time, peak RSS at idle.

### 1b. Correctness gates G1–G9

| # | Gate | Prompt | Pass |
|---|---|---|---|
| G1 | Arith (think off) | `19*23. Answer with only the number.` | exactly `437` |
| G2 | Arith (think on) | same, `chat_template_kwargs: {"enable_thinking": true}` | `reasoning_content` present AND final `437` |
| G3 | Exact string | `Repeat the word BANANA.` | `BANANA` verbatim |
| G4 | Code shape | `Write a python function fib(n) with docstring.` | fenced code block, runs correctly |
| G5 | Tool call | `What's the weather in Tokyo?` + `tools: [{get_weather(city)}]` | `tool_calls` w/ `get_weather` + `"Tokyo"` |
| G6 | Multi-turn tool flow | G5 response fed back with tool result → final answer | completes without template corruption |
| G7 | Vision | AtomicChat `demo.jpg`, transcribe exactly | exact transcription |
| G8 | Reasoning effort | `reasoning_effort: low` vs `xhigh` on a hard problem | token counts differ measurably; both correct |
| G9 | Sampling defaults | thinking on, no overrides → temp 1.0/top_p 0.95 observed | non-degenerate output |

> **This session decides the pin bump.** G2/G8 require `chat_template_kwargs` support — if the bumped build lacks it, fall back to a `--jinja` template override and note it in the run card. If neither works, thinking control is broken → score A down on integration, do not fail outright (thinking can be forced per-request via template).

### 1c. BENCH-A (benchmark, while loaded)

Same script as all sessions (`scripts/bench-qwen38.py` — see §7). Thinking off, temp 0, fixed seed, distinct prompts.

| Sub-test | Method | Records |
|---|---|---|
| Solo decode | 512-in / 1024-out ×3 (median); 512-in / 256-out ×5 (median, prefill-drag control) | tok/s both |
| MTP sweep | spec OFF vs `draft-mtp n-max 2` vs `n-max 5` | tok/s + acceptance (spec counters in server log) |
| Ladder | c1/c4/c8/c16, 8 distinct prompts × 1500-out | aggregate + per-stream tok/s, p95 TTFT, errors |
| Prefix | 19K shared prefix, cold vs warm TTFT | speedup |
| Prefill | unique 8K/32K/100K prompts, `max_tokens:1` | TTFT |

Expectation check: solo ≈ 30–40 tok/s (273 GB/s ÷ 18.6 GB × ~2× MTP). Mismatch >2× → investigate before continuing.

### 1d. Long context — NIAH @ 262K
Needle at ≈8K / 32K / 131K / 247K, 3 needles each = 12 probes. Pass ≥ 11/12.
(Memory check while here: weights 18.6 + KV ~32 GB fp8 ≈ 51 GB → confirm MemAvailable ≥ 15 GB after a full-262K prefill.)

### 1e. Recovery smoke
`docker kill -9` the server mid-generation → next request clean? Time to first successful response (expect seconds via llama-swap respawn, or manual restart).

### 1f. Teardown
Stop server, record final memory, `journalctl -k | grep -cE 'NVRM|Xid'` must be 0.

---

## 4. Stage 2 — Session B: SGLang + RadixArk NVFP4 (≈3–3.5 h)

### 2a. Boot
Compose service (bridge net, port 8888, HF-cache volume) at **`--mem-fraction-static 0.85`** (0.95 is scored as a stability negative — see §5), recipe flags verbatim (`flashinfer`, `fp8_e4m3`, EAGLE 3/1/4, GDN pool 80 slots, `--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder`, `--sampling-defaults model`).
Record: cold-start time (expect minutes), `grep context_len .sglang.log` → 262144, `max_running_requests` → 10.

### 2b. Correctness gates G1–G9 — identical prompts
- G2/G8: verify `reasoning_content` key name matches what pi/litellm expect (SGLang uses `reasoning_content` — same as current stack)
- G5/G6: `qwen3_coder` parser path
- G7: vision served natively (no mmproj needed)

### 2c. BENCH-B (identical script)
Solo, MTP acceptance (from SGLang `/metrics` `spec_*` counters), ladder c1/c4/c8/**c16**, prefix (RadixAttention — expect big warm win), prefill.
Expectation: solo ≈ 17–21 tok/s (their published MTP numbers). Aggregate should keep rising to c16 (this is B's strongest axis — if it stalls <150 @ c16, note it).

### 2d. Long context — NIAH @ 262K (12 probes, ≥11/12)
Optional: 1M YaRN spot check (2 needles) — recipe-validated factors 2.0/4.0.

### 2e. Recovery smoke
`docker kill -9` → `restart: unless-stopped` respawn; time to `/health` 200 (expect minutes — Python cold start). This number goes in the stability column.

### 2f. Teardown — same hygiene as 1f.

---

## 5. Stage 3 — Session C (optional): vLLM + FP8 + DSpark (≈2.5 h)

Same shape as B: 0xBakeer `serve.sh` (port 8002, `--enable-prefix-caching`, DSpark k=7, 262K, `VLLM_MARLIN_USE_ATOMIC_ADD` not needed — FP8 only). G1–G9 (G7 via `--limit-mm-per-prompt.image 2`), BENCH-C, NIAH, recovery. Expectation: solo ≈ 47 tok/s (FP8 DSpark k7), the article's 256 @ c16.

**Skip if time-boxed** — it's the reference/baseline, not a deployment candidate for your stack (stock vLLM on this box has a documented Blackwell history; this recipe is the workaround).

---

## 6. Stage 4 — Winner: stability soak + integration (≈3 h)

Only after Sessions A/B/C are scored and a winner is chosen.

### 6a. Soak (45 min)
Mixed traffic (chat + tool + vision + one long-gen) against the winner:
- RSS trend flat after warmup (leak check)
- 100% completion success; any hang > 60 s = fail
- `docker stats` CPU-pinned-with-zero-completions = the DFlash deadlock signature → fail
- Host: `MemAvailable ≥ 15 GB` throughout; no swap growth > 1 GB; zero `NVRM|Xid|task:blocked` in `journalctl -k`

### 6b. OOM probe
Attempt to load a second model on top (e.g., the embed group). Must be refused predictably — no UVM swap, no cascade. Document what happens.

### 6c. Integration drill
1. **A:** llama-swap `qwen38` test-group entry (bumped pin, mmproj) → verify via `:8088/v1/chat/completions` and a litellm route
2. **B:** compose service + litellm entry + prometheus `sglang` job + stall-monitor repoint (generation probe, not just `/v1/models`)
3. Vision-path swap: aux consumer → new model (retire `unsloth-gemma4-12b-qat-256k-mtp` route)
4. Client swap: pi/agent config, open-webui `OPENAI_MODEL_LIST`, scripts referencing `aeon-qwen36-35b-128k-think` → new name
5. **Rollback drill FIRST:** comment new entry, uncomment aeon, `docker compose up -d --force-recreate` → aeon answers within 5 min. Then do the real flip.

### 6d. Run card template (one per gate/bench per candidate)

```
candidate: A | date: | image/digest: | checkpoint: | ctx: 262144 | kv: q8_0
spec: draft-mtp n-max 2 | thinking: off | temp: 0 | concurrency: c4 | output_len: 1024
gate: G5 tool-call | result: PASS | tok/s: | ttft: | peak rss: | notes:
```

## 7. Decision matrix

| Criterion | Weight | A (llama.cpp GGUF) | B (SGLang NVFP4) | C (vLLM FP8) |
|---|---|---|---|---|
| Correctness gates (9/9?) | 25% | /9 | /9 | /9 |
| Stability (soak + recovery + envelope) | 30% | score 1–5 | score 1–5 | score 1–5 |
| Solo decode tok/s | 15% | | | |
| c16 aggregate tok/s | 10% | | | |
| 262K NIAH | 10% | /12 | /12 | /12 |
| Integration effort (1–5, 5=easy) | 10% | | | |
| **Weighted total** | | | | |

Decision rules:
- **Disqualify** any candidate failing G1–G6 or NIAH < 11/12 unless a documented config fix re-passes.
- **Tie-break on stability** (the box's documented failure mode).
- A vs B tie: prefer A (existing engine, seconds-cold-start, ~51 GB envelope) unless B's c16 aggregate is >2× and the fleet workload is real.

## 8. Checklist (printable)

- [ ] Baseline: zero Xid, MemAvailable ≥ 20 GB
- [ ] Downloads complete (A: GGUF+mmproj+image; B: image; C: image+drafter)
- [ ] **Session A:** boot → G1–G9 → BENCH-A → NIAH → recovery → teardown
- [ ] **Session B:** boot → G1–G9 → BENCH-B → NIAH → recovery → teardown
- [ ] (opt) **Session C:** same shape
- [ ] Decision matrix filled → winner
- [ ] Winner soak 45 min + OOM probe
- [ ] Integration drill + rollback drill (rollback first!)
- [ ] Client swap + monitoring repoint
- [ ] CHANGELOG updated, commit
