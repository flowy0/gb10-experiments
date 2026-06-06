#!/usr/bin/env python3
"""Flint v3 long-context benchmark harness.

Improvements over v2 / earlier longctx_bench.py:
- Uses generated 32K/64K/128K prompt files and answer_keys.json.
- Scores responses deterministically using scorer.py.
- Saves raw prompt copy, raw response JSON, response text, summary CSV, run JSON.
- Samples Docker memory, system MemAvailable, swap, and PSI memory pressure.
- Captures API usage tokens when the backend returns them.
- Supports --models, --tasks, --tiers, --no-unload, --dry.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from scorer import score as score_response

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"
PROMPTS = BASE / "prompts" / "generated"
ANSWER_KEYS = PROMPTS / "answer_keys.json"
LLAMA_SWAP_UNLOAD_URL = "http://localhost:8088/models/unload"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_cmd(cmd: list[str], timeout: int = 20) -> tuple[int, str, str]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 999, "", str(e)


def post_json(url: str, payload: dict, timeout: int = 1200) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def unload_models() -> None:
    try:
        # llama-swap accepts the POST even with an empty body in your setup.
        post_json(LLAMA_SWAP_UNLOAD_URL, {}, timeout=30)
    except Exception:
        pass


def load_yaml(path: Path) -> dict:
    with path.open("r") as f:
        return yaml.safe_load(f)


def read_meminfo() -> dict[str, Any]:
    values: dict[str, int] = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                key = parts[0].rstrip(":")
                if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
                    values[key] = int(parts[1])
    except FileNotFoundError:
        pass
    total = values.get("MemTotal", 0)
    avail = values.get("MemAvailable", 0)
    swap_total = values.get("SwapTotal", 0)
    swap_free = values.get("SwapFree", 0)
    return {
        "mem_total_gb": round(total / 1024 / 1024, 3),
        "mem_available_gb": round(avail / 1024 / 1024, 3),
        "mem_available_pct": round((avail / total * 100), 2) if total else "",
        "swap_total_gb": round(swap_total / 1024 / 1024, 3),
        "swap_free_gb": round(swap_free / 1024 / 1024, 3),
        "swap_used_pct": round(((swap_total - swap_free) / swap_total * 100), 2) if swap_total else 0,
    }


def read_psi_memory() -> dict[str, Any]:
    out = {"psi_some_avg10": "", "psi_some_avg60": "", "psi_full_avg10": "", "psi_full_avg60": ""}
    try:
        with open("/proc/pressure/memory") as f:
            for line in f:
                parts = line.split()
                kind = parts[0]
                fields = dict(p.split("=") for p in parts[1:] if "=" in p)
                if kind == "some":
                    out["psi_some_avg10"] = fields.get("avg10", "")
                    out["psi_some_avg60"] = fields.get("avg60", "")
                elif kind == "full":
                    out["psi_full_avg10"] = fields.get("avg10", "")
                    out["psi_full_avg60"] = fields.get("avg60", "")
    except FileNotFoundError:
        pass
    return out


def docker_stats_rows() -> list[dict]:
    code, stdout, _ = run_cmd(["docker", "stats", "--no-stream", "--format", "{{json .}}"], timeout=20)
    if code != 0:
        return []
    rows = []
    for line in stdout.splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def ai_container_name(name: str) -> bool:
    low = name.lower()
    return any(x in low for x in [
        "llama", "qwen", "gemma", "granite", "devstral", "ministral", "codestral",
        "vllm", "litellm", "librechat", "mongo",
    ])


def memory_sampler(stop: threading.Event, out_csv: Path, interval: float) -> None:
    fields = [
        "timestamp", "container", "cpu_perc", "mem_usage", "mem_perc", "pids",
        "mem_total_gb", "mem_available_gb", "mem_available_pct", "swap_total_gb", "swap_free_gb", "swap_used_pct",
        "psi_some_avg10", "psi_some_avg60", "psi_full_avg10", "psi_full_avg60",
    ]
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        while not stop.is_set():
            mem = read_meminfo()
            psi = read_psi_memory()
            stats = docker_stats_rows()
            wrote = False
            for s in stats:
                name = s.get("Name", "")
                if not ai_container_name(name):
                    continue
                w.writerow({
                    "timestamp": now_iso(),
                    "container": name,
                    "cpu_perc": s.get("CPUPerc", ""),
                    "mem_usage": s.get("MemUsage", ""),
                    "mem_perc": s.get("MemPerc", ""),
                    "pids": s.get("PIDs", ""),
                    **mem,
                    **psi,
                })
                wrote = True
            if not wrote:
                w.writerow({"timestamp": now_iso(), "container": "NO_AI_CONTAINERS", **mem, **psi})
            f.flush()
            stop.wait(interval)


def extract_text(resp: dict) -> str:
    try:
        msg = resp["choices"][0]["message"]
        return msg.get("content") or msg.get("reasoning_content") or ""
    except Exception:
        return ""


def finish_reason(resp: dict) -> str:
    try:
        return resp["choices"][0].get("finish_reason", "")
    except Exception:
        return ""


def output_mode(resp: dict) -> str:
    try:
        msg = resp["choices"][0]["message"]
    except Exception:
        return "backend_error"
    if msg.get("content"):
        return "normal_content"
    if msg.get("reasoning_content"):
        return "reasoning_only"
    if msg.get("tool_calls"):
        return "native_tool_call"
    return "true_empty"


def run_request(model: dict, prompt: str, task: dict) -> tuple[dict, str, str]:
    payload = {
        "model": model["name"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": task.get("temperature", 0.1),
        "max_tokens": task.get("max_tokens", 1200),
    }
    if "top_p" in task:
        payload["top_p"] = task["top_p"]
    if "stop" in task:
        payload["stop"] = task["stop"]
    try:
        resp = post_json(model["endpoint"], payload, timeout=task.get("timeout", 1200))
        return resp, extract_text(resp), ""
    except Exception as e:
        return {}, "", str(e)


def load_tasks(tasks_path: Path, answer_keys: dict) -> list[dict]:
    cfg = load_yaml(tasks_path)
    tasks: list[dict] = []
    for t in cfg.get("tasks", []):
        prompt_file = t.get("prompt_file")
        if prompt_file:
            path = BASE / prompt_file
            # The default tasks.yaml uses generated prompt files.
            key_name = Path(prompt_file).stem
            t = {**t, "prompt_path": str(path), "answer_key": answer_keys.get(key_name, {}).get("answer_key", {})}
        tasks.append(t)
    return tasks


def filter_items(items: list[dict], filters: list[str] | None, key: str = "name") -> list[dict]:
    if not filters:
        return items
    return [x for x in items if any(f in x.get(key, "") for f in filters)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=None, help="model name fragments")
    ap.add_argument("--tasks", nargs="+", default=None, help="task name fragments")
    ap.add_argument("--tiers", nargs="+", default=None, help="32k / 64k / 128k fragments")
    ap.add_argument("--models-file", default="models.yaml")
    ap.add_argument("--tasks-file", default="tasks.yaml")
    ap.add_argument("--no-unload", action="store_true")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    RESULTS.mkdir(exist_ok=True)
    if not ANSWER_KEYS.exists():
        raise SystemExit(f"Missing {ANSWER_KEYS}. Run ./run_generate_prompts.sh first.")
    answer_keys = json.loads(ANSWER_KEYS.read_text())
    models = load_yaml(BASE / args.models_file).get("models", [])
    tasks = load_tasks(BASE / args.tasks_file, answer_keys)

    models = filter_items(models, args.models)
    tasks = filter_items(tasks, args.tasks)
    if args.tiers:
        tasks = [t for t in tasks if any(tier in t.get("name", "") for tier in args.tiers)]

    print(f"Models ({len(models)}): " + ", ".join(m["name"] for m in models))
    print(f"Tasks  ({len(tasks)}): " + ", ".join(t["name"] for t in tasks))

    if args.dry:
        for t in tasks[:5]:
            p = Path(t["prompt_path"])
            text = p.read_text()
            print(f"\n{t['name']}: {p} chars={len(text)} approx_tokens={len(text)//4}")
            print(text[:500].replace("\n", " ") + "...")
        return

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    summary_csv = RESULTS / f"summary-{run_id}.csv"
    run_json = RESULTS / f"run-{run_id}.json"
    rows: list[dict] = []

    fields = [
        "timestamp", "model", "role", "task", "benchmark", "tier", "score", "score_reason",
        "wall_seconds", "prompt_chars", "approx_prompt_tokens", "api_prompt_tokens", "completion_tokens", "total_tokens",
        "finish_reason", "output_mode", "response_chars", "error", "prompt_file", "response_file", "raw_response_file", "memory_file",
    ]
    with summary_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for model in models:
            if not args.no_unload:
                unload_models()
                time.sleep(3)

            mem_file = RESULTS / f"memory-{run_id}-{model['name']}.csv"
            stop = threading.Event()
            sampler = threading.Thread(target=memory_sampler, args=(stop, mem_file, float(model.get("sample_interval", 2))), daemon=True)
            sampler.start()

            # Warmup/load request.
            warm = {"name": "warmup", "temperature": 0, "max_tokens": 20, "timeout": 300, "benchmark": "warmup"}
            print(f"\n== {model['name']} ==")
            print("warming...")
            _resp, _text, err = run_request(model, "Reply with exactly: ok", warm)
            if err:
                print(f"warmup error: {err}")

            for task in tasks:
                prompt_path = Path(task["prompt_path"])
                prompt = prompt_path.read_text()
                prompt_chars = len(prompt)
                approx = prompt_chars // 4
                print(f"running {task['name']} (~{approx} tok)")
                start = time.time()
                resp, text, error = run_request(model, prompt, task)
                wall = round(time.time() - start, 3)
                answer_key = task.get("answer_key", {})
                sc, reason = (0, error) if error else score_response(task["name"], text, answer_key)

                safe_model = model["name"].replace("/", "_")
                response_file = RESULTS / f"response-{run_id}-{safe_model}-{task['name']}.txt"
                raw_file = RESULTS / f"raw-{run_id}-{safe_model}-{task['name']}.json"
                response_file.write_text(text)
                raw_file.write_text(json.dumps(resp, indent=2))
                usage = resp.get("usage", {}) if isinstance(resp, dict) else {}

                row = {
                    "timestamp": now_iso(),
                    "model": model["name"],
                    "role": model.get("role", ""),
                    "task": task["name"],
                    "benchmark": task.get("benchmark", ""),
                    "tier": task.get("tier", ""),
                    "score": sc,
                    "score_reason": reason,
                    "wall_seconds": wall,
                    "prompt_chars": prompt_chars,
                    "approx_prompt_tokens": approx,
                    "api_prompt_tokens": usage.get("prompt_tokens", ""),
                    "completion_tokens": usage.get("completion_tokens", ""),
                    "total_tokens": usage.get("total_tokens", ""),
                    "finish_reason": finish_reason(resp),
                    "output_mode": output_mode(resp),
                    "response_chars": len(text),
                    "error": error,
                    "prompt_file": str(prompt_path),
                    "response_file": str(response_file),
                    "raw_response_file": str(raw_file),
                    "memory_file": str(mem_file),
                }
                rows.append(row)
                writer.writerow(row)
                f.flush()
                print(f"  score={sc}/5 wall={wall}s reason={reason}")

            stop.set()
            sampler.join(timeout=5)
            if not args.no_unload:
                unload_models()
                time.sleep(3)

    model_avgs: dict[str, float] = {}
    for m in {r["model"] for r in rows}:
        vals = [float(r["score"]) for r in rows if r["model"] == m and str(r["score"]).isdigit()]
        if vals:
            model_avgs[m] = round(sum(vals) / len(vals), 3)
    run_json.write_text(json.dumps({"run_id": run_id, "rows": rows, "model_avgs": model_avgs}, indent=2))
    print(f"\nSummary CSV: {summary_csv}")
    print(f"Run JSON:    {run_json}")
    print("Model averages:")
    for m, avg in sorted(model_avgs.items(), key=lambda x: -x[1]):
        print(f"  {m}: {avg}")


if __name__ == "__main__":
    main()
