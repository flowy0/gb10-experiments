#!/usr/bin/env python3
import json
import subprocess
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Query

app = FastAPI(title="Flint Memory API", version="0.1.0")

AI_CONTAINER_KEYWORDS = [
    "llama",
    "qwen",
    "gemma",
    "granite",
    "devstral",
    "ministral",
    "mistral",
    "codestral",
    "vllm",
    "litellm",
    "librechat",
    "mongo",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 1, "", str(e)


def read_meminfo() -> dict[str, Any]:
    values: dict[str, int] = {}

    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                key = parts[0].rstrip(":")
                if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                    values[key] = int(parts[1])
    except Exception as e:
        return {"available": False, "error": str(e)}

    mem_total_kb = values.get("MemTotal", 0)
    mem_available_kb = values.get("MemAvailable", 0)
    swap_total_kb = values.get("SwapTotal", 0)
    swap_free_kb = values.get("SwapFree", 0)

    swap_used_pct = 0.0
    if swap_total_kb > 0:
        swap_used_pct = ((swap_total_kb - swap_free_kb) / swap_total_kb) * 100

    mem_used_pct = 0.0
    if mem_total_kb > 0:
        mem_used_pct = ((mem_total_kb - mem_available_kb) / mem_total_kb) * 100

    return {
        "available": True,
        "mem_total_gb": round(mem_total_kb / 1024 / 1024, 3),
        "mem_available_gb": round(mem_available_kb / 1024 / 1024, 3),
        "mem_used_pct": round(mem_used_pct, 2),
        "swap_total_gb": round(swap_total_kb / 1024 / 1024, 3),
        "swap_free_gb": round(swap_free_kb / 1024 / 1024, 3),
        "swap_used_pct": round(swap_used_pct, 2),
    }


def read_psi_memory() -> dict[str, Any]:
    result: dict[str, Any] = {
        "available": False,
        "psi_some_avg10": None,
        "psi_some_avg60": None,
        "psi_some_avg300": None,
        "psi_full_avg10": None,
        "psi_full_avg60": None,
        "psi_full_avg300": None,
    }

    try:
        with open("/proc/pressure/memory", "r") as f:
            for line in f:
                fields = {}
                for item in line.split()[1:]:
                    if "=" in item:
                        k, v = item.split("=", 1)
                        fields[k] = v

                if line.startswith("some"):
                    result["psi_some_avg10"] = float(fields.get("avg10", 0.0))
                    result["psi_some_avg60"] = float(fields.get("avg60", 0.0))
                    result["psi_some_avg300"] = float(fields.get("avg300", 0.0))
                elif line.startswith("full"):
                    result["psi_full_avg10"] = float(fields.get("avg10", 0.0))
                    result["psi_full_avg60"] = float(fields.get("avg60", 0.0))
                    result["psi_full_avg300"] = float(fields.get("avg300", 0.0))

        result["available"] = True
    except Exception as e:
        result["error"] = str(e)

    return result


def docker_stats(all_containers: bool = False) -> list[dict[str, Any]]:
    code, out, err = run_cmd(
        ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
        timeout=15,
    )

    if code != 0:
        return [{"available": False, "error": err.strip()}]

    rows = []

    for line in out.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue

        name = item.get("Name", "")

        if not all_containers:
            if not any(k in name.lower() for k in AI_CONTAINER_KEYWORDS):
                continue

        rows.append(
            {
                "name": name,
                "container": item.get("Container", ""),
                "cpu_perc": item.get("CPUPerc", ""),
                "mem_usage": item.get("MemUsage", ""),
                "mem_perc": item.get("MemPerc", ""),
                "net_io": item.get("NetIO", ""),
                "block_io": item.get("BlockIO", ""),
                "pids": item.get("PIDs", ""),
            }
        )

    return rows


def recent_oom_events(minutes: int = 10) -> dict[str, Any]:
    code, out, err = run_cmd(
        [
            "journalctl",
            "-k",
            "--since",
            f"{minutes} minutes ago",
            "--no-pager",
        ],
        timeout=10,
    )

    if code != 0:
        return {
            "available": False,
            "oom_recent": False,
            "matches": [],
            "error": err.strip(),
        }

    matches = []

    for line in out.splitlines():
        lower = line.lower()
        if "out of memory" in lower or "oom" in lower or "killed process" in lower:
            matches.append(line[-500:])

    return {
        "available": True,
        "oom_recent": bool(matches),
        "matches": matches[-10:],
    }


def classify_pressure(meminfo: dict[str, Any], psi: dict[str, Any], oom: dict[str, Any]) -> dict[str, Any]:
    reasons = []
    level = "ok"

    mem_available = meminfo.get("mem_available_gb")
    psi_some = psi.get("psi_some_avg10")
    psi_full = psi.get("psi_full_avg10")
    swap_used = meminfo.get("swap_used_pct")

    if oom.get("oom_recent"):
        level = "critical"
        reasons.append("recent OOM event detected")

    if isinstance(mem_available, (int, float)):
        if mem_available < 12:
            level = "critical"
            reasons.append("MemAvailable below 12GB")
        elif mem_available < 24 and level == "ok":
            level = "watch"
            reasons.append("MemAvailable below 24GB")

    if isinstance(psi_full, (int, float)) and psi_full > 1:
        level = "critical"
        reasons.append("PSI full avg10 above 1")

    if isinstance(psi_some, (int, float)) and psi_some > 5:
        if level != "critical":
            level = "watch"
        reasons.append("PSI some avg10 above 5")

    if isinstance(swap_used, (int, float)) and swap_used > 10:
        if level != "critical":
            level = "watch"
        reasons.append("swap usage above 10%")

    return {
        "level": level,
        "reasons": reasons,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "flint-memory-api",
        "timestamp": now_iso(),
    }


@app.get("/memory")
def memory(
    all_containers: bool = Query(False, description="Include all Docker containers instead of AI-related containers only"),
    oom_minutes: int = Query(10, ge=1, le=1440),
) -> dict[str, Any]:
    meminfo = read_meminfo()
    psi = read_psi_memory()
    oom = recent_oom_events(minutes=oom_minutes)

    return {
        "timestamp": now_iso(),
        "host": "flint",
        "meminfo": meminfo,
        "psi_memory": psi,
        "oom": oom,
        "containers": docker_stats(all_containers=all_containers),
        "pressure": classify_pressure(meminfo, psi, oom),
    }


@app.get("/memory/summary")
def memory_summary() -> dict[str, Any]:
    meminfo = read_meminfo()
    psi = read_psi_memory()
    oom = recent_oom_events(minutes=10)
    containers = docker_stats(all_containers=False)

    return {
        "timestamp": now_iso(),
        "mem_available_gb": meminfo.get("mem_available_gb"),
        "mem_total_gb": meminfo.get("mem_total_gb"),
        "swap_used_pct": meminfo.get("swap_used_pct"),
        "psi_some_avg10": psi.get("psi_some_avg10"),
        "psi_full_avg10": psi.get("psi_full_avg10"),
        "oom_recent": oom.get("oom_recent"),
        "pressure": classify_pressure(meminfo, psi, oom),
        "containers": containers,
    }
