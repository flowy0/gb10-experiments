## Core Services

| File/Dir | Purpose |
|---|---|
| `llama-swap/` | Model router config (`config.yaml`) and swap definitions |
| `llama-swap/docs/MEMORY.md` | Memory planning with architectures and DFlash benchmarks |
| `docs/BENCHMARKS.md` | tok/s and tool-eval scores |
| `prometheus/` | Prometheus + Grafana monitoring stack |
| `scripts/` | GPU health monitor, stall monitor |
| `litellm/` | LiteLLM router config (active) |
| `open-webui/` | Chat UI data |
| `docs/VLLM.md` | vLLM build history (deprecated spark build) |
| `docs/HISTORICAL.md` | Previous stack configurations |
| `docker-compose.yml` | Main compose file — launches all services |

## Known Issues

### GPU Cascade Failure

GPU OOM can cascade into a system-wide stall (SSH dies, requires hard reboot).
See `AGENTS.md` for full diagnosis and recovery procedures.

### Open WebUI — Browser Cache After Upgrade

After upgrading Open WebUI, the UI may flash or appear broken.
**Fix:** Hard refresh (`Ctrl+Shift+R` / `Cmd+Shift+R`) or clear browser cache.

---

See [docs/HISTORICAL.md](docs/HISTORICAL.md) for previous stack configurations.

## Current Active Stack — SGLang (Qwen3.8-27B) + llama-swap

| Service | Role | Tech | Port |
|---|---|---|---|
| **SGLang** | **Main model — `radixark-qwen38-27b-nvfp4-dspark-262k-think` (Qwen3.8-27B NVFP4 + DSpark, 262K, vision, thinking)** | SGLang (safe 0.50 config) | 8888 |
| **llama-swap** | Code, Research, Subagent, Embed, Compression | llama.cpp | 8088 |
| **LiteLLM** | Unified router | proxy | 4000 |
| **Open WebUI** | Chat UI | web | 3000 |
| **Prometheus** | Metrics collection | — | 9090 |
| **Grafana** | Dashboards | — | 3001 |

> **2026-08-17:** Stack flipped from AEON vLLM (Qwen3.6-35B) to SGLang + Qwen3.8-27B.
> Full decision history: [docs/QWEN38_RESEARCH.md](docs/QWEN38_RESEARCH.md) + [docs/QWEN38_TESTPLAN.md](docs/QWEN38_TESTPLAN.md) + [docs/qwen38-test-runs/FLIP-WINNER.md](docs/qwen38-test-runs/FLIP-WINNER.md).
> The AEON service is retired (commented in docker-compose.yml, never deleted) — see [docs/HISTORICAL.md](docs/HISTORICAL.md).

### Quick Start

```bash
docker compose up -d sglang-qwen38 llama-swap litellm open-webui prometheus grafana
```

## Quick Reference

- **LiteLLM API (recommended):** `http://localhost:4000/v1` — main model: `radixark-qwen38-27b-nvfp4-dspark-262k-think`
- **SGLang API (direct):** `http://localhost:8888/v1` (also Anthropic-compatible at `/v1/messages`)
- **llama-swap API (direct):** `http://localhost:8088/v1`
- **Open WebUI:** `http://localhost:3000`
- **Grafana:** `http://localhost:3001`
- **Prometheus:** `http://localhost:9090`

## Main Model Speed (SGLang + Qwen3.8-27B — measured on this box)

| Config | Solo | c16 aggregate | Notes |
|---|---|---|---|
| DSpark k7 @ safe 0.50 (current) | ~20–27 tok/s | ~188–291 | fresh-codegen 20.3, math/eval 34–38 (hasso5703) |
| MTP (one-flag alternative) | ~24.5 @0.50 | ~291 @0.85 | better on fresh codegen |

Retired AEON (Qwen3.6-35B-A3B) reference: 164–169 tok/s with DFlash (MoE, 3B active — not comparable to dense 27B).

## Model Groups

Active groups (llama-swap): `research` (26B QAT MTP), `compression`, `subagent`, `embed`, `qwen38-test` — all ≤26B.
Old large models (Qwen3.6 27B/35B, Ornith-35B, Gemma4-31B, Qwen3-Coder, 26B DFlash) were commented out 2026-08-17 to prevent memory overload alongside the SGLang main model. See `llama-swap/config.yaml`. Models load on demand; the main model is always resident on SGLang (8888).
