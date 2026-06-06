#!/usr/bin/env python3
"""Deterministic scoring helpers for generated long-context prompts."""
from __future__ import annotations

import json
import re
from typing import Any


def text_lower(text: str) -> str:
    return (text or "").lower()


def extract_json(text: str) -> Any | None:
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I)
        s = re.sub(r"\s*```$", "", s)
    try:
        return json.loads(s)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text or "", re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def score_needle(text: str, key: dict) -> tuple[int, str]:
    low = text_lower(text)
    facts = key.get("facts", {})
    found = [name for name, val in facts.items() if str(val).lower() in low]
    missing = [name for name in facts if name not in found]
    if len(found) == len(facts):
        return 5, "all position needles found"
    if len(found) >= 4:
        return 4, f"found {len(found)}/{len(facts)}, missing={missing}"
    if len(found) >= 2:
        return 3, f"found {len(found)}/{len(facts)}, missing={missing}"
    if len(found) == 1:
        return 2, f"found one fact only: {found}"
    return 1, "no expected needles found"


def score_conflict(text: str, key: dict) -> tuple[int, str]:
    low = text_lower(text)
    issues = []
    current = key.get("current", "").lower()
    if current not in low:
        issues.append("missing current approved model")
    if not any(x in low for x in ["obsolete", "superseded", "outdated", "earlier"]):
        issues.append("does not mark older statements obsolete")
    for old in key.get("obsolete", []):
        if old.lower() not in low:
            issues.append(f"missing evidence for obsolete model {old}")
    candidate = key.get("candidate_not_current", "").lower()
    if candidate and candidate in low and "current" in low:
        # Only penalize if it appears to make candidate current; simple heuristic.
        if re.search(r"current[^\n]{0,120}" + re.escape(candidate), low) or re.search(re.escape(candidate) + r"[^\n]{0,120}current", low):
            issues.append("candidate confused as current")
    if not issues:
        return 5, "correct current model and obsolete evidence"
    if len(issues) <= 1:
        return 4, "; ".join(issues)
    if len(issues) <= 2:
        return 3, "; ".join(issues)
    return 2, "; ".join(issues)


def score_duplicate(text: str, key: dict) -> tuple[int, str]:
    low = text_lower(text)
    data = extract_json(text)
    group = [x.lower() for x in key.get("duplicate_group", [])]
    found_files = [f for f in group if f in low]
    invented = bool(re.search(r"fake|nonexistent|made_up|unknown\.py", low))
    if invented:
        return 1, "hallucinated filenames"
    if isinstance(data, dict):
        dups = data.get("duplicates", [])
        if not dups:
            return 2, "valid JSON but no duplicates found"
        # Look for a single duplicate entry covering at least 3 known duplicate files.
        best = 0
        for d in dups:
            files = " ".join(map(str, d.get("files", []))).lower()
            count = sum(1 for f in group if f in files)
            best = max(best, count)
        if best >= 4:
            return 5, "all transaction parser duplicate files grouped"
        if best >= 3:
            return 4, "most duplicate files grouped"
        if len(found_files) >= 2:
            return 3, "mentions duplicate files but weak grouping"
        return 2, "JSON present but misses known duplicate group"
    if len(found_files) >= 3 and any(w in low for w in ["duplicate", "duplicated", "similar"]):
        return 4, "text answer found duplicate group but JSON invalid"
    if len(found_files) >= 2:
        return 3, "partial duplicate detection"
    return 2, "known duplicate group not found"


def score_repo_architecture(text: str, key: dict) -> tuple[int, str]:
    low = text_lower(text)
    if re.search(r"fake|nonexistent|made_up|unknown\.py", low):
        return 1, "hallucinated filenames"
    must = [x.lower() for x in key.get("must_mention", [])]
    found = [x for x in must if x in low]
    concepts = ["entry", "data flow", "module", "dependency", "coupling", "risk", "refactor"]
    cfound = [c for c in concepts if c in low]
    if len(found) >= 5 and len(cfound) >= 5:
        return 5, "good architecture coverage with real files"
    if len(found) >= 3 and len(cfound) >= 4:
        return 4, "adequate architecture coverage"
    if len(found) >= 2:
        return 3, "partial file-aware summary"
    return 2, "weak repo architecture summary"


def score_bug_risk(text: str, key: dict) -> tuple[int, str]:
    low = text_lower(text)
    terms = key.get("risk_terms", [])
    files = key.get("files", [])
    term_hits = sum(1 for t in terms if str(t).lower() in low)
    file_hits = sum(1 for f in files if str(f).lower() in low)
    if term_hits >= 5 and file_hits >= 4:
        return 5, "identified timeout/retry/scheduler risk with file evidence"
    if term_hits >= 4 and file_hits >= 2:
        return 4, "identified core cross-file risk"
    if term_hits >= 2:
        return 3, "partial risk detection"
    return 2, "missed dispersed bug risk"


def score_refactor_plan(text: str, key: dict) -> tuple[int, str]:
    low = text_lower(text)
    issues = []
    code_markers = ["\ndef ", "\nclass ", "```python", "import "]
    if sum(1 for m in code_markers if m in low) >= 2:
        issues.append("wrote code instead of plan")
    if not any(x in low for x in ["phase 1", "phase one", "stage 1", "step 1"]):
        issues.append("missing staged plan")
    if not any(x in low for x in ["test", "tests"]):
        issues.append("missing test plan")
    if not any(x in low for x in ["backward", "compatibility", "caller-visible", "callers"]):
        issues.append("missing compatibility discussion")
    if not any(x in low for x in ["rollback", "revert"]):
        issues.append("missing rollback/revert plan")
    if not issues:
        return 5, "safe phased refactor plan"
    if len(issues) <= 1:
        return 4, "; ".join(issues)
    if len(issues) <= 2:
        return 3, "; ".join(issues)
    return 2, "; ".join(issues)


def score_finance(text: str, key: dict) -> tuple[int, str]:
    low = text_lower(text)
    issues = []
    for sec in ["bull", "bear", "metric", "risk", "watchlist"]:
        if sec not in low:
            issues.append(f"missing {sec}")
    if not any(x in low for x in ["section a", "section b", "annual report", "earnings note"]):
        issues.append("missing source citations")
    # Require explicit contradictions.
    if not ("72" in low and "91" in low and "payout" in low):
        issues.append("missed payout contradiction")
    if not ("3.2" in low and "5.8" in low and "wale" in low):
        issues.append("missed WALE contradiction")
    if not issues:
        return 5, "good memo with explicit contradictions"
    if len(issues) <= 1:
        return 4, "; ".join(issues)
    if len(issues) <= 3:
        return 3, "; ".join(issues)
    return 2, "; ".join(issues)


def score_json_rules(text: str, key: dict) -> tuple[int, str]:
    data = extract_json(text)
    if data is None:
        return 1, "invalid JSON"
    low = text_lower(text)
    issues = []
    if "```" in text:
        issues.append("markdown fence leakage")
    raw = json.dumps(data).lower()
    if "codestral-22b-q4" in raw:
        # It can appear as a listed model, but must be deprecated and not_for_code should not be false.
        pass
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        issues.append("missing models array")
    else:
        by_name = {str(m.get("name", "")).lower(): m for m in models if isinstance(m, dict)}
        granite = by_name.get("unsloth-granite-4.1-8b-q5")
        codestral = by_name.get("codestral-22b-q4")
        for m in models:
            if isinstance(m, dict) and str(m.get("cache_type", "")).lower() != "q8_0":
                issues.append("non-q8_0 cache recommended")
                break
        if granite and granite.get("not_for_code") is not True:
            issues.append("granite fin-code<4 not marked not_for_code")
        if codestral and codestral.get("deprecated") is not True:
            issues.append("codestral not marked deprecated")
    if not issues:
        return 5, "valid JSON and rule-compliant"
    if len(issues) <= 1:
        return 4, "; ".join(issues)
    if len(issues) <= 2:
        return 3, "; ".join(issues)
    return 2, "; ".join(issues)


SCORERS = {
    "needle_position": score_needle,
    "conflict_policy": score_conflict,
    "duplicate_logic": score_duplicate,
    "repo_architecture": score_repo_architecture,
    "bug_risk": score_bug_risk,
    "refactor_plan": score_refactor_plan,
    "finance_memo": score_finance,
    "json_rules": score_json_rules,
}


def score(task_name: str, text: str, answer_key: dict) -> tuple[int, str]:
    st = answer_key.get("scoring_type") or task_name.rsplit("-", 1)[0]
    fn = SCORERS.get(st)
    if not fn:
        return 0, f"no scorer for scoring_type={st}"
    return fn(text, answer_key)
