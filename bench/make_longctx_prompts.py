#!/usr/bin/env python3
"""Generate deterministic long-context benchmark prompts and answer keys.

This v3 generator creates size-tiered prompts intended to separate 32K/64K/128K
routes. The token counts are approximate (chars / 4), but each prompt records
its approximate token count and ground truth in answer_keys.json.

Generated families:
- needle_position: facts placed at beginning/25%/50%/75%/end
- conflict_policy: old/middle/final routing decisions with obsolete statements
- duplicate_logic: true duplicate groups + decoy near-duplicates
- repo_architecture: many pseudo-files with known modules and dependencies
- bug_risk: dispersed evidence across config/client/worker/scheduler/tests
- refactor_plan: plan-only transaction parser refactor
- finance_memo: long synthetic finance docs with explicit contradictions
- json_rules: JSON-only output with rules buried at depth
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "prompts" / "generated"
ANSWER_KEYS = OUT / "answer_keys.json"

TIERS = {
    # Safe prompt targets, not full context sizes.
    # Leaves room for chat template, system prompt, completion tokens,
    # and tokenizer mismatch.
    "32k": 28_000,
    "64k": 58_000,
    "128k": 115_000,
}

PARAGRAPHS = [
    "The service boundary follows a layered design where API adapters call domain services, and domain services delegate persistence to repository classes.",
    "Configuration values are loaded from environment-specific files, then overridden by secrets from a secure runtime store before service startup.",
    "The observability stack records latency histograms, retry counters, queue depth, memory pressure, and error classifications for every worker.",
    "Deployment is performed through container images with health checks, readiness probes, and a rollback procedure based on immutable tags.",
    "The data pipeline validates records, normalizes identifiers, enriches metadata, and writes canonical events to durable storage for downstream consumers.",
    "Backpressure is applied when downstream services exceed latency budgets, and non-critical work is deferred to background queues.",
    "The test strategy distinguishes pure unit tests, contract tests, integration tests, and end-to-end smoke tests for operational workflows.",
    "Financial analysis notes separate reported metrics from derived ratios, and classify management commentary as fact, estimate, or inference.",
    "Security checks include input validation, output encoding, audit logging, least-privilege access, and rotation of credentials used by scheduled jobs.",
    "Long context reasoning should preserve exact identifiers, avoid invented filenames, and prefer evidence-backed conclusions over plausible guesses.",
]


def filler_to_tokens(target_tokens: int, seed: int, label: str = "FILLER") -> str:
    rng = random.Random(seed)
    target_chars = target_tokens * 4
    chunks: list[str] = []
    chars = 0
    i = 0
    while chars < target_chars:
        p = rng.choice(PARAGRAPHS)
        s = f"[{label}-{i:05d}] {p}\n"
        chunks.append(s)
        chars += len(s)
        i += 1
    return "\n".join(chunks)


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def split_filler(total_tokens: int, parts: int, seed_base: int, label: str) -> list[str]:
    per = max(1, total_tokens // parts)
    return [filler_to_tokens(per, seed_base + i, f"{label}{i}") for i in range(parts)]


def write_prompt(name: str, tier: str, text: str, key: dict, force: bool) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}-{tier}.txt"
    if path.exists() and not force:
        existing = path.read_text()
        text_for_meta = existing
    else:
        path.write_text(text)
        text_for_meta = text
    return {
        "task": name,
        "tier": tier,
        "file": str(path.relative_to(BASE)),
        "prompt_chars": len(text_for_meta),
        "approx_tokens": approx_tokens(text_for_meta),
        "answer_key": key,
    }


def make_needle_position(tier: str, target_tokens: int) -> tuple[str, dict]:
    # Use five filler segments so facts land near beginning / quarters / end.
    fillers = split_filler(max(1000, target_tokens - 1600), 5, 100, "NEEDLEFILL")
    facts = {
        "BEGIN": "rollback/flint-2026-05",
        "Q25": "SGD 12.50",
        "MID": "http://flint.home.lan:4000/v1",
        "Q75": "codestral-22b-q4",
        "END": "q8_0",
    }
    context = f"""
[FACT-BEGIN] Emergency rollback branch = {facts['BEGIN']}
{fillers[0]}
[FACT-Q25] Invoice reconciliation tolerance = {facts['Q25']}
{fillers[1]}
[FACT-MID] Correct LiteLLM endpoint = {facts['MID']}
{fillers[2]}
[FACT-Q75] Deprecated model = {facts['Q75']}
{fillers[3]}
[FACT-END] Production KV cache type for both K and V = {facts['END']}
{fillers[4]}
""".strip()
    prompt = f"""You are testing long-context retrieval.

Answer based ONLY on the context.
Return JSON only with keys: rollback_branch, invoice_tolerance, litellm_endpoint, deprecated_model, kv_cache_type, evidence_positions.

CONTEXT START
{context}
CONTEXT END
"""
    return prompt, {"facts": facts, "scoring_type": "needle_position"}


def make_conflict_policy(tier: str, target_tokens: int) -> tuple[str, dict]:
    fillers = split_filler(max(1000, target_tokens - 1600), 4, 200, "CONFLICT")
    prompt = f"""You are resolving a policy document with obsolete sections.
Answer based ONLY on the context.
Return JSON only with keys: current_production_model, obsolete_models, evidence_trail, final_date.

CONTEXT START
## 2026-01 earlier policy
Production model: qwen25-coder-14b.
Status: superseded by later policy.

{fillers[0]}

## 2026-03 middle policy
Production model: devstral-small2-24b-q4.
Status: superseded by later policy.

{fillers[1]}

## 2026-04 experimental note
Production model candidate: unsloth-gemma4-26b-a4b-q4.
Status: candidate only, not approved.

{fillers[2]}

## 2026-05 final approved policy
Production model: unsloth-qwen3-coder-30b-a3b-q4-64k.
Status: current approved production model.

{fillers[3]}
CONTEXT END
"""
    return prompt, {
        "current": "unsloth-qwen3-coder-30b-a3b-q4-64k",
        "obsolete": ["qwen25-coder-14b", "devstral-small2-24b-q4"],
        "candidate_not_current": "unsloth-gemma4-26b-a4b-q4",
        "scoring_type": "conflict_policy",
    }


def code_file(path: str, body: str) -> str:
    return f"# File: {path}\n{body.strip()}\n"


def make_repo_files(target_tokens: int) -> str:
    core_files = [
        code_file("payment_gateway/adapters.py", """
def parse_transaction(raw: str) -> dict:
    parts = raw.split('|')
    if len(parts) != 4:
        raise ValueError('bad transaction')
    prefix, txn_id, currency, amount = parts
    if prefix not in ('TXN', 'PAY'):
        raise ValueError('bad prefix')
    return {'id': txn_id.strip(), 'currency': currency.upper(), 'amount': float(amount)}
"""),
        code_file("billing_service/handlers.py", """
def parse_transaction_response(raw: str) -> dict:
    parts = raw.split('|')
    if len(parts) != 4:
        raise ValueError('bad transaction')
    prefix, txn_id, currency, amount = parts
    if prefix not in ('TXN', 'PAY'):
        raise ValueError('bad prefix')
    return {'id': txn_id.strip(), 'currency': currency.upper(), 'amount': float(amount)}
"""),
        code_file("reconciler/core.py", """
def parse_txn(raw: str) -> dict:
    parts = raw.split('|')
    if len(parts) != 4:
        raise ValueError('bad transaction')
    prefix, txn_id, currency, amount = parts
    if prefix not in ('TXN', 'PAY'):
        raise ValueError('bad prefix')
    return {'id': txn_id.strip(), 'currency': currency.upper(), 'amount': float(amount)}
"""),
        code_file("audit_logger/extract.py", """
def extract_transaction(raw: str) -> dict:
    parts = raw.split('|')
    if len(parts) != 4:
        raise ValueError('bad transaction')
    prefix, txn_id, currency, amount = parts
    if prefix not in ('TXN', 'PAY'):
        raise ValueError('bad prefix')
    return {'id': txn_id.strip(), 'currency': currency.upper(), 'amount': float(amount)}
"""),
        code_file("config.py", "TIMEOUT_SECONDS = 30\nMAX_RETRIES = 5\nJOB_INTERVAL_SECONDS = 20"),
        code_file("client.py", """
def post_payment(requests, endpoint, payload):
    from config import TIMEOUT_SECONDS
    return requests.post(endpoint, json=payload, timeout=TIMEOUT_SECONDS)
"""),
        code_file("worker.py", """
def run_with_retry(fn):
    from config import MAX_RETRIES
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except TimeoutError:
            if attempt == MAX_RETRIES - 1:
                raise
"""),
        code_file("scheduler.py", """
def schedule_job(queue):
    from config import JOB_INTERVAL_SECONDS
    return {'interval_seconds': JOB_INTERVAL_SECONDS, 'queue': queue}
"""),
        code_file("tests/test_scheduler.py", """
def test_job_completes_before_next_interval():
    assert JOB_INTERVAL_SECONDS > TIMEOUT_SECONDS
"""),
    ]
    decoys = []
    i = 0
    while approx_tokens("\n".join(core_files + decoys)) < target_tokens:
        decoys.append(code_file(f"service_{i:03d}/module_{i:03d}.py", f"""
class Service{i:03d}:
    def __init__(self, config):
        self.config = config
        self.cache = {{}}

    def normalize_entity_{i:03d}(self, item):
        # Similar shape but not a transaction parser duplicate.
        entity_id = str(item.get('entity_id', '')).strip()
        status = item.get('status', 'unknown')
        return {{'entity_id': entity_id, 'status': status, 'source': 'service_{i:03d}'}}

    def invalidate(self, key):
        self.cache.pop(key, None)
"""))
        i += 1
    return "\n\n---\n\n".join(core_files + decoys)


def make_duplicate_logic(tier: str, target_tokens: int) -> tuple[str, dict]:
    repo = make_repo_files(max(5000, target_tokens - 1200))
    prompt = f"""You are analyzing a codebase for duplicated logic.
Return ONLY valid JSON with keys: duplicates, false_positive_risks.
For each duplicate include: files, function_or_area, similarity_reason, risk, refactor_suggestion.
Do not invent files.

CODEBASE START
{repo}
CODEBASE END
"""
    return prompt, {
        "duplicate_group": [
            "payment_gateway/adapters.py",
            "billing_service/handlers.py",
            "reconciler/core.py",
            "audit_logger/extract.py",
        ],
        "decoy_prefix": "service_",
        "scoring_type": "duplicate_logic",
    }


def make_repo_architecture(tier: str, target_tokens: int) -> tuple[str, dict]:
    repo = make_repo_files(max(5000, target_tokens - 1000))
    prompt = f"""You are reviewing a large repo.
Return structured text with: entry points, data flow, key modules, external dependencies, hidden coupling, risky files, suggested refactor areas.
Do not write code. Do not invent filenames.

REPO START
{repo}
REPO END
"""
    return prompt, {
        "must_mention": ["payment_gateway/adapters.py", "billing_service/handlers.py", "reconciler/core.py", "audit_logger/extract.py", "config.py", "scheduler.py"],
        "scoring_type": "repo_architecture",
    }


def make_bug_risk(tier: str, target_tokens: int) -> tuple[str, dict]:
    repo = make_repo_files(max(5000, target_tokens - 1000))
    prompt = f"""Identify cross-file operational bugs that require combining evidence across files.
Rank by severity and cite evidence filenames.

REPO START
{repo}
REPO END
"""
    return prompt, {
        "risk_terms": ["timeout", "retry", "interval", "overlap", "scheduler", "150", "20"],
        "files": ["config.py", "client.py", "worker.py", "scheduler.py", "tests/test_scheduler.py"],
        "scoring_type": "bug_risk",
    }


def make_refactor_plan(tier: str, target_tokens: int) -> tuple[str, dict]:
    repo = make_repo_files(max(5000, target_tokens - 1000))
    prompt = f"""Create a refactor plan only. Do NOT write code.
Goal: consolidate duplicated transaction parsing behavior without caller-visible changes.
Return: canonical implementation, files to change, tests, backwards compatibility, Phase 1/2/3 rollout, rollback plan.

REPO START
{repo}
REPO END
"""
    return prompt, {"scoring_type": "refactor_plan", "must_not_include_code": True}


def financial_docs(target_tokens: int) -> str:
    base = []
    # Explicit contradiction set for same trust/same period.
    base.append("""
## CICT — Annual Report FY2025 — Section A
Revenue: SGD 1,240.0 million. Net property income: SGD 930.0 million.
Distribution per unit: 8.40 cents. Payout ratio: 72%.
WALE: 3.2 years. Occupancy: 95%.
Management says refinancing risk is moderate and debt cost is stable.
""")
    base.append("""
## CICT — Earnings Note FY2025 — Section B
Revenue: SGD 1,240.0 million. Net property income: SGD 930.0 million.
Distribution per unit: 8.40 cents. Payout ratio: 91%.
WALE: 5.8 years. Occupancy: 95%.
Management says refinancing risk is elevated due to near-term maturities.
""")
    base.append("""
## MIT — Annual Report FY2025 — Section C
Revenue: SGD 890.0 million. Net property income: SGD 680.0 million.
Distribution per unit: 13.20 cents. Payout ratio: 76%.
WALE: 4.1 years. Occupancy: 93%.
""")
    i = 0
    while approx_tokens("\n".join(base)) < target_tokens:
        base.append(f"""
## Synthetic REIT Supplement {i:04d}
Revenue: SGD {800+i%400}.0 million. Net property income: SGD {600+i%250}.0 million.
Distribution per unit: {7.0 + (i % 50)/10:.2f} cents. Payout ratio: {65 + i % 20}%.
WALE: {2 + (i % 5)}.{i % 10} years. Occupancy: {86 + i % 12}%.
Management commentary emphasizes active asset management, portfolio resilience, capital recycling, and debt maturity management.
""")
        i += 1
    return "\n".join(base)


def make_finance_memo(tier: str, target_tokens: int) -> tuple[str, dict]:
    docs = financial_docs(max(5000, target_tokens - 1200))
    prompt = f"""You are preparing a trading advisory research memo based ONLY on provided documents.
Return sections: executive summary, bull case, bear case, key metrics with citations, risks, contradictions, missing data, final watchlist decision.
Separate facts from inference. Do not hallucinate numbers.

DOCUMENTS START
{docs}
DOCUMENTS END
"""
    return prompt, {
        "contradictions": ["CICT FY2025 payout ratio 72% vs 91%", "CICT FY2025 WALE 3.2 vs 5.8"],
        "scoring_type": "finance_memo",
    }


def make_json_rules(tier: str, target_tokens: int) -> tuple[str, dict]:
    fillers = split_filler(max(1000, target_tokens - 1200), 4, 500, "JSONRULE")
    prompt = f"""Rule A: Output JSON only. No markdown fences. No explanation.
Rule B: Deprecated models are codestral-22b-q4 and carnice-v2-27b-q2.
{fillers[0]}
Rule C: Any model with fin-code below 4.0 must have not_for_code=true.
{fillers[1]}
Rule D: Prefer q8_0 KV cache unless explicitly testing q4 variants.
{fillers[2]}
Final task: produce a JSON object with key routing. It must contain an array named models for:
- unsloth-qwen3-coder-30b-a3b-q4-64k with fin_code 4.52
- devstral-small2-24b-q4 with fin_code 4.50
- unsloth-granite-4.1-8b-q5 with fin_code 3.76
- codestral-22b-q4 with fin_code 4.00
Each item needs name, recommended_for, cache_type, deprecated, not_for_code.
{fillers[3]}
"""
    return prompt, {"scoring_type": "json_rules"}


BUILDERS = {
    "needle_position": make_needle_position,
    "conflict_policy": make_conflict_policy,
    "repo_architecture": make_repo_architecture,
    "duplicate_logic": make_duplicate_logic,
    "bug_risk": make_bug_risk,
    "refactor_plan": make_refactor_plan,
    "finance_memo": make_finance_memo,
    "json_rules": make_json_rules,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tiers", nargs="+", default=["32k", "64k", "128k"], choices=TIERS.keys())
    ap.add_argument("--tasks", nargs="+", default=list(BUILDERS.keys()), choices=BUILDERS.keys())
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    keys: dict[str, dict] = {}

    for tier in args.tiers:
        for task, builder in BUILDERS.items():
            if task not in args.tasks:
                continue

            target = TIERS[tier]

            # Finance prose tokenizes larger than our rough chars/4 estimate,
            # so use a lower target to avoid llama.cpp context overflow.
            if task == "finance_memo":
                if tier == "32k":
                    target = 25_000
                elif tier == "64k":
                    target = 52_000
                elif tier == "128k":
                    target = 105_000

            prompt, key = builder(tier, target)
            meta = write_prompt(task, tier, prompt, key, args.force)
            keys[f"{task}-{tier}"] = meta

            print(
                f"generated {meta['file']} "
                f"~{meta['approx_tokens']} tokens "
                f"(target={target})"
            )

    ANSWER_KEYS.write_text(json.dumps(keys, indent=2))
    print(f"answer keys: {ANSWER_KEYS}")


if __name__ == "__main__":
    main()
