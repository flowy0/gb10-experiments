# Changelog

## 2026-08-20

**DFlash2 draft test (Weschera recipe) — strong result, not yet promoted:**
- Built `weschera/qwen38-27b-dflash2:2026-08-19` (Python-source overlay on our same stock base image + SGLang source e5a3e4d3 with DFlash2/quantized-lm-head patch); downloaded `z-lab/Qwen3.8-27B-DFlash2` draft (1.9 GB)
- Tested at the SAME safe config as production (mem-fraction 0.50, 4 concurrent, cpuset): gates **10/10**, solo **30.68 tok/s (+51% vs DSpark 20.26)**, c16 223.4 (+19%), thinking-on 31.7 (+30%), draft acceptance **3.6-3.9 vs 2.3-2.9**, prefill/prefix unchanged, 0 errors/hangs/kernel alerts
- DFlash2 is the fastest draft method measured on this box at the safe memory setting
- **Gate before promotion: 30-min soak** (DFlash family deadlock history 2026-08-11; DFlash2 is a different implementation — clean bench so far). Run card: docs/qwen38-test-runs/DFLASH2-TEST.md
- Production main still DSpark; test container on port 8889

## 2026-08-19

**SGLang tuning — CPU pinning + corrected GDN pool (from updated MiaAI recipe):**
- Adopted MiaAI 2026-08-18 tuning: `cpuset 5-9,15-19` (GB10 X5 cores; scheduler/tokenizer off the A725 efficiency cores, +2-7% decode) — verified engine affinity
- Corrected mamba pool sizing: `--max-mamba-cache-size 16` = concurrency(4) × 4 state slots (MiaAI: spec verify window is a separate engine-side buffer; old ×12 sizing over-provisioned) — ssm_state pool dropped 3.45→1.20 GB
- Kept mem-fraction-static 0.50 (hasso5703 freeze risk) and 4 concurrent — NOT adopting MiaAI's 0.90/10-concurrent
- Restarted sglang-qwen38; verified: cpuset affinity 5-9,15-19, max_mamba_cache_size 16, engine startup OK, generation OK
- AGENTS.md concurrency rule updated to corrected sizing

## 2026-08-18

**Pi agent config reference (docs/PI_AGENT_CONFIG.md):**
- Documented the hermes pi-agent configuration for the remote machine (YAML): model block (radixark-qwen38-27b-nvfp4-dspark-262k-think via litellm :4000), defaultThinkingLevel medium, retry.provider.timeoutMs 1800000 (truncation fix for slow 20-27 tok/s generations), compaction reserveTokens 16384
- Litellm pass-through fix: `allowed_openai_params: [reasoning_effort]` only — `chat_template_kwargs` / `max_reasoning_tokens` break the OpenAI-SDK path (500 AsyncCompletions.create() unexpected keyword argument); thinking stays ON via SGLang template default
- Verified through litellm: reasoning_effort medium → thinking text present + correct answer

## 2026-08-17

**llama-swap OOM hardening — old large models commented out:**
- Commented 12 large/legacy model entries: all qwen3.6 (27B/35B/35B-A3B), qwen3-coder-next, qwen3-coder-30b, deepreinforce-ornith-35b ×3, gemma4-31b — prevents accidental stacking alongside the SGLang main model (~76 GB) that could cross the ~110 GB danger line (NV_ERR pressure seen 2026-08-17)
- Removed the **DFlash 26B** entry + research-group member (deadlock hazard per 2026-08-11 changelog; research group now serves only the verified QAT MTP 26B)
- Empty `code` group commented; groups now: qwen38-test / research / compression / embed / subagent
- 11 active models remain (all ≤26B; only large one = research 26B QAT MTP); llama-swap restarted, verified via /v1/models
- 12B DFlash subagent entry left as-is (out of scope per 2026-08-11 changelog)

## 2026-08-17

**Co-residency test — research model alongside main (issue noted):**
- `unsloth-gemma4-26b-a4b-qat-mtp2-128k-think` (Gemma4 26B QAT MTP, 14.2 GB + MTP draft, `-c 262144`) loaded via llama-swap in ~20s alongside the SGLang main model — healthy, responding, SGLang unaffected
- Memory with both: **91 GB used / 30 GB available / swap idle** — within envelope but close to the ~110 GB danger line; one more 26B would cross it
- **⚠️ 4× `NV_ERR_NO_MEMORY` (20:30:34) during the co-load** — CUDA context buffer allocation (`kgrctxAllocMainCtxBuffer`) failed transiently then recovered; both models stayed healthy (sglang RestartCount=0, stall monitor no action). Same driver-pressure signature as AGENTS.md playbook
- Lesson reinforced: load one big model at a time, let it fully cold-start; avoid stacking 3 models; the 0.50 SGLang config gives 30 GB headroom for exactly one large llama.cpp model
- Stall monitor (20:39 run) will log WARNING (kernel alerts +3) — expected, not an action trigger (both models pass generation probes)

## 2026-08-17

**🔴 FLIP — Qwen3.8-27B is now the main model (SGLang + DSpark, safe config):**
- Winner: **SGLang (B2)** — RadixArk NVFP4 + DSpark k7 @ mem-fraction-static 0.50 + docker 100g caps (hasso5703 field-validated GB10-safe config; SGLang's accounting misses 25-40GB of transient flashinfer/autotuner allocations on unified memory — >0.50 risks a hard freeze)
- Named per AGENTS.md convention: `radixark-qwen38-27b-nvfp4-dspark-262k-think` — exposed via litellm (port 4000) → sglang-qwen38:8888
- aeon-qwen36-35b RETIRED (commented in compose, removed from litellm; port 8000 freed); litellm depends_on → sglang-qwen38; open-webui model list → new model
- Stall monitor repointed to sglang (port 8888, generation-probe mandatory — SGLang /v1/models answers before engine ready); timer was pausing it during sessions — re-enable after soak
- Retest data (Session B2/B2b): SGLang DSpark@0.50 solo 20.3 / c16 187.6 / prefix 51× / gates 10/10 / 262K spot-check FOUND; MTP@0.50 solo 24.5 (one-flag alternative); DSpark underperforms MTP on fresh codegen but is the community-validated config (hasso 34-38 tok/s on math/eval workloads)
- vLLM (candidate C) DISQUALIFIED: 2× GPU driver OOM (NV_ERR_NO_MEMORY) at recipe gmu 0.85 — matches AGENTS.md "stock vLLM crashes on Blackwell"
- OOM probe passed: nomic-embed coexists with main model (50 GB headroom)
- **45-min soak PASSED**: 252/252 requests OK (0 hangs), RSS flat 5.79→5.793 GiB (no leak), 0 kernel errors; vision verified separately (live transcription via litellm, thinking on)
- Integration verified: litellm:4000 → sglang:8888 full path answers correctly; vision+thinking proven live (enable_thinking + generous max_tokens)
- Winner run card: docs/qwen38-test-runs/FLIP-WINNER.md

## 2026-08-17

**Session A started — llama.cpp + AtomicChat GGUF (candidate A):**
- Booted standalone on 8090 (bumped pin `server-cuda13@sha256:7ee22018…`, `-c 262144`, q8_0 KV, MTP n2, mmproj) — **cold boot ~25 s**
- Correctness gates **10/10 PASS** (arith think on/off, BANANA, code, tool call, multi-turn, vision transcription, reasoning effort low<xhigh, sampling)
- Findings: (1) llama.cpp does NOT translate OpenAI `role:tool` for the Qwen3.8 template — tool results must be sent as `role:user` `<tool_response>…</tool_response>` blocks (client/agent layer must format them); (2) valid `reasoning_effort` = xhigh|medium|low (`high` raises Jinja error)
- Bench: solo **20.8 tok/s**; MTP sweep 11.1 → 20.8 (n2, 1.87×) → 21.1 (n5); ladder c1=22.7 c4=59.6 c8=93.1 c16=**126.0** aggregate, 0 errors; prefix 19K cold→warm **116.7×** (26s→0.22s); prefill TTFT 8K=11s 32K=44s 100K=159s; thinking-on ~20% hit (16.8 tok/s)
- Operational: 4 slots @262K (concurrency beyond 4 queues); ~37 GB memory; aeon stopped for session (will restore at teardown)
- NIAH @ 262K in progress (12 probes, ~80 min)
- New scripts: scripts/qwen38-gates.sh (G1–G9, reusable per candidate), scripts/qwen38-niah.py (needle probes); run cards in docs/qwen38-test-runs/ (git-ignored)

**Session A complete:**
- NIAH @ 262K **12/12 PASS** (needles @ 8K/32K/131K/247K × 3 in ~224K window, ~540s/probe)
- Teardown done; aeon restored
- Candidate A summary: 262K confirmed, tools/thinking/vision work (`<tool_response>` protocol for multi-turn), 20.8 solo / 126 c16 (4-slot cap @262K), 116× prefix caching, ~37 GB memory

**Session B — SGLang + RadixArk NVFP4 (candidate B):**
- Boot ~180s (pre-seeded HF cache, no download); compose service at mem-fraction 0.85 (105 GB reserved, 15 GB headroom)
- Gates **10/10 PASS**; **native `role:tool` works** (qwen3_coder parser — drop-in OpenAI semantics, no `<tool_response>` workaround); vision exact; reasoning effort low<xhigh
- Bench: solo **27.4** (+31% vs A), c16 aggregate **291.0** (+2.3× vs A), prefill 100K **77s** (2× faster), prefix 46.8×, thinking-on 22.8 tok/s
- NIAH @ 262K **12/12 PASS** (~314s/probe, 1.7× faster prefill)
- Stability: graceful restart (compose/stall-monitor path) recovers to full speed; **SIGKILL auto-restart BROKEN on this box** (exit 137, restart policy didn't fire, dead 10+ min until manual restart); post-heavy-load degradation to ~0.3 tok/s fixed by graceful restart; `/v1/models` not a reliable readiness signal
- **Methodology correction:** `docker kill -9` is an invalid flag on this Docker build (`-s KILL` required) — Session A's original recovery smoke was invalid, re-tested properly (llama.cpp: health ~5-6s warm, generation OK); earlier "empty generations" were thinking-on artifacts (template defaults thinking ON — probes must set `enable_thinking:false` or give token headroom)
- aeon restored; box back to production state

**Session C — vLLM stock + FP8 + DSpark k7 (ABORTED: GPU OOM):**
- Boot ~721s (torch.compile); gates 10/10 effective (thinking in `message.reasoning` — vLLM convention; native role:tool works; effort low<xhigh); KV cache 624K tokens = matches 0xBakeer's published FP8 DSpark-k7 figure (config validated)
- **CRASH: `NV_ERR_NO_MEMORY` from NVRM driver during c16 ladder at gmu 0.85** — same cascade signature as AGENTS.md playbook; 0.85 = 2.4× the box's documented 0.35 vLLM limit; stock vLLM memory spikes (torch.compile + cuda-graph capture) unlike SGLang's flat 0.85 reservation
- Fresh-gen solo: **13.96 tok/s** — the article's 46.9/75 figures were edit-heavy workloads; on fresh generation (agent's actual workload) FP8+DSpark is slower than both A (20.8) and B (27.4)
- Session stopped by decision; 4-bit repo leg (unsloth NVFP4, 22 GB downloaded) NOT tested; retry at gmu 0.70/enforce-eager/V2-off didn't complete boot
- **Verdict: candidate C disqualified on stability** — consistent with AGENTS.md's standing "stock vLLM crashes on Blackwell" warning

## 2026-08-17

**Qwen3.8-27B stack wiring (flip-ready, nothing started):**
- docker-compose.yml: added `sglang-qwen38` service (MiaAI-Lab recipe flags verbatim, `--mem-fraction-static 0.85`, port 8888, HF cache mounted from /opt/atom/models/hf-cache, Triton cache volume) — **profile-gated** (`profiles: [qwen38-test]`) so plain `docker compose up -d` never starts it; start explicitly with `docker compose up -d --force-recreate sglang-qwen38` after stopping aeon (0.85×128GB + aeon = OOM risk)
- litellm/config.yaml: added `qwen3.8-27b-sglang` → `http://sglang-qwen38:8888/v1` (active; inert until sglang is up)
- llama-swap/config.yaml: added `atomicchat-qwen38-27b-mtp-262k-think-code` (candidate A — bumped pin `server-cuda13@sha256:7ee22018…`, `--mmproj`, `-c 262144`, q8_0 KV, MTP, embedded template — NOT the qwen3.6 fixed template) + `qwen38-test` group
- scripts/stall-monitor.sh: parameterized watch (MONITOR_PORT/MODEL/CONTAINER env, default aeon; e.g. `MONITOR_PORT=8888 MONITOR_MODEL=qwen3.8-27b-sglang MONITOR_CONTAINER=sglang-qwen38`)
- prometheus/prometheus.yml: added `sglang` scrape job (no data until sglang up)
- .gitignore: docs/qwen38-test-runs/ (bench output)
- Nothing running, nothing restarted — production (aeon on 8000) untouched

## 2026-08-17

**Qwen3.8-27B bench harness + Stage 0 prep (scripts/bench-qwen38.py):**
- Wrote shared benchmark harness: solo decode (1024-out + 256-out prefill-drag control), MTP sweep, c1–c16 concurrency ladder, cold/warm prefix TTFT, prefill TTFT, thinking-on cost — OpenAI-compatible (llama.cpp/SGLang/vLLM), temp 0, thinking off by default, distinct prompts per level, JSON checkpoint after every sub-test, run-card output
- Validated against a mock server; fixed: thread-local sessions (shared Session deadlocks under the ladder), transient-error retries (ConnectionReset kills a long run otherwise), per-sub-test error isolation + checkpointing (one failure no longer discards the session)
- Stage 0 downloads complete: AtomicChat AD-Q5_K_M-Q4_K_M GGUF (18.5 GB) + mmproj-F16 (0.93 GB) → /opt/atom/models/atomicchat-qwen38; RadixArk Qwen3.8-27B-NVFP4 (3 shards) → /opt/atom/models/hf-cache (HF cache structure, ready for SGLang mount); images pulled: lmsysorg/sglang:qwen38-27b (digest febfb971…), ghcr.io/ggml-org/llama.cpp:server-cuda13 (digest 7ee22018… — pin-bump candidate)
- Measured: this box pulls from HF at ~11.4 MB/s (~91 Mbps) — downloads were bandwidth-bound

## 2026-08-17

**Qwen3.8-27B test plan (docs/QWEN38_TESTPLAN.md):**
- Full empirical plan to decide between candidates: A) llama.cpp + AtomicChat AD-Q5_K_M-Q4_K_M GGUF (arch `qwen35` = same as qwen3.6, runs on existing stack with bumped llama.cpp pin), B) SGLang + RadixArk NVFP4, C) optional vLLM FP8 reference
- **Per-candidate sessions** (box can only host one engine at a time): each candidate booted once, then correctness gates G1–G9 → **full benchmark** (solo, MTP sweep, c1–c16 ladder, prefix, prefill) → NIAH @ 262K → recovery smoke → teardown; winner then gets 45-min soak + OOM probe + integration/rollback drills
- 9 correctness gates (arith think on/off, tools, multi-turn, vision, reasoning effort), controlled methodology (≥400-tok decode, thinking off, distinct prompts, cold/warm prefix)
- Key findings feeding the plan: AtomicChat GGUF header arch = `qwen35` (same family as running qwen3.6 → pinned llama.cpp build v9843 likely works but predates the model; pin bump + gates G2/G8 verify chat_template_kwargs support); SGLang mem-fraction 0.85 max (0.95 = cascade risk); decision rule = disqualify on core-gate fail, tie-break on stability

## 2026-08-17

**Qwen3.8-27B implementation research (docs/QWEN38_RESEARCH.md):**
- Assessed @0xBakeer tweet/article (75 tok/s solo, 256 tok/s @ 16 concurrent) against two repos: r0b0tlab vLLM NVFP4+MTP and MiaAI-Lab SGLang
- Recovered full article text; headline numbers trace to 0xBakeer's own repos (FP8 + DSpark k=7/k=14 + `--enable-prefix-caching`, stock vLLM v0.27.1-aarch64 image — no custom wheel)
- Key findings: quant is the smallest lever (1.6× solo, 0.2% @ c16); spec decode ≈ 6× and output-preserving; prefix caching silently OFF for hybrids in vLLM (14–22× on shared prefixes); DSpark drafter 3.3× cheaper per draft token than MTP; `VLLM_MARLIN_USE_ATOMIC_ADD=1` mandatory for 4-bit on SM121
- Verdict: 0xBakeer FP8 recipe primary (output-preserving, 262K, 46.9 solo/256 c16), MiaAI SGLang as stable alternative, r0b0tlab only for ≤32K/thinking-off; speed regression vs MoE 35B-A3B flagged (dense 27B)
- No config changes made — research only

**AEON vLLM upgraded to v0.26.0 (2026-07-27):**
- Image: `ghcr.io/aeon-7/aeon-vllm-ultimate:2026-07-27-v0.26.0` (was v0.25.1) — vLLM 0.26.0 (429 commits): NVFP4_AWQ checkpoints, DFlash batch-cap unlock (128-way), `--prefix-match-unit`, drafter `kv_cache_dtype`, hybrid partial prefix-cache hits
- **DFlash stays disabled** (deadlock root cause, upstream has no fix — open issue #5 still unresolved)
- Retested without DFlash: 73 tok/s (parity with v0.25.1 baseline), `finish: stop` with content, no engine errors
- Rollback tag documented in docker-compose.yml: `:2026-07-16-v0.25.1`
- Memory: ~15 GiB available with all 3 engines loaded (26B + 27B llama.cpp + vLLM 53 GB) — 27B TTLs out in 1h
- Repo intel: AEON vllm-ultimate-dgx-spark issue #9 (unified-memory pressure → host freezes) closed; fix = lower max-num-seqs + drop kv-cache-memory-bytes override; issue #5 (DFlash crash under load) still OPEN

## 2026-08-11 (second fix)

**DFlash removed from all llama.cpp models — MTP instead:**
- **unsloth-gemma4-26b-a4b-qat-mtp2-128k-think** (research): DFlash draft → **MTP draft** (`mtp-gemma-4-26B-A4B-it.gguf`, arch `gemma4-assistant` same as proven-good 12B) with `--spec-draft-n-max 2` — matches the config's original "QAT MTP γ=2" design; keeps spec-decode speedup without DFlash deadlock risk. Cold start 10.9s, responds normally
- **unsloth-qwen36-27b-q4-dflash-64k-code** (code): DFlash draft → **built-in MTP** (`--spec-type draft-mtp --spec-draft-n-max 2`, no draft file — GGUF includes MTP head, same as the mtp2-ud-q3 sibling)
- **unsloth-gemma4-12b-q4-dflash-64k-think** (subagent): still DFlash — NOT changed (outside scope; MTP siblings already exist for it via `unsloth-gemma4-12b-qat-64k-mtp-np2` / `-128k-mtp`)
- llama-swap restarted; both converted models verified loading and generating
- GPU: 93.6 GB of 131 GB in use (vLLM 53 GB + 26B 20 GB + 27B 21 GB); RAM pressure high (~4.5 GB free) while all three loaded — 27B TTLs out in 1h

## 2026-08-11

**vLLM DFlash deadlock — diagnosis & fix:**
- **Incident**: AEON vLLM (aeon-qwen36-35b) engine deadlocked Sun Aug 9 ~20:54 +08 — spun at 100% CPU with 1 request stuck "running", **zero completions for ~38h** through Tue Aug 11
- **Symptoms from Fri Aug 7**: spec-decode throughput collapsed to 0.2–4 tok/s; litellm logged **74 request timeouts** (all on `aeon-qwen36-35b-128k-think`), each waiting the full 6000s timeout; 17 on Fri, 11 Sat, 25 Sun, 19 Mon, 2 Tue
- **Root cause**: DFlash speculative decoding (`num_speculative_tokens:12`) deadlocks the engine. Same DFlash draft path also stalled llama.cpp models (13–24 min requests, SIGKILL exit 137). NVRM `NV_ERR_NO_MEMORY` driver OOM at Aug 10 23:01 under system RAM pressure (12.3/16 GB swap used)
- **Why it wasn't caught**: `/v1/models` is served by the API server process, not the engine — kept answering 200 in 1.4ms while the engine was hung; stall monitor only checked `/v1/models` and its restart target `vllm-qwen36-35b-a3b-nvfp4` was commented out
- **Fix**: disabled DFlash on aeon-qwen36-35b (commented out `--speculative-config` + `/dflash` mount, baseline ~73 tok/s no spec decode); restarted with `docker compose up -d --force-recreate aeon-qwen36-35b`
- **Stall monitor hardening**: now also sends a real `max_tokens:1` generation probe (45s timeout, score +3) in addition to `/v1/models`; restart target corrected to `aeon-qwen36-35b`
- **Note**: model is `Qwen3_5MoeForConditionalGeneration` — no built-in MTP head, so no spec-decode alternative until AEON fixes DFlash or an MTP head is available

## 2026-07-28

**AEON vLLM Ultimate tested — 3× speedup:**
- **Qwen3.6-35B-A3B**: 222 tok/s (vs 73 before) — AEON vLLM v0.25.1, DFlash + FP8 KV
- **Gemma4 26B NVFP4**: 309 tok/s (vs 80 on llama.cpp, 50 on old vLLM) — DFlash + FP8 KV
- AEON uses `--gpu-memory-utilization 0.60` (78 GB) vs 0.35 (46 GB) before
- Tool calling works on both models
- Memory trade-off: 52 GB remaining for llama.cpp (was 85 GB)

**GPU cascade crash investigation:**
- **Root cause**: vLLM hit NVRM Xid 13 Graphics Exception at 03:07, corrupting GPU state
- **Cascade**: Subsequent model loads failed with OOM → system memory pressure → SSH dead → reboot
- **Fix**: Reduced vLLM `--gpu-memory-utilization` 0.40 → 0.35 (~46 GB), added GPU health monitor
- **Doc**: Added cascade failure pattern, diagnosis steps, and lockout recovery to AGENTS.md

## 2026-07-16

**Gemma4 updates & testing:**
- **Updated Gemma4 chat template** (July 2026 release) — fixed tool-calling loops, thinking gate logic
- **Gemma4 26B vanilla + DFlash** scored **97/100** tool-eval (up from ~85-90 for earlier Gemma4 variants)
- **Tested Unsloth Qwen3.6-35B-A3B NVFP4** (25 GB) — **66 tok/s** vs NVIDIA's 73 tok/s, removed
- **nomic-embed-text batch size** increased to 8192 for large embedding chunks
- **Agentic workflow note added**: DFlash + thinking = broken. DFlash needs `enable_thinking: false`

## 2026-07-14

**Stack overhaul — vLLM hermes + DFlash:**
- **Hermes switched from Ornith 35B (llama-swap) → Qwen3.6-35B-A3B NVFP4 (vLLM)**
  - 73 tok/s baseline, **270 tok/s with DFlash** (3.7× speedup)
  - Built-in vision — replaces aux model
  - LiteLLM router added (port 4000) for unified endpoint
  - Gemma4 vLLM services retired (commented out)

**DFlash speculative decoding (vLLM + llama.cpp):**
- **Hermes (vLLM):** 270 tok/s with z-lab DFlash draft (737 MB)
- **Gemma4 26B research (llama.cpp):** 80 tok/s with Alittlehammmer DFlash (254 MB)
- **Gemma4 12B subagent (llama.cpp):** 76 tok/s with williamliao DFlash (422 MB)
- **Qwen3.6-27B code (llama.cpp):** vanilla Q4 + DFlash draft (986 MB) added
- Rebuilt vLLM image to July 12 main (v0.23.1rc1.dev1053)

**New models:**
- **Qwopus3.6-27B-v2** and **Qwopus3.6-35B-A3B-Coder** (Jackrong finetunes, test group)
- **Qwythos-9B** (Empero, Claude Mythos reasoning, test group)
- **nomic-embed-text-v1.5** (81 MB, embed group, 32k context, batch 8192)
- **BGE-M3** replaced nomic (briefly), then nomic restored

**Memory optimization:**
- Aux model removed (hermes handles vision)
- Compression model unused
- All three DFlash models fit simultaneously (~124 GB out of 131)
- OOM avoidance notes added to AGENTS.md

**Infrastructure:**
- vLLM image rebuilt (spark-vllm-docker)
- LiteLLM router added for unified endpoint
- LibreChat stopped (Gemma4 tool-calling issues)
- Open WebUI upgraded to v0.10.2
- Chat template updated to froggeric v21.3
- MEMORY.md updated with DFlash benchmarks and scenarios
- README updated with current stack and known issues

## 2026-06-27

**Stack config changes:**
- **Code model**: Ornith-35B → Qwen3.6-27B UD-Q3 MTP (SWE-bench 75.0, 24 GB, 97/100 tool-eval)
- **Hermes**: `-c 262144 --parallel 2 -kvu` → 256k shared pool, 2 slots (~48 GB)
- **Subagent**: `-c 65536 --parallel 2 -kvu` → 64k shared pool, 2 slots
- **Hermes temp 0.8 → 0.6** — tighter for agentic tasks
- **Subagent -np 3 → -np 2** (saves 3 GB)
- **KV cache standardized to q8_0** on all Ornith routes (was f16 → halved memory)
- **Compression**: uses E4B TQ (excluded from active memory calc)
- **Ornith and 9B renamed** to `deepreinforce-` prefix (convention)

**Test group additions:**
- `deepreinforce-ornith-35b-q4-128k-think-code` (~27 GB with q8_0 KV)
- `deepreinforce-ornith-35b-q4-64k-think-code` (~25 GB)
- `deepreinforce-ornith-9b-q4-64k-think-code` and `-code` (no reasoning)
- `unslooth-qwen3-coder-next-ud-q3-64k-think-code` (80B hybrid, 34 GB file)

**Bugs found and fixed:**
- **Slot splitting** — `-c 131072 --parallel 2` without `-kvu` silently gave each slot 65k
- **`--np 2` invalid** — should be `-np 2` (single dash). Removed duplicate with `--parallel`.
- **Missing `groups:` section** — corrupted by YAML edits. Restored.
- **Config validation script** (`llama-swap/check-yaml.sh`) updated with better checks.

**Discovered / evaluated:**
- **Ornith-1.0-35B** — 100/100 tool-eval (Q4_K_M, 20 GB)
- **Qwen3-Coder-Next 80B** — 39 tok/s, ~37 GB at 64k
- **BeeLlama.cpp** (Anbeeld fork, 718 stars) — DFlash + TurboQuant combined
- **DeepSeek DSpark Gemma4 12B draft** — `Gemma4DSparkModel` arch, not compat yet
- **DFlash attempt**: Docker image built but `dflash-draft` arch not recognized

**Documentation:**
- **MEMORY.md** rewritten with full architecture tables, KV calculations, active stack
- **AGENTS.md** updated: naming convention, KV cache convention, MTP+mmproj note
- **BENCHMARKS.md** updated with Ornith and tool-eval scores
- **CHANGELOG update rule** added to AGENTS.md

- **Fixed slot splitting bug** — added `-kvu` (kv-unified) to hermes and subagent.
  Without it, `-c 131072 --parallel 2` silently gave each slot only 65k.
  With `-kvu`, the full pool is shared dynamically between slots.
  Hermes: `-c 262144 -kvu` → 256k pool, 2 slots (~48 GB).
  Subagent: `-c 65536 -kvu --parallel 2` → full 64k per slot.
- **MTP + mmproj collision tested** — no issue found. Draft acceptance 63% (text) and 53% (image).
- **Hermes temp 0.8 → 0.6** — tighter for agentic tasks
- **KV cache standardized to q8_0** on all Ornith routes (was f16 default, halved memory)
- **Subagent -np 3 → -np 2** (saves 3 GB)
- **Ornith 35B 128k added** (test group, ~27 GB with q8_0 KV)
- **BeeLlama.cpp discovered** (Anbeeld fork, 718 stars) — DFlash + TurboQuant combined
- **DeepSeek DSpark Gemma4 12B draft model** found — not llama.cpp compatible yet
- **DFlash attempt**: Docker image built but `dflash-draft` architecture not recognized
- **MEMORY.md rewritten** with full current stack calculations

## 2026-06-25

- **Downloaded & tested Qwen3.6 27B NVFP4** (vLLM, 25 GB, 17 tok/s) — rejected
- **Downloaded Qwen3.6 27B IQ4_NL + UD-Q4_K_XL** GGUF quants for llama.cpp
- **Rebuilt spark-vllm-docker** with wheel from June 23 (PR #45413: Qwen3 parser engine)
- **Added `qwen3_coder` tool parser** to vLLM config
- **Tested DiffusionGemma 26B NVFP4** — 127-135 tok/s on vLLM (port 8001)
- **DiffusionGemma tool-eval-bench** — 85/100 ★★★★ (53/69 passed)
- **Rolled back** NVFP4 → FP8 256k baseline for Gemma4 26B (quality regression)
- **Added MTP γ test entries** (mtp1/mtp2/mtp3) for Qwen3.6 27B in code group
- **Switched 12B QAT** from 128k → 256k TQ (matches vLLM context)
- **Fixed reasoning flags** across all think variants (`--reasoning on`, `--reasoning-budget`)
- **Added `docs/BENCHMARKS.md`** with all tok/s and tool-eval results
- **Added `docs/QUICK_CMDS.md`** with common commands reference
- **Updated AGENTS.md** with benchmark recording rules, tool parser notes, V2 runner

## 2026-06-09

- **Upgraded llama.cpp:** b9294 → 9544 (server-cuda13, commit 98d5e8ba8)
- **Downloaded Gemma4 MTP drafter:** `gemma-4-26B-A4B-it-MTP-Q8_0.gguf` (441 MB)
- **Added MTP variant:** `unsloth-gemma4-26b-a4b-q4-128k-fa-think-mtp` (requires build >9544)
- **Updated GGUFs:** 26B Q4 and Q5 re-downloaded for latest chat template fixes

## 2026-06-08

- **vLLM attempts concluded:** NVFP4 (AutoTuner loop), FP8 (OOM), AEON (container too large)
- **Hermes main:** switched from Qwen35B → Gemma4 26B QAT for safety/data privacy
- **Hermes aux:** moved from `hermes` → `summary` group for simultaneous loading
- **LibreChat/OpenWebUI:** updated to use Qwen36 only
- **Fixed duplicate group membership** errors causing llama-swap to crash
- **Documented all vLLM attempts** in README with root cause analysis

## 2026-06-07

- **Added iq4-fa-think-code variants** for 27B, 26B, and 35B (temp=0.6, pp=0.0)
- **Added --reasoning-budget 16384** to all 28 general think variants (was unlimited)
- **Renamed -thinking → -think**, -thinking-code → -think-code across all models
- **Added 512k YaRN variants** for 35B (non-think + think)
- **Moved all MTP models** to dedicated `mtp-test` group

## 2026-06-06

- **Added iq4_nl KV cache variants** (q4, q5, q2 at 256k) with --flash-attn on
- **Added Gemma4 12B QAT** (non-think + think at 128k and 256k)
- **Added Gemma4 31B 256k YaRN** thinking variant
- **Attempted vLLM:** AEON image (40.8 GB) → OOM during loading
- **Git repo synced** to github.com/flowy0/gb10-experiments

## 2026-06-05

- **Fixed context division issue:** removed --parallel from all models (was splitting -c by N slots)
- **Added Gemma4 26B QAT** variants (128k + 256k, both thinking)
- **Removed --flash-attn on** from 256k Gemma4 models (unreliable on this build)
- **Switched KV cache q5_1 → q8_0** for stability
- **Added --reasoning-budget** to Gemma4 thinking models

## 2026-06-04

- **Added Gemma4 12B** (Q4_K_M 128k + Q5_K_M YaRN 256k)
- **Added Gemma4 31B** (UD-Q2_K_XL 128k, non-think + think)
- **Created docs/MEMORY.md** with architecture tables and pairing estimates

## 2026-06-01 — 2026-06-03

- **Qwen3.6 model setup:** thinking/non-thinking variants, MTP, high-context (64k/128k/256k)
- **Upgraded llama.cpp b9085 → b9294** for --spec-type draft-mtp support
- **Added Qwen3.6 35B-A3B** (UD-Q2_K_XL) at 32k, 128k, 256k
- **Reasoning budget and repeat-penalty** added to fix thinking loops
- **Group reorganization:** code, research, stable, hermes groups configured

## 2026-05-26 — 2026-05-31

- Initial llama-swap config setup
- Qwen3.6 27B models added
- Gemma4 E4B and 26B-A4B configured
- LibreChat and Open WebUI integrated

### Build 9585 — Gemma4 MTP Support (2026-06-10)

- Upgraded llama.cpp from b9544 (Jun 6) → **b9585** (Jun 9) — includes PR #23398 for Gemma4 MTP speculative decoding
- Added  entry with Q8_0 MTP drafter (95 MB)
- Updated all 130 image SHA references in config.yaml


### Build 9585 — Gemma4 MTP Support (2026-06-10)

- Upgraded llama.cpp from b9544 (Jun 6) -> b9585 (Jun 9) — includes PR #23398 for Gemma4 MTP
- Added unsloth-gemma4-e4b-qat-q4-256k-mtp entry with Q8_0 MTP drafter (95 MB)
- Updated 130 image SHA references in config.yaml

### Known Issue: E4B MTP segfault on b9585

- E4B MTP works with flash-attn off + fit off at small contexts
- Crashes (segfault, exit 139) at 128k+ context on Blackwell GB10
- 26B MTP works fine — likely b9585 bug specific to E4B MTP
- Using E4B QAT non-MTP variant instead

### DiffusionGemma — Pending llama.cpp Support

- Downloaded DiffusionGemma 26B Q4 (16 GB) — multimodal Gemma4 variant with image input
- Entry added but commented out: unknown model architecture 'diffusion-gemma' on b9585
- PRs #24427 and #24423 opened 2026-06-10 — waiting for merge + new build
