#!/usr/bin/env python3
"""
qwen38-niah.py — needle-in-a-haystack probes at 262K context (test plan §5a).

Needles at the given token positions inside a ~255K-token window, 3 needles per
position. Pass = needle string present in the completion. 12 probes total.

Usage:
  python3 scripts/qwen38-niah.py --base-url http://127.0.0.1:8090/v1 \
      --model <name> --out docs/qwen38-test-runs --tag "Session A"
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_spec = importlib.util.spec_from_file_location("benchmod", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bench-qwen38.py"))
_bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bench)
FILLER = _bench.FILLER
Client = _bench.Client

NEEDLES = ["7XQ-4912", "KRM-8831", "BZT-2274"]


def build_prompt(needle_pos_tokens, needle, cpt, rng, window=255000):
    """Filler text of ~`window` tokens with `needle` inserted at needle_pos_tokens."""
    needle_sentence = f"The secret code is {needle}. Remember it."
    before_chars = int(needle_pos_tokens * cpt * 0.90)
    total_chars = int(window * cpt * 0.95)
    after_chars = max(0, total_chars - before_chars - len(needle_sentence))

    def fill(budget):
        parts, acc, i = [], 0, 0
        sentences = FILLER[:]
        rng.shuffle(sentences)
        while acc < budget:
            s = sentences[i % len(sentences)]
            parts.append(s)
            acc += len(s) + 1
            i += 1
            if i >= len(sentences):
                sentences = FILLER[:]
                rng.shuffle(sentences)
                i = 0
        return " ".join(parts)

    body = [fill(before_chars), needle_sentence, fill(after_chars),
            "\n\nRetrieval question: What is the secret code that was mentioned in the text? Answer with the code only."]
    return "\n".join(body)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--out", default="docs/qwen38-test-runs")
    p.add_argument("--tag", default="")
    p.add_argument("--positions", default="8192,32768,131072,247296")
    p.add_argument("--needles", type=int, default=3)
    p.add_argument("--timeout", type=int, default=1200)
    p.add_argument("--seed", type=int, default=20260817)
    args = p.parse_args()

    client = Client(args.base_url, args.model, args.timeout, True)
    rng = random.Random(args.seed)
    cpt = client.calibrate_cpt()
    print(f"cpt={cpt:.3f}")

    positions = [int(x) for x in args.positions.split(",")]
    results = {"candidate": args.tag, "positions": positions,
               "needles": args.needles, "cpt": round(cpt, 3), "probes": []}
    passed = 0

    for pos in positions:
        for ni in range(args.needles):
            needle = NEEDLES[ni]
            prompt = build_prompt(pos, needle, cpt, rng)
            t0 = time.monotonic()
            print(f"probe needle@{pos} ({needle}) — prefill...", flush=True)
            try:
                text, usage, elapsed = client.chat(prompt, 60)
                pt = usage.get("prompt_tokens") or 0
                ok = needle in text
                passed += ok
                results["probes"].append({
                    "position": pos, "needle": needle,
                    "prompt_tokens": pt, "elapsed_s": round(elapsed, 1),
                    "found": ok, "response": text.strip()[:120],
                })
                print(f"  {'FOUND' if ok else 'MISS'} needle@{pos} pt={pt} {elapsed:.0f}s", flush=True)
            except Exception as e:
                results["probes"].append({"position": pos, "needle": needle,
                                          "error": f"{type(e).__name__}: {e}"})
                print(f"  ERROR needle@{pos}: {type(e).__name__}: {e}", flush=True)

    results["passed"] = passed
    results["total"] = len(results["probes"])
    results["pass_ratio"] = f"{passed}/{len(results['probes'])}"
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"niah-{run_id}.json")
    with open(path, "w") as f:
        json.dump(results, f, indent=1)
    print(f"\nNIAH: {passed}/{len(results['probes'])} → {path}", flush=True)


if __name__ == "__main__":
    main()
