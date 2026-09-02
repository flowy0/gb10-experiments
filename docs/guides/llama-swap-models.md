# llama-swap Models & Groups

llama-swap (port 8088) spawns llama.cpp model containers on demand. Each model has a `cmd` in `llama-swap/config.yaml`; groups hold alternative members with `swap: true`. Models load on first request per group and unload after their TTL.

## Live groups (2026-08-27, after OOM hardening)

| Group | Member(s) | Context | Purpose |
|---|---|---|---|
| **qwen38-test** | `atomicchat-qwen38-27b-mtp-262k-think-code` (AtomicChat AD-Q5_K_M-Q4_K_M + mmproj) | 262k | Qwen3.8 GGUF test path (candidate A archive) |
| **research** | `unsloth-gemma4-26b-a4b-qat-mtp2-128k-think` | 262k | Fallback — verified loads alongside the SGLang main (~30 GB headroom) |
| **compression** | `unsloth-gemma4-12b-qat-256k-mtp`, `-128k-mtp`, `unsloth-gemma4-e4b-qat-tq-128k-compression` | 256k/128k | Compression, web, titles, search |
| **embed** | `nomic-embed-text-v1.5-q4-32k` | 32k | Embeddings for the web UIs |
| **subagent** | `unsloth-gemma4-12b-qat-64k-mtp-np2`, `unsloth-gemma4-12b-q4-dflash-64k-think` | 64k | Quick sub-tasks |

Standalone models (loadable by name, not in a group): `unsloth-qwen35-4b-q4-64k-formatter`, `deepreinforce-ornith-9b-q4-64k-*` (both 64k).

> **Do NOT re-enable** the commented-out large models (Qwen3.6 27B/35B, qwen3-coder, ornith-35B, gemma4-31B, 26B DFlash) without re-testing memory co-residency with the SGLang main model. They were commented out 2026-08-17 for OOM prevention.

## Naming convention

Model IDs use the HuggingFace repo owner as the prefix:

- `radixark-` → RadixArk checkpoints (Qwen3.8 NVFP4 — current main)
- `unsloth-` → Unsloth models (Gemma4, Qwen3.6)
- `deepreinforce-` → DeepReinforce (Ornith)
- `s-batman-` / `anbeeld-` → those publishers
- Never use `unsloth-` for another provider's models.

## New-model flow

1. Add the definition to `llama-swap/config.yaml` (see config-conventions.md for indentation).
2. Add it to a test group.
3. Restart llama-swap: `docker compose restart llama-swap`.
4. Test: `curl -X POST http://localhost:8088/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"<name>","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'`
5. On failure: remove from the group, comment out the definition, note it in the CHANGELOG.
6. On success: benchmark it (benchmarking.md) and add a row to `docs/BENCHMARKS.md`.

## KV cache convention (llama.cpp)

- Always set `--cache-type-k q8_0 --cache-type-v q8_0` on non-TurboQuant models — without it llama.cpp defaults to f16 (2 bytes), doubling KV memory.
- TurboQuant models use `turbo4` (4-bit = 0.5 bytes).

## Speculative decoding notes (llama.cpp)

- `--spec-type draft-mtp --spec-draft-n-max 2` is the default for models with built-in MTP heads (most Gemma4/Qwen GGUFs include the head in the file).
- DFlash2 (`--spec-type draft-dflash`) now works in llama.cpp via upstream patch #27342 (community fork builds) — used by the GLM-5.3-Flash recipe, not by this stack's llama.cpp image.
- Old DFlash1 draft path deadlocked this box in 2026-08-11 (38h outage) — do not reintroduce `draft-dflash` with old DFlash1 drafts.
- **MTP + mmproj is compatible** (tested on the 12B QAT MTP: 63% text / 53% image acceptance). No need to split entries.

## llama.cpp + Qwen3.8 multi-turn tools

llama.cpp does not translate OpenAI `role:tool` messages for the Qwen3.8 chat template. Tool results must be sent as `role:user` content wrapped in `<tool_response>...</tool_response>`, with the preceding assistant turn as the raw `<tool_call>` XML. This applies to the qwen38-test entry; the SGLang main model uses native `role:tool`.
