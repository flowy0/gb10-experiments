# OpenCode Config — Qwen3.8-27B DFlash2 (flint server)

> Reference for the OpenCode coding agent pointed at this box's litellm endpoint (port 4000).
> Model: `radixark-qwen38-27b-nvfp4-dflash2-262k-think` (SGLang + DFlash2, safe 0.50 config, 262K, vision, thinking).

## Full config (opencode.json)

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "flint-server/radixark-qwen38-27b-nvfp4-dflash2-262k-think",
  "small_model": "flint-server/radixark-qwen38-27b-nvfp4-dflash2-262k-think",
  "provider": {
    "flint-server": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Flint Server (litellm)",
      "options": {
        "baseURL": "http://flint.home.lan:4000/v1",
        "apiKey": "none"
      },
      "models": {
        "radixark-qwen38-27b-nvfp4-dflash2-262k-think": {
          "name": "Qwen3.8 27B (DFlash2)",
          "reasoning": true,
          "attachment": true,
          "limit": {
            "context": 262144,
            "output": 8192
          },
          "modalities": {
            "input": ["text", "image"],
            "output": ["text"]
          },
          "options": {
            "reasoning_effort": "medium"
          }
        }
      }
    }
  }
}
```

## Field explanations

| Field | Value | Reason |
|---|---|---|
| `npm` | `@ai-sdk/openai-compatible` | Standard OpenAI-compatible adapter for litellm |
| `baseURL` | `http://flint.home.lan:4000/v1` | This box's litellm endpoint (replace host as needed) |
| `apiKey` | `"none"` | litellm does not check the key |
| `reasoning` | `true` | Thinking is ON by default; marks the model as reasoning-capable |
| `attachment` | `true` | Vision — the model is a VLM; images are accepted |
| `limit.context` | `262144` | Native context of the model |
| `limit.output` | `8192` | Output budget (raise to 12000–16000 only for very long outputs) |
| `modalities` | text+image in / text out | Vision support |
| `options.reasoning_effort` | `"medium"` | Controls thinking depth (litellm allows only this parameter for this model) |

## Known limits

- Thinking is ON by default (SGLang chat-template default) — no `enable_thinking` needed.
- **Do NOT add** `chat_template_kwargs` or `max_reasoning_tokens` — litellm rejects them (OpenAI-SDK path error).
- `reasoning_effort` is allowed through litellm (verified 2026-08-18). If the AI SDK ever rejects it, remove the `options` block — thinking still works at default depth.
- Truncation prevention: keep `limit.output` ≥ 4096 and use `reasoning_effort: "medium"` (xhigh measured 1,800+ reasoning tokens on hard prompts). If responses truncate, the client stream timeout may need raising (see pi reference).

## Related docs

- [PI_AGENT_CONFIG.md](./PI_AGENT_CONFIG.md) — the pi agent variant (same model, same limits)
- [main-model.md](guides/main-model.md) — main model request rules
