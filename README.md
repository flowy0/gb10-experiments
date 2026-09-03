# Flint — Local AI Stack

*A DGX Spark (GB10) running a local Qwen3.8-27B main model, helper models, chat UI, and coding-agent endpoints — all on the home network.*

## Quick summary

| | |
|---|---|
| **Main model** | `radixark-qwen38-27b-nvfp4-dflash2-262k-think` — Qwen3.8-27B (NVFP4), thinking + vision + tools, 262K context |
| **Engine** | SGLang (port 8888) → LiteLLM router (port 4000) |
| **Chat UI** | Open Web UI — `https://chat.testerlab.online` (LAN only, real certificate) |
| **Helper models** | llama-swap (port 8088): research 26B, compression, subagent, embeddings |
| **The one rule** | One large helper model at a time — overloading the box can freeze it |

**Start everything:** `docker compose up -d`

## Contents

- [Quick reference](#quick-reference)
- [Services](#services)
- [Main model](#main-model)
- [Model groups (llama-swap)](#model-groups-llama-swap)
- [Known issues](#known-issues)
- [Documentation](#documentation)

## Quick reference

- **LiteLLM API (recommended):** `http://localhost:4000/v1`
- **SGLang API (direct):** `http://localhost:8888/v1` (Anthropic-compatible at `/v1/messages`)
- **llama-swap API:** `http://localhost:8088/v1`
- **Open Web UI:** `https://chat.testerlab.online` (LAN) or `http://localhost:3000`
- **Grafana:** `http://localhost:3001` · **Prometheus:** `http://localhost:9090`

## Services

| Service | Role | Port |
|---|---|---|
| **SGLang** | Main model — `radixark-qwen38-27b-nvfp4-dflash2-262k-think` | 8888 |
| **LiteLLM** | Unified router for all clients | 4000 |
| **llama-swap** | On-demand llama.cpp models | 8088 |
| **Open Web UI** | Chat website for humans | 3000 |
| **Caddy** | LAN reverse proxy + HTTPS certificate | 80 / 443 |
| **Prometheus** | Metrics collection | 9090 |
| **Grafana** | Dashboards | 3001 |

> The stack flipped from AEON vLLM (Qwen3.6-35B) to SGLang + Qwen3.8-27B on 2026-08-17; DFlash2 became the draft on 2026-08-20. History: [research](docs/QWEN38_RESEARCH.md), [test plan](docs/QWEN38_TESTPLAN.md). AEON is retired (never deleted — see [HISTORICAL](docs/HISTORICAL.md)).

## Main model

- **Name:** `radixark-qwen38-27b-nvfp4-dflash2-262k-think` (Qwen3.8-27B NVFP4 + DFlash2, 262K, vision, thinking)
- **Speed (measured):** ~20–31 tok/s solo on fresh codegen; higher on edit/math workloads; up to ~223 tok/s at 16 concurrent (4-slot cap)
- **Thinking:** ON by default — budget `max_tokens` (≥1000–2000) or set `reasoning_effort`
- **Full rules:** [docs/guides/main-model.md](docs/guides/main-model.md)

## Model groups (llama-swap)

Active: `research` (26B QAT MTP), `compression`, `subagent`, `embed`, `qwen38-test` — all ≤26B. Models wake on request and sleep on TTL. The main model is always resident. Old large models were commented out (2026-08-17) to prevent memory overload. See [llama-swap models guide](docs/guides/llama-swap-models.md).

## Known issues

- **GPU cascade failure** — an overload can lock the whole machine (SSH dies, hard reboot needed). Prevention and recovery: [crash-avoidance guide](docs/guides/crash-avoidance.md).
- **Open Web UI after upgrade** — the page may flash or look broken. Fix: hard refresh (`Ctrl+Shift+R`) or clear the browser cache.
- **Open Web UI sessions** — users log in again after a container restart. Content is always stored.

## Documentation

### Orientation
| Doc | What it is |
|---|---|
| [FLINT_OVERVIEW](docs/FLINT_OVERVIEW.md) | Plain-language summary — what the box is and does |
| [QUICK_CMDS](docs/QUICK_CMDS.md) | Common commands: restarts, test curls, benchmarks |
| [HISTORICAL](docs/HISTORICAL.md) | Previous stack configurations |

### Operation guides (read before the task)
| Guide | When to read |
|---|---|
| [config-conventions](docs/guides/config-conventions.md) | editing any YAML config |
| [git-workflow](docs/guides/git-workflow.md) | every change (commit + changelog) |
| [main-model](docs/guides/main-model.md) | main model requests, SGLang operations |
| [llama-swap-models](docs/guides/llama-swap-models.md) | llama-swap models and groups |
| [crash-avoidance](docs/guides/crash-avoidance.md) | memory envelope, OOM risk |
| [monitoring](docs/guides/monitoring.md) | prometheus, grafana, stall monitor |
| [benchmarking](docs/guides/benchmarking.md) | performance tests and harness |
| [reverse-proxy](docs/guides/reverse-proxy.md) | Caddy / HTTPS for Open Web UI |
| [vllm-reference](docs/guides/vllm-reference.md) | historical vLLM knowledge (not used) |

### Client configurations
| Doc | What it is |
|---|---|
| [PI_AGENT_CONFIG](docs/PI_AGENT_CONFIG.md) | pi (Hermes) agent config |
| [OPENCODE_CONFIG](docs/OPENCODE_CONFIG.md) | OpenCode agent config |

### Model research and benchmarks
| Doc | What it is |
|---|---|
| [QWEN38_RESEARCH](docs/QWEN38_RESEARCH.md) | Qwen3.8 implementation research |
| [QWEN38_TESTPLAN](docs/QWEN38_TESTPLAN.md) | candidate test plan and methodology |
| [BENCHMARKS](docs/BENCHMARKS.md) | tok/s and tool-eval scores |
| [llama-cpp-turboquant](docs/llama-cpp-turboquant.md) | TurboQuant notes |
| [CUDA_GRAPHS](docs/CUDA_GRAPHS.md) | CUDA graphs explanation |
| [VLLM](docs/VLLM.md) | AEON vLLM history (retired) |
