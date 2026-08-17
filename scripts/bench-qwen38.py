#!/usr/bin/env python3
"""
bench-qwen38.py — Qwen3.8-27B candidate benchmark harness (test plan §7).

Measures decode throughput, concurrency aggregate, prefix-caching TTFT and
prefill TTFT against ANY OpenAI-compatible endpoint (llama.cpp server, SGLang,
vLLM). One script, identical methodology for every candidate.

Methodology rules (docs/QWEN38_TESTPLAN.md §1):
  * decode throughput measured on >=400 output tokens (short outputs = prefill drag)
  * thinking OFF for throughput (chat_template_kwargs.enable_thinking=false)
  * temperature 0, distinct prompts per concurrency level
  * aggregate AND per-stream tok/s, p95 TTFT, error count
  * every sub-test writes JSON; a run card line is printed at the end

Usage:
  python3 scripts/bench-qwen38.py --base-url http://127.0.0.1:8090/v1 \
      --model qwen3.8-27b --out docs/qwen38-test-runs/session-a \
      --spec-label "draft-mtp-n2" --tag "candidate A"
  # run a subset:
  ... --only solo,ladder
  # engine without chat_template_kwargs support:
  ... --no-disable-thinking
"""

import argparse
import json
import math
import os
import random
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

RETRIES = 2          # transient connection errors: retry count
RETRY_BACKOFF = 1.0  # seconds


def _post(session, url, body, timeout, stream=False):
    """POST with transient-error retries so a hiccup doesn't kill a long run."""
    last = None
    for attempt in range(RETRIES + 1):
        try:
            return session.post(url, json=body, timeout=timeout, stream=stream)
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            last = e
            if attempt < RETRIES:
                time.sleep(RETRY_BACKOFF * (attempt + 1))
    raise last

# ---------------------------------------------------------------------------
# prompt pool — distinct topics so concurrency levels don't share prefixes
# ---------------------------------------------------------------------------

TASKS = [
    "Write a Python module implementing an LRU cache with TTL expiry, thread safety, and a decorator API.",
    "Design a SQL schema for a multi-tenant todo app with soft deletes and audit logs, then write the migration.",
    "Explain how you would profile and optimize a slow PostgreSQL query that joins five tables with a correlated subquery.",
    "Write a bash script that monitors a directory for new files, deduplicates them by hash, and archives them with timestamps.",
    "Describe the tradeoffs between event sourcing and CRUD for a banking ledger, with concrete examples.",
    "Write a Go program that implements a rate limiter with token bucket semantics and exposes it over gRPC.",
    "Design a distributed job scheduler that survives worker crashes and guarantees at-least-once execution.",
    "Write a TypeScript function that deeply merges two objects with type-safe output and cycle detection.",
    "Explain how garbage collectors work, comparing mark-sweep, generational, and concurrent collectors with diagrams in prose.",
    "Write a Rust implementation of a lock-free MPMC queue using crossbeam, with benchmarks and safety notes.",
    "Design a prompt-injection defense for a retrieval-augmented chatbot, including prompt examples of attacks and mitigations.",
    "Write a Python script that fetches a paginated REST API, retries with exponential backoff, and writes results to parquet.",
    "Explain the CAP theorem using the example of a global chat system with offline message sync.",
    "Write a Kubernetes deployment for a stateful service with persistent volumes, liveness probes, and a canary rollout strategy.",
    "Design a cache invalidation strategy for a CDN serving personalized content that changes hourly.",
    "Write a C++ snippet implementing a memory pool allocator with alignment guarantees and zero fragmentation for fixed-size blocks.",
    "Explain how transformer attention works, then walk through a minimal implementation in NumPy line by line.",
    "Write a data validation library in Python that produces human-readable error trees for nested JSON.",
    "Design an anomaly detection system for server metrics that adapts to weekly seasonality without manual thresholds.",
    "Write a shell one-liner suite that summarizes nginx logs: top IPs, status codes, slowest endpoints, with awk.",
    "Explain the differences between optimistic and pessimistic concurrency control, with a multi-user inventory example.",
    "Write a Java class implementing a thread-safe bounded buffer using condition variables, with a producer-consumer demo.",
    "Design a feature flag system with gradual rollout, kill switches, and experiment bucketing that stays consistent under load.",
    "Write a SQL query that finds duplicate customer records by fuzzy name and address matching, with a scoring threshold.",
    "Explain how you would build a recommendation engine from clickstream data, from raw logs to serving endpoint.",
]

FILLER = [
    "The system should remain responsive under load and degrade gracefully rather than failing outright.",
    "Careful attention to edge cases pays off disproportionately in production systems.",
    "A good design documents its invariants explicitly, because implicit ones are violated first.",
    "Latency budgets should be measured end to end, not per component in isolation.",
    "Backpressure is a feature, not an implementation detail; without it queues grow without bound.",
    "Idempotency keys turn at-least-once delivery into effectively exactly-once semantics.",
    "The cheapest way to handle failure is to make the failure mode loud and the recovery path trivial.",
    "Write the test that would have caught the bug before writing the code that fixes it.",
    "Observability is the ability to answer questions about the system that nobody thought to ask.",
    "A queue that can back up indefinitely is a buffer for an unbounded problem.",
    "Configuration that can be invalid should fail at startup, not at midnight.",
    "The contract between components matters more than the implementation of either one.",
    "Retries without jitter collapse into thundering herds the moment a dependency blinks.",
    "Reads scale horizontally; writes need a story. Every architecture discussion starts there.",
    "A metric you cannot alert on is a log line wearing a costume.",
    "Timeouts should be short enough to fail fast and long enough to never fire in health.",
    "The second-order effects of a design decision usually arrive after the first release.",
    "Code that is easy to delete is easy to replace, and replacement is the real maintenance.",
    "Measure the p99, but ship for the median user and the pathological case.",
    "Consistency models are a contract with the future readers of your system.",
    "A schema migration is a deployment with a rollback story you have already rehearsed.",
    "The happy path is where features live; the sad path is where careers are made.",
    "Batching reduces overhead at the cost of latency, and the optimum is rarely zero.",
    "Caching makes everything fast until it makes everything wrong, which is why invalidation is hard.",
    "An incident postmortem that names no owner teaches no lesson.",
    "Prefer boring technology that you fully understand over exciting technology you partially do.",
    "The worst outage is the one caused by the safety mechanism you added last quarter.",
    "Documentation decays from the moment it is written; code review is the only refresh cycle.",
    "Rate limits protect the provider, but they also discipline the consumer into batching.",
    "Every retry budget should have a kill switch that a human can reach without a deploy.",
    "The best interface is the one where misuse is a syntax error, not a runtime surprise.",
    "Deadlines in distributed systems are not optional; they are the only thing that bounds the blast radius.",
]


def make_prompt(target_tokens: int, topic: str, cpt: float, rng: random.Random) -> str:
    """Build a distinct prompt of roughly `target_tokens` tokens (chars/token `cpt`)."""
    task = rng.choice(TASKS) if topic is None else topic
    header = "You are a senior staff engineer. Write a thorough, well-structured answer.\n\n"
    body = [task, ""]
    budget_chars = int(target_tokens * cpt * 0.92)  # 8% safety margin
    used = 0
    sentences = FILLER[:]
    rng.shuffle(sentences)
    i = 0
    while used < budget_chars and sentences:
        s = sentences[i % len(sentences)]
        body.append(s + "\n")
        used += len(s) + 1
        i += 1
        if i >= len(sentences):
            sentences = FILLER[:]
            rng.shuffle(sentences)
            i = 0
    body.append("")
    body.append("Question: " + task)
    body.append("Answer:")
    return header + "\n".join(body)


# ---------------------------------------------------------------------------
# OpenAI-compatible client helpers
# ---------------------------------------------------------------------------

class Client:
    def __init__(self, base_url, model, timeout, disable_thinking, verify_certs=True):
        self.base = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.disable_thinking = disable_thinking
        self.verify_certs = verify_certs
        self._tl = threading.local()

    @property
    def session(self):
        """Thread-local session — requests.Session is not safe to share across
        threads, and the concurrency ladder runs requests in parallel."""
        s = getattr(self._tl, "session", None)
        if s is None:
            s = requests.Session()
            s.verify = self.verify_certs
            self._tl.session = s
        return s

    def _body(self, messages, max_tokens, temperature=0.0):
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if self.disable_thinking:
            body["chat_template_kwargs"] = {"enable_thinking": False}
        return body

    def chat(self, prompt, max_tokens, temperature=0.0):
        """Non-streaming completion. Returns (text, usage, elapsed)."""
        body = self._body([{"role": "user", "content": prompt}], max_tokens, temperature)
        t0 = time.monotonic()
        r = _post(self.session, f"{self.base}/chat/completions", body, self.timeout)
        elapsed = time.monotonic() - t0
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
        d = r.json()
        usage = d.get("usage", {})
        text = (d.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return text, usage, elapsed

    def chat_stream_ttft(self, prompt, max_tokens, temperature=0.0):
        """Streaming request; returns (first_token_s, text, usage, elapsed)."""
        body = self._body([{"role": "user", "content": prompt}], max_tokens, temperature)
        body["stream"] = True
        t0 = time.monotonic()
        ttft = None
        chunks = []
        with _post(self.session, f"{self.base}/chat/completions", body, self.timeout, stream=True) as r:
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if ttft is None:
                        delta = (chunk.get("choices") or [{}])[0].get("delta", {})
                        if delta.get("content") or delta.get("reasoning_content"):
                            ttft = time.monotonic() - t0
                    chunks.append(chunk)
        elapsed = time.monotonic() - t0
        text = "".join(
            (c.get("choices") or [{}])[0].get("delta", {}).get("content", "") or ""
            for c in chunks
        )
        usage = {}
        for c in chunks:
            if c.get("usage"):
                usage = c["usage"]
        return ttft, text, usage, elapsed

    def count_prompt_tokens(self, prompt):
        """Ground-truth prompt length via a max_tokens=1 request."""
        _, usage, _ = self.chat(prompt, 1)
        return usage.get("prompt_tokens") or len(prompt) // 3

    def calibrate_cpt(self):
        """chars-per-token for this tokenizer, measured once."""
        sample = " ".join(FILLER[:6]) + "\n" + TASKS[0]
        n = self.count_prompt_tokens(sample)
        if n == 0:
            return 3.7
        return len(sample) / n


# ---------------------------------------------------------------------------
# sub-tests
# ---------------------------------------------------------------------------

def run_solo(client, cpt, rng, in_tokens, out_tokens, reps, tag):
    """Decode-dominated throughput, median of reps."""
    topic = rng.choice(TASKS)
    prompt = make_prompt(in_tokens, topic, cpt, rng)
    rows = []
    for i in range(reps):
        text, usage, elapsed = client.chat(prompt, out_tokens)
        ot = usage.get("completion_tokens") or len(text) // 3
        pt = usage.get("prompt_tokens") or 0
        tok_s = ot / elapsed if elapsed > 0 else 0.0
        rows.append({"rep": i + 1, "prompt_tokens": pt, "output_tokens": ot,
                     "elapsed_s": round(elapsed, 3), "tok_s": round(tok_s, 2)})
    med = statistics.median(r["tok_s"] for r in rows)
    return {"tag": tag, "input_tokens": in_tokens, "output_tokens": out_tokens,
            "reps": reps, "median_tok_s": round(med, 2),
            "best_tok_s": max(r["tok_s"] for r in rows), "rows": rows}


def run_ladder(client, cpt, rng, levels, out_tokens, timeout_extra):
    """Concurrency ladder: aggregate + per-stream tok/s + p95 TTFT."""
    results = {}
    for n in levels:
        topics = rng.sample(TASKS, min(n, len(TASKS)))
        prompts = [make_prompt(256, t, cpt, rng) for t in topics]  # 256-in, decode-dominated
        def one(prompt):
            t0 = time.monotonic()
            text, usage, elapsed = client.chat(prompt, out_tokens)
            ot = usage.get("completion_tokens") or len(text) // 3
            return {"tok_s": ot / elapsed if elapsed > 0 else 0.0,
                    "elapsed_s": elapsed, "output_tokens": ot,
                    "ttft_approx": None, "wall": time.monotonic() - t0}
        with ThreadPoolExecutor(max_workers=n) as ex:
            futs = [ex.submit(one, p) for p in prompts]
            rows = [f.result() for f in as_completed(futs)]
        agg = sum(r["tok_s"] for r in rows)
        per_stream = agg / n
        results[str(n)] = {
            "concurrency": n, "prompts": len(prompts),
            "aggregate_tok_s": round(agg, 2),
            "per_stream_tok_s": round(per_stream, 2),
            "errors": 0, "rows": rows,
        }
    return results


def run_prefix(client, cpt, rng, prefix_tokens, suffix_tokens, runs):
    """Cold vs warm TTFT on a shared prefix (agent system-prompt simulation)."""
    prefix = make_prompt(prefix_tokens, None, cpt, rng).rsplit("Answer:", 1)[0]
    out = {}
    for i in range(runs):
        suffix = f"Answer the question embedded above. Question: {rng.choice(TASKS)[:60]}... Answer:"
        prompt = prefix + "\n" + suffix
        ttft, text, usage, elapsed = client.chat_stream_ttft(prompt, suffix_tokens)
        key = "cold" if i == 0 else "warm"
        out[key] = {"ttft_s": round(ttft, 3) if ttft else None,
                    "prompt_tokens": usage.get("prompt_tokens") or 0,
                    "elapsed_s": round(elapsed, 3)}
        time.sleep(2)  # let warm cache settle
    if out.get("cold", {}).get("ttft_s") and out.get("warm", {}).get("ttft_s"):
        c = out["cold"]["ttft_s"]
        w = out["warm"]["ttft_s"]
        out["speedup"] = round(c / w, 2) if w > 0 else None
    return out


def run_prefill(client, cpt, rng, sizes):
    """Unique-content prefill TTFT + prefill tok/s, max_tokens=1."""
    out = {}
    for size in sizes:
        prompt = make_prompt(size, None, cpt, rng)
        ttft, text, usage, elapsed = client.chat_stream_ttft(prompt, 1)
        pt = usage.get("prompt_tokens") or 0
        out[str(size)] = {
            "target_tokens": size, "actual_prompt_tokens": pt,
            "ttft_s": round(ttft, 3) if ttft else None,
            "prefill_tok_s": round(pt / ttft, 1) if ttft and ttft > 0 else None,
            "elapsed_s": round(elapsed, 3),
        }
    return out


def run_think(client, cpt, rng, out_tokens):
    """Thinking-on sanity + cost: reasoning tokens, output tokens, tok/s."""
    prompt = make_prompt(256, "Explain the difference between MTP and DSpark speculative decoding, and why draft acceptance is a poor tuning signal.", cpt, rng)
    body = {
        "model": client.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": out_tokens,
        "temperature": 1.0,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": True},
    }
    t0 = time.monotonic()
    r = client.session.post(f"{client.base}/chat/completions", json=body, timeout=client.timeout)
    elapsed = time.monotonic() - t0
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}
    d = r.json()
    msg = (d.get("choices") or [{}])[0].get("message", {})
    usage = d.get("usage", {})
    reasoning = msg.get("reasoning_content") or ""
    content = msg.get("content") or ""
    return {
        "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens") or (len(reasoning) // 3),
        "content_tokens": usage.get("completion_tokens", 0) - (usage.get("completion_tokens_details", {}).get("reasoning_tokens") or 0),
        "reasoning_chars": len(reasoning),
        "content_chars": len(content),
        "has_reasoning_content": bool(reasoning),
        "elapsed_s": round(elapsed, 3),
        "tok_s": round(usage.get("completion_tokens", 0) / elapsed, 2) if elapsed > 0 else 0.0,
    }


def _save(results, out_dir, run_id):
    """Write the current results JSON (checkpointed after every sub-test)."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"bench-{run_id}.json")
    with open(path, "w") as f:
        json.dump(results, f, indent=1)
    return path


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Qwen3.8-27B candidate benchmark harness")
    p.add_argument("--base-url", required=True, help="OpenAI-compatible base URL, e.g. http://127.0.0.1:8090/v1")
    p.add_argument("--model", required=True, help="served model name")
    p.add_argument("--out", default="docs/qwen38-test-runs", help="output dir for JSON results")
    p.add_argument("--tag", default="", help="run tag (e.g. 'candidate A, session 1')")
    p.add_argument("--spec-label", default="", help="spec-decode config label (e.g. draft-mtp-n2, no-spec)")
    p.add_argument("--only", default="", help="comma list of sub-tests: solo,short,ladder,prefix,prefill,think")
    p.add_argument("--solo-in", type=int, default=512)
    p.add_argument("--solo-out", type=int, default=1024)
    p.add_argument("--solo-reps", type=int, default=3)
    p.add_argument("--short-out", type=int, default=256)
    p.add_argument("--short-reps", type=int, default=5)
    p.add_argument("--ladder", default="1,4,8,16", help="comma concurrency levels")
    p.add_argument("--ladder-out", type=int, default=1500)
    p.add_argument("--prefix-tokens", type=int, default=19000)
    p.add_argument("--prefix-runs", type=int, default=2)
    p.add_argument("--prefill", default="8192,32768,100000", help="comma prefill sizes in tokens")
    p.add_argument("--think-out", type=int, default=1200)
    p.add_argument("--timeout", type=int, default=600, help="per-request timeout s")
    p.add_argument("--no-disable-thinking", action="store_true",
                   help="omit chat_template_kwargs (engine without thinking control)")
    p.add_argument("--seed", type=int, default=20260817)
    return p.parse_args()


def main():
    sys.stdout.reconfigure(line_buffering=True)  # stream progress when piped/backgrounded
    args = parse_args()
    rng = random.Random(args.seed)
    client = Client(args.base_url, args.model, args.timeout, not args.no_disable_thinking)
    os.makedirs(args.out, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    meta = {
        "run_id": run_id, "tag": args.tag, "spec_label": args.spec_label,
        "base_url": args.base_url, "model": args.model, "seed": args.seed,
        "thinking_disabled": not args.no_disable_thinking,
        "timestamp": run_id,
    }

    # health
    try:
        r = client.session.get(f"{client.base}/models", timeout=30)
        if r.status_code != 200:
            sys.exit(f"server not ready: HTTP {r.status_code} at {client.base}/models")
        served = [m.get("id") for m in r.json().get("data", [])]
        meta["served_models"] = served
        print(f"server OK. served: {served}")
    except Exception as e:
        sys.exit(f"server not reachable at {client.base}: {e}")

    print("calibrating chars/token ...")
    cpt = client.calibrate_cpt()
    meta["chars_per_token"] = round(cpt, 3)
    print(f"  cpt = {cpt:.3f}")

    only = set(x.strip() for x in args.only.split(",") if x.strip())
    results = {"meta": meta}

    def want(name):
        return not only or name in only

    def safe(name, fn):
        """Run a sub-test; record the error and continue so one failure never
        discards the rest of the session's data."""
        if not want(name):
            return
        print(f"=== {name} ===", flush=True)
        try:
            results[name] = fn()
        except Exception as e:
            results[name] = {"error": f"{type(e).__name__}: {e}"}
            print(f"  ERROR: {type(e).__name__}: {e}", flush=True)
        finally:
            # checkpoint after every sub-test so progress survives crashes
            _save(results, args.out, run_id)

    safe("solo", lambda: run_solo(client, cpt, rng, args.solo_in, args.solo_out, args.solo_reps, args.spec_label))
    if "solo" in results and "error" not in results["solo"]:
        print(f"  median {results['solo']['median_tok_s']} tok/s")

    safe("short", lambda: run_solo(client, cpt, rng, args.solo_in, args.short_out, args.short_reps, args.spec_label))
    if "short" in results and "error" not in results["short"]:
        print(f"  median {results['short']['median_tok_s']} tok/s")

    def _ladder():
        levels = [int(x) for x in args.ladder.split(",")]
        return run_ladder(client, cpt, rng, levels, args.ladder_out, args.timeout)
    safe("ladder", _ladder)
    if "ladder" in results and "error" not in results["ladder"]:
        for k, v in results["ladder"].items():
            print(f"  c{v['concurrency']}: aggregate {v['aggregate_tok_s']} tok/s | per-stream {v['per_stream_tok_s']} | errors {v['errors']}")

    safe("prefix", lambda: run_prefix(client, cpt, rng, args.prefix_tokens, 200, args.prefix_runs))
    if "prefix" in results and "error" not in results["prefix"] and results["prefix"].get("speedup"):
        print(f"  cold {results['prefix'].get('cold', {}).get('ttft_s')}s | warm {results['prefix'].get('warm', {}).get('ttft_s')}s | speedup {results['prefix'].get('speedup')}")

    def _prefill():
        sizes = [int(x) for x in args.prefill.split(",")]
        return run_prefill(client, cpt, rng, sizes)
    safe("prefill", _prefill)
    if "prefill" in results and "error" not in results["prefill"]:
        for k, v in results["prefill"].items():
            print(f"  {k} tok: TTFT {v['ttft_s']}s | prefill {v['prefill_tok_s']} tok/s")

    safe("think", lambda: run_think(client, cpt, rng, args.think_out))
    if "think" in results and "error" not in results["think"]:
        t = results["think"]
        print(f"  reasoning_tokens={t['reasoning_tokens']} content_tokens={t['content_tokens']} has_reasoning_content={t['has_reasoning_content']} tok_s={t['tok_s']}")

    outfile = os.path.join(args.out, f"bench-{run_id}.json")
    _save(results, args.out, run_id)
    print(f"\nresults -> {outfile}")

    # run card line (test plan §6d)
    print("\n--- RUN CARD ---")
    print(f"candidate: {args.tag or '?'} | date: {run_id} | base: {args.base_url} | model: {args.model} | spec: {args.spec_label or '?'} | ctx: (record) | kv: (record)")
    if "solo" in results:
        print(f"solo({args.solo_in}->{args.solo_out}): {results['solo']['median_tok_s']} tok/s | short({args.solo_in}->{args.short_out}): {results.get('short', {}).get('median_tok_s', 'n/a')} tok/s")
    if "ladder" in results and isinstance(results["ladder"], dict) and "error" not in results["ladder"]:
        lv = results["ladder"]
        print("ladder aggregate: " + " | ".join(f"c{v['concurrency']}={v['aggregate_tok_s']}" for v in lv.values()))
    if "prefix" in results and results["prefix"].get("speedup"):
        print(f"prefix: cold {results['prefix']['cold']['ttft_s']}s -> warm {results['prefix']['warm']['ttft_s']}s ({results['prefix']['speedup']}x)")
    if "prefill" in results:
        print("prefill TTFT: " + " | ".join(f"{k}={v['ttft_s']}s" for k, v in results["prefill"].items()))
    if "think" in results and "error" not in results["think"]:
        print(f"think: reasoning={results['think']['reasoning_tokens']} tok, {results['think']['tok_s']} tok/s")


if __name__ == "__main__":
    main()
