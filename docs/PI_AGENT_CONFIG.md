# Pi Agent Configuration — Hermes (Qwen3.8-27B main model)

> Reference for the pi coding agent ("hermes") running on a remote machine, pointed at this box's litellm endpoint (port 4000).
> Model: `radixark-qwen38-27b-nvfp4-dflash2-262k-think` (SGLang + DSpark, safe 0.50 config, 262K, vision, thinking).

## Full JSON config (pi config file — config.json)

```json
{
  "defaultThinkingLevel": "medium",
  "retry": {
    "provider": {
      "timeoutMs": 1800000
    }
  },
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000
  },
  "providers": {
    "flint-server": {
      "baseUrl": "http://flint.home.lan:4000/v1",
      "api": "openai-completions",
      "apiKey": "none",
      "models": [
        {
          "id": "radixark-qwen38-27b-nvfp4-dflash2-262k-think",
          "reasoning": true,
          "input": ["text", "image"],
          "contextWindow": 262144,
          "maxTokens": 8192,
          "samplingParams": {
            "reasoning_effort": "medium"
          }
        }
      ]
    }
  }
}
```

> Pi also accepts YAML (config.yaml) with the same structure — the field names are identical.

## Setting explanations

| Setting | Value | Reason |
|---|---|---|
| `defaultThinkingLevel` | `medium` | Thinking stays ON; moderate depth avoids token-budget loss (xhigh measured 1,800+ reasoning tokens on hard prompts). |
| `retry.provider.timeoutMs` | `1800000` (30 min) | The model generates at 20–27 tok/s. A full 8192-token response takes up to ~7 min. The SDK default timeout cut long responses ("Response was truncated before completion"). |
| `compaction.reserveTokens` | `16384` | Must be ≥ `maxTokens` (8192) so compaction never reserves too little room for the answer. |
| `compaction.keepRecentTokens` | `20000` | Recent conversation text preserved across compaction. |
| `reasoning` | `true` | Tells pi the model supports thinking (handles `reasoning_content` correctly). |
| `input` | `["text", "image"]` | Qwen3.8-27B is a VLM — vision is served natively by SGLang. |
| `contextWindow` | `262144` | Matches the model's native context; pi's default (128000) is too small. |
| `maxTokens` | `8192` | Output budget. Raise to 12000–16000 only for long documents/large code files. |
| `samplingParams.reasoning_effort` | `medium` | Controls thinking depth per request (SGLang maps it into the chat template). |

## Known limits (litellm pass-through)

- Only `reasoning_effort` is allowed through litellm for this model (`allowed_openai_params`).
- **Do NOT send** `chat_template_kwargs` or `max_reasoning_tokens` — litellm's OpenAI-SDK path rejects them (500 `AsyncCompletions.create() got an unexpected keyword argument`).
- Thinking is ON by default (SGLang chat-template default), so `enable_thinking` is not needed.
- `reasoning_effort` is effectively fixed at the samplingParams value; pi cannot change it per session via the thinking toggle (that path would need `chat_template_kwargs`, which is blocked). If per-session control is required, either raise the litellm `allowed_openai_params` for `chat_template_kwargs` (currently breaks the SDK call — needs an `extra_body` mapping) or use a second litellm model entry with a different effort.

## Truncation prevention summary

"Response was truncated before completion" had two causes, both addressed here:
1. Thinking at xhigh ate the token budget → fixed with `reasoning_effort: medium`.
2. Client stream timeout on slow long generations → fixed with `retry.provider.timeoutMs: 1800000`.

## Related docs

- Stack status / migration: [QWEN38_RESEARCH.md](./QWEN38_RESEARCH.md), [QWEN38_TESTPLAN.md](./QWEN38_TESTPLAN.md), [qwen38-test-runs/FLIP-WINNER.md](./qwen38-test-runs/FLIP-WINNER.md)
- Litellm model entry: `litellm/config.yaml` (model `radixark-qwen38-27b-nvfp4-dflash2-262k-think`, `allowed_openai_params: [reasoning_effort]`)
- Server-side concurrency/memory rules: [main-model.md](guides/main-model.md) and [crash-avoidance.md](guides/crash-avoidance.md)
