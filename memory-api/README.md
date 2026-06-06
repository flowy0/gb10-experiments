````markdown
# Flint Memory API

A lightweight FastAPI service that runs on **Flint** and exposes host/container memory telemetry for remote benchmark clients.

This is useful when benchmarks are run from another machine, such as a MacBook, because the OpenAI-compatible LLM API does **not** expose Docker memory, host memory, PSI memory pressure, or OOM events.

## Purpose

The benchmark client can measure:

- response quality
- latency
- token usage
- HTTP errors
- model output

But only Flint can measure:

- Docker container memory
- system `MemAvailable`
- swap usage
- Linux PSI memory pressure
- recent OOM events
- active AI container CPU/memory usage

This service bridges that gap by exposing memory telemetry over HTTP.

---

## Architecture

```text
Client benchmark machine
  └── run_bench.py
        ├── sends LLM requests to Flint
        ├── polls Flint Memory API
        └── records memory summary per task

Flint
  ├── llama-swap / llama.cpp / LiteLLM / LibreChat
  └── Flint Memory API
        ├── reads /proc/meminfo
        ├── reads /proc/pressure/memory
        ├── runs docker stats
        ├── checks recent OOM logs
        └── exposes HTTP endpoints
````

---

## Service location

Recommended install path:

```bash
/opt/atom/memory-api
```

Files:

```text
/opt/atom/memory-api/
├── app.py
├── pyproject.toml
└── uv.lock
```

Systemd service:

```text
/etc/systemd/system/flint-memory-api.service
```

---

## Endpoints

### Health check

```http
GET /health
```

Example:

```bash
curl -s http://flint.home.lan:8099/health | jq
```

Example response:

```json
{
  "ok": true,
  "service": "flint-memory-api",
  "timestamp": "2026-05-04T09:30:00.000000+00:00"
}
```

---

### Memory summary

```http
GET /memory/summary
```

Recommended endpoint for benchmark polling.

Example:

```bash
curl -s http://flint.home.lan:8099/memory/summary | jq
```

Example response:

```json
{
  "timestamp": "2026-05-04T09:30:00.000000+00:00",
  "mem_available_gb": 72.1,
  "mem_total_gb": 119.7,
  "swap_used_pct": 0.0,
  "psi_some_avg10": 0.0,
  "psi_full_avg10": 0.0,
  "oom_recent": false,
  "pressure": {
    "level": "ok",
    "reasons": []
  },
  "containers": [
    {
      "name": "ls-unsloth-qwen3-coder-30b-a3b-q4-64k",
      "container": "abc123",
      "cpu_perc": "98.2%",
      "mem_usage": "18.2GiB / 119.7GiB",
      "mem_perc": "15.2%",
      "net_io": "1.2MB / 3.4MB",
      "block_io": "0B / 0B",
      "pids": "42"
    }
  ]
}
```

---

### Full memory report

```http
GET /memory
```

Example:

```bash
curl -s http://flint.home.lan:8099/memory | jq
```

This returns a fuller object containing:

```text
meminfo
psi_memory
oom
containers
pressure
```

Use this for debugging. Use `/memory/summary` for benchmark polling.

---

## Install

### 1. Create folder

```bash
mkdir -p /opt/atom/memory-api
cd /opt/atom/memory-api
```

### 2. Create `pyproject.toml`

```toml
[project]
name = "flint-memory-api"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
]
```

### 3. Sync dependencies

```bash
uv sync
```

If `uv` is not installed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version
```

---

## Run manually

From Flint:

```bash
cd /opt/atom/memory-api
uv run uvicorn app:app --host 0.0.0.0 --port 8099
```

Test locally:

```bash
curl -s http://localhost:8099/health | jq
curl -s http://localhost:8099/memory/summary | jq
```

Test from client machine:

```bash
curl -s http://flint.home.lan:8099/memory/summary | jq
```

---

## Run with systemd

Create service file:

```bash
sudo nano /etc/systemd/system/flint-memory-api.service
```

Recommended service:

```ini
[Unit]
Description=Flint Memory API
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=g
WorkingDirectory=/opt/atom/memory-api
Environment="PATH=/home/g/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/g/.local/bin/uv run uvicorn app:app --host 0.0.0.0 --port 8099
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

If `uv` is installed somewhere else, check with:

```bash
which uv
```

Then update `ExecStart`.

Reload systemd:

```bash
sudo systemctl daemon-reload
```

Start service:

```bash
sudo systemctl start flint-memory-api.service
```

Enable at boot:

```bash
sudo systemctl enable flint-memory-api.service
```

Or start and enable together:

```bash
sudo systemctl enable --now flint-memory-api.service
```

Check status:

```bash
systemctl status flint-memory-api.service
```

View logs:

```bash
journalctl -u flint-memory-api.service -f
```

Restart after editing `app.py`:

```bash
sudo systemctl restart flint-memory-api.service
```

---

## Common systemd issue: `uv` not found

If logs show:

```text
/usr/bin/env: ‘uv’: No such file or directory
```

systemd cannot see your user shell PATH.

Fix by using the full path to `uv`:

```bash
which uv
```

Example result:

```text
/home/g/.local/bin/uv
```

Then set:

```ini
ExecStart=/home/g/.local/bin/uv run uvicorn app:app --host 0.0.0.0 --port 8099
```

Also include:

```ini
Environment="PATH=/home/g/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart flint-memory-api.service
```

---

## Memory pressure interpretation

The API returns:

```json
"pressure": {
  "level": "ok",
  "reasons": []
}
```

Pressure levels:

| Level      | Meaning                            |
| ---------- | ---------------------------------- |
| `ok`       | Memory looks healthy               |
| `watch`    | Memory pressure is developing      |
| `critical` | OOM risk or serious stall detected |

Suggested thresholds:

| Signal           |    Watch |            Critical |
| ---------------- | -------: | ------------------: |
| `MemAvailable`   | `< 24GB` |            `< 12GB` |
| PSI `some avg10` |    `> 5` |                   — |
| PSI `full avg10` |        — |               `> 1` |
| Swap used        |  `> 10%` | depends on workload |
| OOM event        |        — |      any recent OOM |

---

## Benchmark integration

Set these environment variables on the benchmark client:

```bash
export FLINT_MEMORY_API_ENABLED=1
export FLINT_MEMORY_API_URL=http://flint.home.lan:8099
export FLINT_MEMORY_API_INTERVAL=2
```

Then run the benchmark:

```bash
uv run python run_bench.py \
  --models qwen3-coder-30b-a3b-q4-64k granite-4.1-8b-q5-64k \
  --tiers 64k
```

When enabled, the benchmark should:

1. Check `/health`.
2. Start polling `/memory/summary` before each task.
3. Poll every `FLINT_MEMORY_API_INTERVAL` seconds.
4. Stop polling after the task finishes.
5. Summarize memory samples into the result row.

Suggested result fields:

```text
memory_api_enabled
memory_api_available
memory_api_error
memory_api_samples
min_mem_available_gb
max_mem_used_pct
max_swap_used_pct
max_psi_some_avg10
max_psi_full_avg10
oom_seen
memory_pressure_level
memory_pressure_reasons
peak_container_mem_gib
peak_container_mem_name
```

---

## Running without memory telemetry

To disable memory telemetry:

```bash
unset FLINT_MEMORY_API_ENABLED
```

Or:

```bash
export FLINT_MEMORY_API_ENABLED=0
```

The benchmark should continue normally and mark memory fields as unavailable.

---

## Security notes

This API exposes host/container information.

Do **not** expose it to the public internet.

Recommended access patterns:

```text
LAN only
Tailscale only
Trusted VLAN only
```

If you want to bind only to Tailscale, find Flint’s Tailscale IP:

```bash
tailscale ip -4
```

Then change systemd:

```ini
ExecStart=/home/g/.local/bin/uv run uvicorn app:app --host 100.x.y.z --port 8099
```

Restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart flint-memory-api.service
```

---

## Troubleshooting

### Service is not running

```bash
systemctl status flint-memory-api.service
journalctl -u flint-memory-api.service -n 100 --no-pager
```

### Start manually

```bash
cd /opt/atom/memory-api
uv run uvicorn app:app --host 0.0.0.0 --port 8099
```

### Port is already in use

```bash
sudo ss -ltnp | grep 8099
```

### Docker stats error

Check Docker access for user `g`:

```bash
docker ps
```

If permission denied, add user to Docker group:

```bash
sudo usermod -aG docker g
```

Then log out/in or reboot.

### `/memory/summary` works locally but not from client

Check service bind address:

```bash
sudo ss -ltnp | grep 8099
```

Check name resolution:

```bash
ping flint.home.lan
```

Try direct IP:

```bash
curl -s http://<flint-ip>:8099/health | jq
```

---

## Useful commands

Start:

```bash
sudo systemctl start flint-memory-api.service
```

Stop:

```bash
sudo systemctl stop flint-memory-api.service
```

Restart:

```bash
sudo systemctl restart flint-memory-api.service
```

Enable on boot:

```bash
sudo systemctl enable flint-memory-api.service
```

Disable on boot:

```bash
sudo systemctl disable flint-memory-api.service
```

View logs:

```bash
journalctl -u flint-memory-api.service -f
```

Test endpoint:

```bash
curl -s http://flint.home.lan:8099/memory/summary | jq
```

---

## Expected usage

For normal benchmark runs:

```text
1. Ensure service is running on Flint.
2. Enable memory polling on client.
3. Run benchmark.
4. Compare:
   - model score
   - coverage
   - latency
   - min MemAvailable
   - max PSI
   - peak container memory
   - pressure level
```

Example comparison:

```text
Model                                Score  Coverage  Wall(s)  MinMemGB  MaxPSI  PeakGiB  Pressure
qwen3-coder-30b-a3b-q4-64k           4.50   8/8       573      61.2      0.0     18.4     ok
granite-4.1-8b-q5-64k                4.38   8/8       709      72.8      0.0     7.9      ok
```

---

## Design principle

The Memory API is optional telemetry.

Benchmark correctness must not depend on it.

If the API is unavailable:

```text
benchmark should continue
memory_api_available=false
memory fields should be null
results should still be valid
```

```
```
