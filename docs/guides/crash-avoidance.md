# Crash Avoidance (OOM & Cascade Failure)

The most important operational knowledge for this box. A GPU OOM here does not just kill a container — it can lock up the entire system and require a hard reboot.

## The cascade pattern

1. GPU runs out of memory → NVIDIA UVM swaps GPU memory to system RAM
2. System RAM fills → journald/dockerd/sshd stall
3. llama-server processes block on NVIDIA driver locks (122s+)
4. SSH becomes unresponsive → hard reboot required

## Signs of a cascade

- `NVRM: Xid ... Graphics Exception` in `dmesg`
- `NV_ERR_NO_MEMORY` in kernel logs
- `Under memory pressure, flushing caches` in journald
- `task:...blocked for more than 122 seconds`
- SSH drops while the machine is powered on

Check with: `journalctl -k --since "10 minutes ago" | grep -cE "NV_ERR|Xid"` — this must be 0 before loading another model.

## Prevention rules

- **The SGLang main model reserves ~76 GB at `mem-fraction-static 0.50`.** Do not raise it (freeze risk above 0.50 — see main-model.md).
- **Load one llama.cpp model at a time** — let it cold start (~5–30s) before requesting another.
- **Keep total host usage below ~110 GB** of 128 GB.
- **One large llama.cpp model fits with the main model** (91/121 GB used, ~30 GB free). Two large models = danger.
- **Don't run concurrent benchmark/soak workloads with extra models loaded.**
- **If the system feels sluggish, stop unused llama-swap containers immediately:**
  ```bash
  docker ps --filter name=ls- --format '{{.Names}}' | xargs docker rm -f
  ```
- **GPU health monitor:** `/opt/atom/scripts/gpu-health.sh` watches for Xid errors (its restart target is stale — vLLM-era; review before relying on it).

## Memory envelope (SGLang era, current)

| Scenario | Total used | Free |
|---|---|---|
| Main model only (0.50) | ~71 GB | **~50 GB** ✅ |
| + one large llama.cpp model (≤26B) | ~91 GB | **~30 GB** ✅ |
| + two large llama.cpp models | ~115 GB | ⚠️ danger line |
| + three | 120+ GB | ❌ crash risk |

Historical vLLM-era numbers (46 GB reserve etc.) live in [vllm-reference.md](vllm-reference.md).

## If locked out

- Hard power cycle (hold the power button).
- After reboot, check `journalctl -k | grep NVRM` for Xid errors before loading workloads.
- Don't immediately restart the workload that crashed — the GPU driver may need a cold boot.
- Expect `NV_ERR_NO_MEMORY` transients after an OOM; vLLM/SGLang retry allocations and usually recover on the next boot.
