# Hermes Agent — Model Setup Summary

## Server
- **URL:** http://flint.home.lan:8088/v1
- **API:** OpenAI-compatible
- **Hardware:** NVIDIA GB10 (122 GB unified VRAM)

## Recommended Model
`unsloth-qwen36-35b-a3b-q2-256k-thinking-code`
- Context: 262,144 tokens
- Temp: 0.6 (coding-optimized thinking)
- Reasoning budget: 16,384 (prevents thinking loops)
- KV cache: q8_0 (full precision, reliable at 256k)
- Group: code

## Why this model
- Qwen3.6 MoE (~3B active params) — fast inference
- Most stable across benchmarks (fin-research 4.80 at all context sizes)
- Capped reasoning budget preserves context for actual conversation
- Proven tool-calling support
- No flash-attention (unstable at 256k on this build)

## Alternative Models (separate groups, run simultaneously)

| Model | Group | Context | Notes |
|---|---|---|---|
| `unsloth-gemma4-12b-q5-256k-think` | research | 256k | Lighter Gemma alternative |
| `unsloth-gemma4-26b-a4b-q5-256k-fa-think` | stable | 256k | Higher quality Gemma |

## Pi Config
```json
{
  "id": "unsloth-qwen36-35b-a3b-q2-256k-thinking-code",
  "contextWindow": 262144,
  "maxTokens": 8192
}
```
