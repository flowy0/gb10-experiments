# Monitoring

## Stack

- **Prometheus** — port 9090. Scrapes SGLang, llama-swap, and itself. No auth. Fixed LAN address: `https://prometheus.testerlab.online` (Caddy + Let's Encrypt via Cloudflare DNS-01; LAN-only by topology — see reverse-proxy.md). Raw API stays at `http://127.0.0.1:9090` and `http://<lan-ip>:9090`.
- **Grafana** — port 3001. Login required. Service-account key in `.env` as `GRAFANA_SA_KEY`.
- **Stall monitor** — user systemd timer (`stall-monitor.timer`), runs `/opt/atom/scripts/stall-monitor.sh` every ~30 min.

## Prometheus targets

Defined in `prometheus/prometheus.yml`:
- `sglang` job → `sglang-qwen38:8888` (main model)
- `llama-swap` job → `llama-swap:8080`
- self → localhost:9090
- (the old `vllm` job on 172.18.0.1:8000 is stale — vLLM is not running; see vllm-reference.md)

## Grafana dashboards

- **LLM Stack** (uid `llm-stack`) is file-provisioned from `prometheus/dashboards/llm-stack.json` (source of truth; Grafana hot-reloads file changes ~30s). Panels: llama-swap System Memory, Running Requests, Queue Depth, Generation Throughput, Prefix Cache Hit Rate, DFlash Acceptance Rate, DFlash Accept Length, Memory Pool Usage, SGLang GPU Memory by Pool.
- To update a provisioned dashboard: edit the JSON file (then Grafana picks it up) — the API refuses writes to provisioned dashboards.

## Metrics available

- **SGLang:** serves native Prometheus metrics at `:8888/metrics` (requires `--enable-metrics` in the launch args — added 2026-09-04). Key series (all carry `model_name`): `sglang:num_running_reqs`, `sglang:num_queue_reqs`, `sglang:gen_throughput` (windowed — only moves under load), `sglang:cache_hit_rate` (0–1), `sglang:spec_accept_rate` (0–1), `sglang:spec_accept_length`, `sglang:token_usage`/`sglang:mamba_usage` (0–1), `sglang:kv_cache_memory_usage_gb`, `sglang:graph_memory_usage_gb` (per phase). Engine logs additionally carry per-batch detail; `scripts/monitor-sglang-toks.sh` samples them to `/tmp/sglang-toks.csv` every 10s.
- **Prometheus config reload:** the config file is bind-mounted but not watched — after editing `prometheus/prometheus.yml`, run `docker kill -s HUP prometheus`.
- **llama-swap:** `llamaswap_memory_used_bytes`, `llamaswap_memory_free_bytes`, `llamaswap_cpu_util_percent` (per core), `llamaswap_load_average`.
- Historical vLLM metrics (`vllm:spec_decode_*`, `vllm:num_requests_*`) live in vllm-reference.md — not scrapeable now.

## Stall monitor behavior

- Scores signals: D-state processes, blocked procs (loadavg), kernel alerts (`NVRM|Xid|NV_ERR|blocked for more|hung.task`), memory pressure, available-memory %, SSH reachability, and a **model generation probe**.
- The generation probe is mandatory for SGLang — `/v1/models` answers before the engine is ready (see main-model.md).
- Restart action: `docker compose restart <MONITOR_CONTAINER>` (graceful — the correct SGLang recovery path).
- Defaults (target the main model): `MONITOR_PORT=8888 MONITOR_MODEL=radixark-qwen38-27b-nvfp4-dflash2-262k-think MONITOR_CONTAINER=sglang-qwen38`.
- Log: `/tmp/stall-monitor.log`. Pause during deliberate maintenance: `systemctl --user stop stall-monitor.timer`; resume with `start`.

## Health checks

- SGLang direct: `curl http://127.0.0.1:8888/v1/models` (API) + a real generation request with `reasoning_effort` and enough `max_tokens` (the empty-content trap).
- litellm route: `curl http://127.0.0.1:4000/v1/models` — the main model must appear.
- Kernel: `journalctl -k --since "10 minutes ago" | grep -cE "NV_ERR|Xid"` → 0.
