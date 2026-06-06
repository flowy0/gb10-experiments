#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys
import pandas as pd

BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"


def main() -> None:
    files = sorted(RESULTS.glob("summary-*.csv"))
    if not files:
        print("No summary files found in results/")
        return
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else files[-1]
    df = pd.read_csv(path)
    print(f"Summary: {path}")
    print("\nModel averages:")
    print(df.groupby("model")["score"].mean().sort_values(ascending=False).round(3).to_string())
    print("\nModel x tier averages:")
    if "tier" in df.columns:
        print(df.pivot_table(index="model", columns="tier", values="score", aggfunc="mean").round(3).to_string())
    print("\nTask averages:")
    print(df.groupby("task")["score"].mean().sort_values(ascending=False).round(3).to_string())
    print("\nLatency by model, seconds:")
    print(df.groupby("model")["wall_seconds"].agg(["mean", "max"]).round(2).to_string())

    # Memory summaries
    print("\nMemory summaries from referenced memory files:")
    mem_files = sorted(set(str(x) for x in df.get("memory_file", []) if isinstance(x, str)))
    for mf in mem_files:
        p = Path(mf)
        if not p.exists():
            continue
        try:
            mdf = pd.read_csv(p)
            min_avail = pd.to_numeric(mdf["mem_available_gb"], errors="coerce").min()
            max_some = pd.to_numeric(mdf["psi_some_avg10"], errors="coerce").max()
            max_full = pd.to_numeric(mdf["psi_full_avg10"], errors="coerce").max()
            print(f"  {p.name}: min_mem_available_gb={min_avail:.2f}, max_psi_some={max_some:.2f}, max_psi_full={max_full:.2f}")
        except Exception as e:
            print(f"  {p.name}: failed to analyze memory CSV: {e}")


if __name__ == "__main__":
    main()
