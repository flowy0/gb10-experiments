# Changelog

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
