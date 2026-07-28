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

## Current Active Stack — AEON vLLM + llama-swap

| Service | Role | Tech | Port |
|---|---|---|---|
| **AEON vLLM** | Hermes (Gemma4 26B NVFP4, DFlash, 131k) | v0.25.1 | 8000 |
| **llama-swap** | Code, Subagent, Embed, Compression | llama.cpp | 8088 |
| **LiteLLM** | Unified router | proxy | 4000 |
| **Open WebUI** | Chat UI | web | 3000 |
| **Prometheus** | Metrics collection | — | 9090 |
| **Grafana** | Dashboards | — | 3001 |

See `llama-swap/docs/MEMORY.md` for memory calculations and DFlash benchmarks.

### Quick Start

```bash
docker compose up -d aeon-gemma4-26b llama-swap litellm open-webui prometheus grafana
```

## Quick Reference

- **LiteLLM API (recommended):** `http://localhost:4000/v1`
- **llama-swap API (direct):** `http://localhost:8088/v1`
- **AEON vLLM (hermes direct):** `http://localhost:8000/v1`
- **Open WebUI:** `http://localhost:3000`
- **Grafana:** `http://localhost:3001` (admin/admin)
- **Prometheus:** `http://localhost:9090`

## Hermes Speed (AEON vLLM v0.25.1)

| Model | Speed | Speculation |
|---|---|---|
| **Gemma4 26B NVFP4** | **309 tok/s** 🚀 | DFlash γ=12 + FP8 KV |
| Qwen3.6-35B-A3B (fallback) | 222 tok/s | DFlash γ=12 + FP8 KV |

## Model Groups

See `llama-swap/config.yaml` for groups. Models load on demand. AEON vLLM handles the hermes role.
