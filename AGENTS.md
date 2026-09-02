# /opt/atom — Local AI Stack

Docker-compose orchestration of a local AI inference stack on one NVIDIA DGX Spark (GB10, 128 GB unified memory): **SGLang** serves the main model (Qwen3.8-27B NVFP4 + DFlash2), **llama-swap** serves on-demand llama.cpp models, **litellm** routes to clients. All services are compose-managed.

## Rules that apply to every task

1. **Config integrity** — never delete model definitions; comment them out with `# `. Validate YAML after every edit. When adding entries near existing ones, use exact text match, not line numbers.
2. **Git** — commit and push after every change; add a dated entry to `CHANGELOG.md`. Check `git diff --stat` before committing.
3. **Main model** — `radixark-qwen38-27b-nvfp4-dflash2-262k-think` on SGLang port 8888, exposed via litellm port 4000. Thinking is ON by default: budget `max_tokens` (≥1000–2000) or set `reasoning_effort`, or responses come back empty.
4. **Memory safety** — the box can hard-freeze if overloaded (GPU OOM → system lockup). Load one large model at a time; keep host usage below ~110 GB. **vLLM is not used on this box** (two driver OOMs; details in [vllm-reference.md](docs/guides/vllm-reference.md)).
5. **YAML indentation** — each config file has its own layout. Read [config-conventions.md](docs/guides/config-conventions.md) before editing compose/llama-swap/litellm files.

## Guides — read the relevant one before the task

| Guide | When to read |
|---|---|
| [config-conventions.md](docs/guides/config-conventions.md) | editing any YAML config |
| [git-workflow.md](docs/guides/git-workflow.md) | every change |
| [main-model.md](docs/guides/main-model.md) | requests to the main model, SGLang ops |
| [llama-swap-models.md](docs/guides/llama-swap-models.md) | llama-swap models/groups |
| [crash-avoidance.md](docs/guides/crash-avoidance.md) | loading models, OOM risk |
| [monitoring.md](docs/guides/monitoring.md) | prometheus/grafana/stall monitor |
| [benchmarking.md](docs/guides/benchmarking.md) | performance tests |
| [vllm-reference.md](docs/guides/vllm-reference.md) | historical vLLM knowledge (not currently used) |

## Project map

| File / dir | Purpose |
|---|---|
| `llama-swap/config.yaml` | model definitions + groups — **most important config** |
| `docker-compose.yml` | service orchestration |
| `litellm/config.yaml` | client routing (model list) |
| `CHANGELOG.md` | change history |
| `README.md` | stack overview |
| `docs/` | research, run cards, agent configs, guides |
| `scripts/` | benchmark harness + ops scripts |
