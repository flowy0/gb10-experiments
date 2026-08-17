# Qwen3.8-27B on DGX Spark — Implementation Research

> **OUTCOME (2026-08-17):** The winner is **SGLang + RadixArk Qwen3.8-27B-NVFP4 + DSpark k7 at the safe GB10 config** (`--mem-fraction-static 0.50` + docker 100g caps) — now the main model as `radixark-qwen38-27b-nvfp4-dspark-262k-think`. vLLM was disqualified (2× driver OOM); llama.cpp was the strong runner-up. Full results: [qwen38-test-runs/FLIP-WINNER.md](qwen38-test-runs/FLIP-WINNER.md).

> Research date: 2026-08-17. Source: [@0xBakeer tweet + X article](https://x.com/0xBakeer/status/2089090318905774558) (article id `2089076470865854466`), plus three GitHub repos compared below.
> Context: evaluating replacing the current main model (Qwen3.6-35B-A3B, `aeon-qwen36-35b`) with Qwen3.8-27B (dense), single model on this box.

## TL;DR

- The tweet's headline numbers (**75 tok/s solo, 256 tok/s aggregate at 16 parallel requests**) come from **0xBakeer's own repos**, not from either repo in the original comparison. Recipe: **stock vLLM image + DSpark k=7/k=14 drafter + `--enable-prefix-caching`**. No custom wheel required.
- The single biggest wins are **not quantization**: speculative decoding ≈ 6× and prefix caching 14–22× on shared prefixes — both output-preserving. 4-bit quant buys 1.6× solo and **0.2% at 16 concurrent requests**.
- Of the two repos originally compared:
  - **r0b0tlab (vLLM NVFP4+MTP, custom tuned wheel)** — fastest of the two as shipped (27.8 tok/s c1), but 32K context on fast profiles, thinking recommended off, **prefix caching explicitly disabled** (the article's biggest prefill lever), 1-day-old custom build with a bespoke checkpoint.
  - **MiaAI-Lab (SGLang cookbook)** — slower (16.9–21 tok/s) but 262K–1M context with MTP, thinking on, tools, vision, official image. Better *agent* default.
- **Verdict for this stack:** if switching to Qwen3.8-27B, prefer **0xBakeer's FP8 recipe** (output-preserving, all three levers on, stock image) with DSpark k=7, prefix caching on, 262K context. MiaAI SGLang as the stable alternative if vLLM DSpark/prefix-cache quirks bite.
- **Watch out:** Qwen3.6-35B-A3B is a MoE (3B active, ~164 tok/s on this box). Qwen3.8-27B is dense — expect a 2–10× per-token regression regardless of implementation. The switch is a capability trade, not a speed trade.

---

## 1. The article — claims vs methodology

Full article text recovered via syndication API. It is a 40-configuration benchmark study on one DGX Spark (GB10, 128 GB, 273 GB/s), `temperature=0`, thinking disabled.

### Headline ladder (single stream, edit-heavy workload)

| Step | Config | tok/s | Gain |
|---|---:|---:|---:|
| Baseline | Qwen3.8-27B-**FP8**, no spec decode, no prefix cache (stock vLLM) | 7.88 | 1.0× |
| + speculative decoding | FP8 + spec (MTP or DSpark k≈7) | 46.8 | 5.9× |
| + deeper draft | FP8 + DSpark k=14 | 58.5 | **7.4× — still FP8, zero accuracy risk** |
| + 4-bit quant | NVFP4 + DSpark k=14 | 75.0 | 9.5× total (only **1.6×** from quant) |

### Key findings

1. **"Quantization is a single-user optimization."** NVFP4 vs FP8 advantage: +27% at c1 → +20% at c4 → +10% at c8 → **+0.2% at c16**. Single-stream is bandwidth-bound (273 GB/s); under batch it becomes compute-bound and byte count stops mattering.
2. **Prefix caching is silently OFF in vLLM for hybrid models.** Default logic in `engine/arg_utils.py`: `is_prefix_caching_supported AND NOT is_hybrid`. Qwen3.8 reports `is_hybrid=True` (48 GatedDeltaNet + 16 full-attention layers). Enabling it: **14× on a 19K shared prefix, 22× on 53K** (cost: ~22% of KV capacity).
3. **DSpark drafter > MTP.** Cost per draft token: MTP 0.153 decode-steps (re-runs one layer sequentially + full ~150K-vocab `lm_head` per draft), DSpark 0.046 (separate 5-layer, ~1B drafter emits a 7-token block at once). DSpark accepts *fewer* tokens/pass (7.91 vs 8.95) and is still ~46% faster.
4. **Acceptance rate is the wrong tuning dial.** k=7→14 drops acceptance 98.7%→68.7% yet speeds generation up 27%: mean tokens/pass rises 7.91→10.62. First 5 draft positions are ~free (1.000/1.000/1.000/1.000/1.000/0.959/0.945 at k=14); position 14 is 2.7%.
5. **SM121 has no native FP4 compute path.** 4-bit weights dequantize through Marlin before every matmul; decode hides it, prefill pays 7–9% at long context (absent at 8K).
6. **k does not transfer across quant or workload.** k=14 costs 4.6% aggregate at c8 on NVFP4 but **43% on FP8** (FP8 KV = 579K tokens vs NVFP4's 1.32M). Draft acceptance: ~99% editing existing code, ~29% writing new code.
7. **Spec decode can't force a token but does change output.** 20/20 byte-identical within a config; 8/20 across configs (batch-geometry changes FP accumulation order). Deterministic per config, not per model.
8. **Prefill is where 4-bit loses** — ~8K: −1.4%, ~32K: +7.1% FP8 advantage, ~100K: +9.1%. Marlin dequant is compute-bound work in the compute-bound phase.

---

## 2. The three implementations

### 2a. 0xBakeer repos (the article's actual recipes) — `0xBakeer/Qwen3.8-27B-FP8-on-a-single-DGX-Spark` + `...-4-bit-on-a-single-DGX-Spark`

- **Image:** stock `vllm/vllm-openai:v0.27.1-aarch64` (no custom build)
- **Default spec:** DSpark k=7 (`SPEC=dspark|mtp|off`, `K=7`), drafter `Doopeworld/Qwen3.8-27B-DSpark-vLLM`
- **Flags that matter:** `--enable-prefix-caching`, `--max-model-len 262144`, `--gpu-memory-utilization 0.85`, `--max-num-batched-tokens 16384` (required for k≥14: default 2048 makes `max_num_scheduled_tokens = -1280`), `--reasoning-parser qwen3`, `--tool-call-parser qwen3_xml`, `--enable-auto-tool-choice`, `--limit-mm-per-prompt.image 2`
- **4-bit repo adds:** `-e VLLM_MARLIN_USE_ATOMIC_ADD=1` (**not optional on SM121** — Marlin race produces *incorrect output* silently), `-e VLLM_USE_FLASHINFER_MOE_FP4=0` (cheap insurance; CUTLASS FP4 reportedly emits garbage on SM121). Default model `unsloth/Qwen3.8-27B-NVFP4` (22.6 GB, **1,323,090 KV tokens**).
- **Measured (NVFP4 + DSpark k=7, gmu 0.85, 262K):**

| | c1 | c4 | c8 | c16 |
|---|---:|---:|---:|---:|
| FP8 | 46.91 | 134.21 | 208.71 | **256.08** |
| NVFP4 | 59.79 | 161.36 | 229.31 | **256.47** |

- **NVFP4 + DSpark k=14 (single stream):** 75.01 tok/s edit-heavy / 29.55 fresh-gen. k=14 loses ~5% at c8 → use k=7 for fleet, k=14 for interactive.
- **Quality:** FP8 = zero quantization question. NVFP4 (Unsloth) publishes no quality numbers; MixedInt4-AutoRound publishes 99.32% MMLU recovery but has 1.85× less KV and slower prefill/aggregate.

### 2b. r0b0tlab — `r0b0tlab/qwen38-27b-nvfp4-sm121-vllm` (vLLM NVFP4+MTP)

- **Image:** custom source-built **vLLM v0.27.2rc0-sm121** wheel (private commit `7f7a32c`, GHCR `ghcr.io/r0b0tlab/qwen38-27b-nvfp4-sm121:v0.27.2rc0-sm121`). Cannot rebuild without the exact source+arch list. Claims tuned SM121 FP4 GEMM kernels: stock-nightly MTP 20.4 vs their 27.8.
- **Checkpoint:** `r0b0tlab/Qwen3.8-27B-NVFP4-MTP-sm121` (18.6 GB, ModelOpt 0.46.0rc1, shipped `qwen3_5` recipe, BF16 MTP head merged). 0 downloads at research time; had a publication bug (incomplete 4-shard tree — verify with `final-sota-shards.sha256`).
- **Profiles:** `mtp` (MTP k=3, `--max-model-len 32768`, gmu 0.70), `ar`, `dspark` (adapted RadixArk draft, k=7), `long` (262K, **AR-only**, gmu 0.85, `--max-num-batched-tokens 8192`).
- **All profiles:** `--kv-cache-dtype fp8 --enforce-eager --no-enable-prefix-caching`.
- **Measured:** dedicated c1 27.83 (2048-tok decode, MTP k=3), ladder c8 84.28, DSpark c1 28.46 / c8 61.53. Quality gates: GSM8K 81.25%, HumanEval 39/40, IFEval 37/40, NIAH 8/8 @ 262,144.
- **Critical flags:** checkpoint ships `kv_cache_quant_algo: "FP8"` — serve **must** keep `--kv-cache-dtype fp8`, else deterministic arithmetic defect (19×23 → "417").
- **Caveats:** recommends thinking OFF (claims "no `<think>` special tokens" — contradicts official card; their own sanity suite shows `thinkon` working); no prefix caching; README's "no prefix cache on this hybrid GDN family" is contradicted by 0xBakeer's source-level finding (it *is* supported, just defaulted off); DSpark underperforms vs 0xBakeer's (different draft checkpoint + adaptation).

### 2c. MiaAI-Lab — `MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark` (SGLang)

- **Image:** official cookbook-pinned `lmsysorg/sglang:qwen38-27b` (multi-arch incl. arm64, active on Docker Hub)
- **Checkpoint:** `RadixArk/Qwen3.8-27B-NVFP4` (18.2 GB, 97K downloads) — `QUANT=nvfp4|fp8|bf16` all fit
- **Flags:** `--mem-fraction-static 0.95`, `--attention-backend flashinfer` (trtllm_mha is SM100-only), `--chunked-prefill-size 8192`, `--disable-prefill-cuda-graph`, `--kv-cache-dtype fp8_e4m3`, MTP via `--speculative-algorithm EAGLE --speculative-num-steps 3 --speculative-eagle-topk 1 --speculative-num-draft-tokens 4`, GDN state pool sized from `MAX_CONCURRENT_REQUESTS` (default 10), `--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder`
- **Context:** native 262,144 → 1M via YaRN (`YARN=1`, factor 2.0/4.0 validated) — with MTP enabled throughout
- **Measured (single stream, 400-tok essay):** MTP 16.9 tok/s thinking / 21.0 non-thinking; DSpark 16.9/16.2; DSpark+FP8 target 11.4/11.5. No aggregate numbers published; `bench.sh` referenced but not in repo.
- **Strengths:** thinking on by default (`reasoning_content`, `preserve_thinking`, per-request `reasoning_effort`), tool calling, vision live, Anthropic-compatible endpoint, RadixAttention prefix caching on by default, 68 stars/7 forks.
- **Weaknesses:** slowest published solo numbers of the three; engine is new to this stack (we run llama.cpp + vLLM).

---

## 3. Flag diff (the three vLLM/SGLang configs)

| Flag / choice | 0xBakeer (article) | r0b0tlab | MiaAI SGLang |
|---|---|---|---|
| Image | `vllm/vllm-openai:v0.27.1-aarch64` (stock) | custom `v0.27.2rc0-sm121` (GHCR) | `lmsysorg/sglang:qwen38-27b` |
| Checkpoint | FP8 (28.5 GiB) or Unsloth NVFP4 (22.6 GB) | r0b0tlab NVFP4+MTP (18.6 GB) | RadixArk NVFP4 (18.2 GB) |
| Spec decode | **DSpark k=7** (k=14 solo) | MTP k=3 | MTP EAGLE 3/1/4 |
| Prefix caching | **ON** | **OFF** (`--no-enable-prefix-caching`) | ON (RadixAttention) |
| Context | 262,144 with spec | 32,768 with spec / 262,144 AR-only | 262,144 native / 1M YaRN with spec |
| Thinking | `--reasoning-parser qwen3` | off recommended | `--reasoning-parser qwen3` |
| Tool parser | `qwen3_xml` + auto-tool-choice | `qwen3_xml` | `qwen3_coder` |
| KV cache | auto (checkpoint fp8) | fp8 **required** (flag-critical) | fp8_e4m3 explicit |
| Env vars | `VLLM_MARLIN_USE_ATOMIC_ADD=1` (4-bit only) | — | — |
| Max batched tokens | 16,384 | default / 8,192 (long) | 8,192 chunked prefill |
| Solo tok/s (best measured) | **75.0** (NVFP4 k=14) / 46.9 (FP8 k=7) | 27.8 (MTP k=3) | 21.0 (MTP, non-think) |
| c8 aggregate | 229.3 (NVFP4) / 208.7 (FP8) | 84.3 (MTP k=3) | n/p |
| c16 aggregate | **256.5** (NVFP4) / 256.1 (FP8) | n/p | n/p |

> **Methodology note (why r0b0tlab's numbers look low):** r0b0tlab's ladder uses 1024-token inputs with 256-token outputs, and `output_throughput = output_len/duration` *includes prefill time*. Prefill is ~80% of total tokens there, dragging throughput down. 0xBakeer measures decode-dominated workloads (400–3,000 output tokens) where prefill is amortized. Both 0xBakeer's FP8 RESULTS §6 and r0b0tlab's own numbers ("dedicated c1" 2048-tok decode = 27.83 vs ladder c1 256-tok = 19.22) show this effect. **Always compare like-for-like: concurrency, output length, cold/warm cache, spec decode on/off.**

---

## 4. Gotchas that cost real time (from 0xBakeer NOTES.md)

1. **Prefix caching off by default on hybrids (vLLM)** — `--enable-prefix-caching` explicitly, or it's silently off. Not caused by spec decode (that's an old-version note; 0.27.1 has no conflict).
2. **Parser names don't follow a pattern:** `--reasoning-parser qwen3` ✓ (not qwen3_xml); `--tool-call-parser qwen3_xml` ✓ (not qwen3). `qwen3_5_mtp` is deprecated → use `mtp`. Wrong name costs a full model load before failing.
3. **Thinking is on by default at high effort** — can generate tens of thousands of reasoning tokens. Send `chat_template_kwargs: {"reasoning_effort": "low"}` or `{"enable_thinking": false}`; always set `max_tokens`. Benchmarks that omit this aren't measuring decode.
4. **`VLLM_MARLIN_USE_ATOMIC_ADD=1` is mandatory on SM121 with 4-bit weights** — without it, silent incorrect output (race in Marlin kernel). CUTLASS FP4 kernels reportedly produce silent garbage on SM121 → prefer W4A16 (NVFP4) over W4A4.
5. **k is bounded twice:** KV capacity (k=8 needs 18.67 GiB KV at gmu 0.44) and batch budget (k=14 needs `--max-num-batched-tokens 16384` or startup fails with negative `max_num_scheduled_tokens`).
6. **Adaptive verification (vLLM PR #47808) does not work on this model** — GDN attention backend doesn't support on-device verification trimming; raises at KV-cache init ~6 min into startup. Architectural, not hardware-specific.
7. **Suffix decoding unavailable on vLLM 0.27.x** — gated behind `arctic-inference==0.1.1` which pins vLLM 0.10.1.
8. **Idle engines cost memory, not bandwidth** — dedicating the GPU (gmu 0.85 vs 0.44) bought no solo throughput; its only value is allowing higher k / longer context.

---

## 5. Mapping to this stack

| Item | Current (aeon-qwen36-35b) | Qwen3.8-27B candidates |
|---|---|---|
| Engine | AEON vLLM fork v0.26.0 (port 8000) | stock vLLM v0.27.1-aarch64 (0xBakeer, port 8002) or SGLang (MiaAI, port 8888) |
| Weights | NVFP4 MoE 35B-A3B (3B active) | FP8 28.5 GiB / NVFP4 18–23 GB dense |
| Context | 128K | 262K (all three recipes) / 1M (SGLang YaRN) |
| Spec decode | DFlash (disabled — deadlock) | DSpark k=7 or MTP k=3 (vLLM) / MTP EAGLE (SGLang) |
| Thinking | on ("-128k-think") | on via `--reasoning-parser qwen3` / SGLang qwen3 parser |
| Tools | auto-tool-choice | qwen3_xml (vLLM) / qwen3_coder (SGLang) |
| Speed | ~73 tok/s (DFlash off) / 164–169 (DFlash on) | 47–75 solo / 256 c16 (0xBakeer) · 17–21 (SGLang) |

**Practical notes:**

- **Ports:** r0b0tlab and the current AEON vLLM both default to 8000 (conflict if both up); 0xBakeer defaults to 8002 (free); MiaAI uses 8888 (free).
- **Integration:** all three are OpenAI-compatible → add to llama-swap as a group member (or point litellm at them). SGLang additionally serves an Anthropic-compatible endpoint (`ANTHROPIC_BASE_URL=http://host:8888`, no `/v1` suffix) for Claude Code.
- **Memory as sole model:** any of the three fits easily (20–28 GiB weights; gmu 0.85 / mem-fraction 0.95 reserve the rest). This frees the ~46 GB currently held by AEON + all llama.cpp TTL models.
- **Speed reality check:** the current main (MoE, 3B active) is 2–10× faster per token than dense 27B. If agentic capability (Terminus 73.0 vs 63.4 for Qwen3.6-27B) isn't the goal, the switch is a net speed loss.
- **DFlash precedent:** this box already had one spec-decode deadlock (AEON DFlash, 38h outage). DSpark is a different (external, cheap) drafter — but validate with a generation probe and keep the stall monitor that now does `max_tokens:1` probes, not just `/v1/models`.

---

## 6. Recommendation (single-model scenario)

1. **Primary: 0xBakeer FP8 recipe** — stock image, output-preserving, all three levers (DSpark k=7, prefix caching, 262K), 46.9 solo / 256 c16, zero quantization-quality question. Exactly what the tweet advertises, fully reproducible.
2. **If DSpark/prefix-cache quirks bite, or 1M context needed: MiaAI SGLang** — 262K–1M with MTP, thinking/tools/vision first-class, official image. Accept ~2× slower solo.
3. **r0b0tlab only for max single-stream NVFP4 decode at ≤32K context, thinking off** — a 1-day-old custom wheel + bespoke checkpoint is the wrong risk profile for a sole production model, and it leaves the two biggest levers (prefix caching, DSpark) off the table.
4. If **only** aggregate throughput matters (fleet of concurrent agents): NVFP4 ≈ FP8 at c16 → prefer FP8 for zero quality risk.

---

## 7. Sources

- Tweet: <https://x.com/0xBakeer/status/2089090318905774558> (article: `x.com/i/article/2089076470865854466`)
- FP8 recipe: <https://github.com/0xBakeer/Qwen3.8-27B-FP8-on-a-single-DGX-Spark> (README, serve.sh, RESULTS.md, NOTES.md, LIMITATIONS.md, EVAL.md)
- 4-bit comparison: <https://github.com/0xBakeer/Qwen3.8-27B-4-bit-on-a-single-DGX-Spark>
- vLLM NVFP4+MTP: <https://github.com/r0b0tlab/qwen38-27b-nvfp4-sm121-vllm> (+ HF checkpoint `r0b0tlab/Qwen3.8-27B-NVFP4-MTP-sm121`)
- SGLang: <https://github.com/MiaAI-Lab/Qwen3.8-27B-SGLang-DGX-Spark> (+ SGLang cookbook page for Qwen3.8-27B)
- Checkpoints: `Qwen/Qwen3.8-27B-FP8`, `unsloth/Qwen3.8-27B-NVFP4`, `RadixArk/Qwen3.8-27B-NVFP4`, `Doopeworld/Qwen3.8-27B-DSpark-vLLM`
- Related repos found during research: `hasso5703/dgx-spark-qwen38` (34–38 tok/s, the "38.28" figure 0xBakeer §6 references), `gitcommit90/qwen38-27b-dgx-spark`, `tonyd2wild/Qwen3.8-27B-NVFP4-DGX-Spark`
- GGUF path (not assessed here): `unsloth/Qwen3.8-27B-GGUF` (1.9M downloads) — would slot into existing llama.cpp/llama-swap without a new engine, at unknown (likely lower) throughput.
