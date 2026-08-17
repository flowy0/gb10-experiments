# Qwen3.8-27B — Candidate Test Plan

> Purpose: empirically decide between the deployment options for making Qwen3.8-27B the sole main model on this DGX Spark.
> Companion doc: [QWEN38_RESEARCH.md](./QWEN38_RESEARCH.md) (background, published numbers, methodology traps).

## Candidates

| ID | Engine | Checkpoint | Size | Where it runs |
|---|---|---|---|---|
| **A** | llama.cpp (existing stack, pin bumped) | AtomicChat `AD-Q5_K_M-Q4_K_M` (KL 0.00730) + `mmproj-F16` | ~19.6 GB | llama-swap/llama.cpp, same as qwen3.6 today |
| **B** | SGLang (new engine) | RadixArk `Qwen3.8-27B-NVFP4` | ~18.2 GB (+22 GB download) | standalone container, port 8888 |
| C* | vLLM stock (optional reference) | `Qwen/Qwen3.8-27B-FP8` + DSpark k=7 | 28.5 GiB | 0xBakeer recipe, port 8002 |

\* Candidate C is optional — it's the article's 75/256 recipe and the correctness baseline (FP8 = output-preserving). Run it only if you want the third data point.

## 0. Decision criteria (what "better" means here)

1. **Correctness** — arith, tools, thinking, vision, long-context retrieval all pass (non-negotiable bar).
2. **Stability** — no hangs, bounded memory, fast recovery, no cascade risk. Weighted highest given the box's history.
3. **Speed** — solo decode (agent latency) and c8/c16 aggregate (fleet/parallel tool calls), TTFT on long prompts.
4. **Context** — 262K native actually usable (NIAH), not just accepted by the server.
5. **Integration cost** — changes to compose/llama-swap/litellm/monitoring, rollback effort.

Minimum bar: any candidate that fails a core correctness gate with a config fix unavailable is **disqualified**.

## 1. Methodology rules (violating these invalidates the comparison)

Learned the hard way from the research — apply identically to every candidate:

1. **Decode throughput must be measured on ≥400 output tokens.** Short outputs + prefill drag makes numbers incomparable (r0b0tlab's 1024-in/256-out ladder vs 0xBakeer's 400–3000-token runs differ by ~3×).
2. **Thinking OFF for all throughput numbers** (`temperature 0`, `enable_thinking: false`). Qwen3.8 defaults thinking ON at `xhigh` effort — a benchmark that forgets this measures nothing.
3. **Thinking ON tested separately** — verify `reasoning_content` present and measure the tok/s cost (expect a real hit).
4. **Concurrency ladder:** c1 / c4 / c8 / c16, same prompts, distinct payloads (avoid identical-prompt cache effects). Aggregate AND per-stream tok/s.
5. **Cold vs warm prefix:** agent workloads reuse a long system prompt — measure TTFT cold vs warm (prefix caching) on a ~19K shared prefix.
6. **Same gates, same prompts, same scripts for all candidates.** Do not mix published numbers with your own.
7. **Record config with every run** (engine, image, spec-decode, context, kv cache, concurrency, output len, thinking). See the run-card template in §6.
8. **One candidate owns the box during its tests.** Stop aeon + llama.cpp models first (AGENTS.md: load one model at a time, never exceed the memory envelope).

## 2. Stage 0 — prep & baseline (≈30 min)

```bash
# 1. Free the box (accept main-model downtime during tests; production can stay up for Stage 1–2 *standalone* runs)
docker ps --filter name=ls- --format '{{.Names}}' | xargs -r docker rm -f
# keep aeon running during standalone correctness/speed stages; stop it before integration/soak

# 2. Baseline snapshot
free -g; cat /proc/meminfo | grep -E 'MemTotal|MemAvailable'
docker stats --no-stream
# record: baseline RSS, swap usage, loadavg, `journalctl -k --since today | grep -cE 'NVRM|Xid'`

# 3. Downloads (parallel, background):
# A:  AtomicChat AD-Q5_K_M-Q4_K_M (18.6 GB) + mmproj-F16 (0.93 GB) → /opt/atom/models/atomicchat-qwen38/
#     current server-cuda13 image (pin bump from v9843/2026-06-30)
# B:  docker pull lmsysorg/sglang:qwen38-27b  (+ RadixArk weights land in HF cache on first boot)
# C:  docker pull vllm/vllm-openai:v0.27.1-aarch64 (+ Doopeworld/Qwen3.8-27B-DSpark-vLLM drafter)

# 4. Test port allocation (avoid prod ports):
#    A → 8090 standalone (later: llama-swap member)
#    B → 8888 (per recipe)
#    C → 8002 (per recipe)
```

**Go/no-go:** baseline journald has zero NVRM/Xid lines and MemAvailable ≥ 20 GB before each candidate boots.

## 3. Stage 1 — correctness gates (identical for A, B, C; ≈45 min each)

All via OpenAI-compatible endpoint, `temperature 0`. Paste every response into the run card.

| # | Gate | Prompt | Pass |
|---|---|---|---|
| G1 | Arith (think off) | `19*23. Answer with only the number.` | exactly `437` |
| G2 | Arith (think on) | same, `chat_template_kwargs: {"enable_thinking": true}` | `reasoning_content` present AND final `437` |
| G3 | Exact string | `Repeat the word BANANA.` | `BANANA` verbatim |
| G4 | Code shape | `Write a python function fib(n) with docstring.` | fenced code block, runs correctly |
| G5 | Tool call | `What's the weather in Tokyo?` + `tools: [{get_weather(city)}]` | response contains `tool_calls` w/ `get_weather` + `"Tokyo"` |
| G6 | Multi-turn tool flow | G5 response fed back with tool result → final answer | completes without template corruption |
| G7 | Vision (A/B only; C optional) | image: AtomicChat `demo.jpg`, prompt: transcribe exactly | exact transcription (A needs `--mmproj`; B serves vision natively) |
| G8 | Reasoning effort | `reasoning_effort: low` vs `xhigh` on a hard problem | token counts differ measurably; both correct |
| G9 | Sampling defaults | thinking on, no overrides → temp 1.0/top_p 0.95 observed (per checkpoint card) | non-degenerate output |

**A-specific:** verify `chat_template_kwargs` (enable_thinking / reasoning_effort) works on the bumped llama.cpp build — if the June pin doesn't support it, that's the reason to bump, and this gate decides the pin. Fallback if unsupported: test with a `--jinja` template override.
**B-specific:** G5 uses `--tool-call-parser qwen3_coder` (already in recipe); verify `reasoning_content` key name matches what pi/litellm expect (SGLang: `reasoning_content`, same as current stack).

## 4. Stage 2 — performance (≈1.5 h per candidate)

Use one script for all three (`scripts/bench-qwen38.py`, to be written — or the inline curl pattern below). All runs: thinking off, temp 0, fixed seed, distinct prompts.

### 4a. Solo decode
- Input 512 tok, output 1024 tok → tok/s = output_tokens / wall (decode-dominated)
- Input 512 tok, output 256 tok → repeat 5×, report median (this is the number that will look "slow" — prefill drag, expected)
- MTP check: run same with spec decode ON vs OFF; record acceptance/tokens-per-pass from engine counters:
  - llama.cpp: `--spec-type draft-mtp --spec-draft-n-max 2` (stack default) and `5` (article: deeper draft wins); compare tok/s
  - SGLang: EAGLE 3/1/4 (recipe default) — acceptance from SGLang metrics `/metrics` (`sglang:spec_*`)
- Expectation vs published: A ≈ 30–40 tok/s (273 GB/s ÷ 18.6 GB × ~2× MTP), B ≈ 17–21, C ≈ 47 (FP8 DSpark k7). Mismatch >2× → investigate before continuing.

### 4b. Concurrency ladder
c1 / c4 / c8 / c16, 8 distinct prompts × 1500 output tokens each, report:
- aggregate tok/s, per-stream tok/s, p95 TTFT, error count
- **Expectation:** aggregate should keep rising to c16 (target ≈ 150–256 for B; A likely lower — llama.cpp scheduler is the weak point; this is B's strongest argument)

### 4c. Prefix caching (agent-workload simulation)
- 19K-token shared prefix (system prompt + context), 2 requests with different suffixes
- TTFT cold (new container / cache flushed) vs warm → report speedup
- **Expectation:** B: big win (RadixAttention); A: llama.cpp prefix cache (if the bumped build enables it); C: 14–22× per 0xBakeer

### 4d. Prefill (long prompts)
TTFT for ~8K / ~32K / ~100K unique prompts, `max_tokens: 1` (isolates prefill). Note: A at 262K context needs `-c 262144` + q8_0 KV (see §5 memory math) — verify it even fits before this test.

## 5. Stage 3 — long context, stability, recovery

### 5a. Long context (NIAH)
Needle at positions ≈8K / 32K / 131K / 247K inside a 262,144-token window, 3 needles each → 12 probes. Pass = ≥11/12 correct.
- A: `-c 262144 --cache-type-k q8_0 --cache-type-v q8_0` (18.6 GB weights + ~32 GB KV fp8 ≈ 51 GB — inside envelope)
- B: `--context-length 262144` at `mem-fraction-static 0.85` (not 0.95 — see stability)
- Also test 1M YaRN on B only (optional, article: validated 2.0/4.0 factors)

### 5b. Memory envelope & soak
- Record peak container RSS + host MemAvailable after: cold boot, 262K prefill, c16 run
- **Pass:** host MemAvailable ≥ 15 GB at all times; no swap growth > 1 GB; no NVRM/Xid in `journalctl -k`; no `task:...blocked` lines
- Soak: 45 min of mixed traffic (chat + tool + vision + one long-gen), monitor:
  - RSS growth trend (memory leak check — flat after warmup)
  - completion success rate (target 100%; any hang > 60 s = fail)
  - `docker stats` CPU pinned at 100% with 0 completions = the DFlash-style deadlock signature → fail

### 5c. Fault injection & recovery
| Test | A (llama-swap) | B (container) |
|---|---|---|
| `docker kill -9` server | llama-swap respawns on next request; time it (expect seconds) | `restart: unless-stopped` respawns; time it (expect minutes — Python cold start) |
| Kill mid-generation | next request clean | same |
| OOM probe: force overcommit with a second model | must fail predictably (llama.cpp refuses load), no cascade | mem-fraction 0.85 → second model load must be refused by you, not by UVM swap |
| Stall monitor | repoint to candidate endpoint; verify generation-probe (not just `/v1/models`) fires correctly | same |

**The stability decision rule (from the box's history):** the candidate that keeps host MemAvailable highest, recovers fastest, and has zero Xid/kernel alerts over the soak wins the stability axis. A large static reservation (B at 0.95 ≈ 122 GB) is itself a cascade risk — if B requires 0.95 to pass 5a, that's a mark against it.

## 6. Stage 4 — integration & run cards

### 6a. Integration drill (the winner gets wired in; both candidates get a dry run)
1. **A:** new llama-swap model entry (`qwen38` test group) with bumped image pin, `-c 262144`, q8_0 KV, `--spec-type draft-mtp`, `--mmproj`; verify via `curl :8088/v1/chat/completions` and a litellm route
2. **B:** compose service `sglang-qwen38` (bridge net, port 8888, HF cache volume, mem-fraction 0.85) + litellm entry + prometheus `sglang` job + stall-monitor repoint
3. **Vision path:** verify the aux-vision consumer (litellm `unsloth-gemma4-12b-qat-256k-mtp`) can be pointed at the new model instead
4. **Client swap:** pi/agent config, open-webui `OPENAI_MODEL_LIST`, any script referencing `aeon-qwen36-35b-128k-think` → new model name
5. **Rollback drill:** comment out new entry, uncomment aeon, `docker compose up -d --force-recreate` → aeon answers within 5 min (run this BEFORE the final flip, not after)

### 6b. Run card template (one per gate per candidate)

```
candidate: A | date: | image/digest: | checkpoint: | ctx: 262144 | kv: q8_0
spec: draft-mtp n-max 2 | thinking: off | temp: 0 | concurrency: c4 | output_len: 1024
gate: G5 tool-call | result: PASS | tok/s: | ttft: | peak rss: | notes:
```

## 7. Decision matrix (fill after Stage 4)

| Criterion | Weight | A (llama.cpp GGUF) | B (SGLang NVFP4) | C (vLLM FP8) |
|---|---|---|---|---|
| Correctness gates (9/9?) | 25% | /9 | /9 | /9 |
| Stability (5b/5c) | 30% | score 1–5 | score 1–5 | score 1–5 |
| Solo decode tok/s | 15% | | | |
| c16 aggregate tok/s | 10% | | | |
| 262K NIAH | 10% | /12 | /12 | /12 |
| Integration effort (1–5, 5=easy) | 10% | | | |
| **Weighted total** | | | | |

Decision rules:
- **Disqualify** any candidate failing G1–G6 or NIAH < 11/12 unless a documented config fix exists and re-passes.
- **Tie-break on stability weight** (that's the box's documented failure mode).
- If A and B tie: prefer A (existing engine, seconds-cold-start, small envelope) unless B's c16 aggregate is >2× and the fleet workload is real.

## 8. Logistics

- Total wall time ≈ 1 day (downloads ~40 GB can parallelize overnight; tests ~6–8 h sequential since one candidate owns the box)
- Keep aeon up during Stages 1–2 standalone tests (ports don't clash); stop it for soak/integration
- Every artifact (logs, run cards, bench JSON) lands in `docs/qwen38-test-runs/` (git-ignored or committed summaries)
- No config changes to production until the winner is chosen; the integration drill is the last step, not the first

## 9. Checklist (printable)

- [ ] Baseline snapshot + zero Xid lines
- [ ] Downloads complete (A: GGUF+mmproj+image; B: image; C: image+drafter)
- [ ] G1–G9 pass on A
- [ ] G1–G9 pass on B
- [ ] (opt) G1–G9 pass on C
- [ ] Solo decode + MTP acceptance measured (A, B)
- [ ] c1/c4/c8/c16 ladder (A, B)
- [ ] Cold/warm prefix TTFT (A, B)
- [ ] Prefill 8K/32K/100K (A, B)
- [ ] NIAH 12 probes @ 262K (A, B)
- [ ] Soak 45 min + memory trend (winner only)
- [ ] Fault injection + recovery timing (winner only)
- [ ] Integration drill + rollback drill (winner)
- [ ] Decision matrix filled, CHANGELOG updated, commit
