"""
Deterministic risk-scoring engine.

This is the repeatable assessment mechanism the assignment requires: risk is
NEVER decided by asking an LLM "is this high risk?". Instead, a use case's
structured intake answers (and, secondarily, keyword hits in its free-text
description) are matched against a stored table of governance criteria
(`data/criteria.json` -> `criteria` table). Every matched criterion carries a
fixed weight and a citation to one or more real sources. Given the same
inputs and the same criteria table, this always produces the same output —
that repeatability, plus the citation trail, is what makes the assessment
auditable instead of a black-box LLM opinion.

The LLM (see llm_explainer.py) only ever runs AFTER this module has already
produced scores + citations, to phrase them in prose. It cannot change a
score or invent a citation.
"""

import json

DIMENSIONS = [
    "Data Privacy",
    "Bias/Fairness",
    "Human Oversight",
    "Explainability",
    "Security",
    "Decision Impact",
    "Regulatory Exposure",
    "Model Risk",
    "Monitoring",
]

# (minimum score, level) checked from highest to lowest
LEVEL_BANDS = [(85, "Critical"), (60, "High"), (30, "Medium"), (0, "Low")]


def score_to_level(score):
    for threshold, level in LEVEL_BANDS:
        if score >= threshold:
            return level
    return "Low"


def load_criteria_from_db(conn, industry=None):
    """industry=None returns every industry's rules (used by admin/debug tooling);
    normal assessment flows always pass the use case's own industry so a use case
    is only ever scored against its own industry's rule set."""
    from src.db import query

    if industry:
        rows = query(
            conn,
            "SELECT id, dimension, condition_json, keyword_json, risk_weight, "
            "risk_level_if_matched, rationale, source_ids_json FROM criteria WHERE industry = ?",
            (industry,),
        )
    else:
        rows = query(
            conn,
            "SELECT id, dimension, condition_json, keyword_json, risk_weight, "
            "risk_level_if_matched, rationale, source_ids_json FROM criteria",
        )
    criteria = []
    for r in rows:
        criteria.append(
            {
                "id": r[0],
                "dimension": r[1],
                "condition": json.loads(r[2]),
                "keyword_any": json.loads(r[3]),
                "risk_weight": r[4],
                "risk_level_if_matched": r[5],
                "rationale": r[6],
                "source_ids": json.loads(r[7]),
            }
        )
    return criteria


def _condition_matches(condition, use_case):
    for key, expected in condition.items():
        if key == "multi_jurisdiction":
            actual = len(use_case.get("jurisdictions", []) or []) >= 2
            if actual not in expected:
                return False
            continue
        actual = use_case.get(key)
        if isinstance(actual, list):
            if not any(a in expected for a in actual):
                return False
        else:
            if actual not in expected:
                return False
    return True


def _keyword_matches(keywords, description):
    if not keywords:
        return True
    text = (description or "").lower()
    return any(kw.lower() in text for kw in keywords)


def evaluate(use_case, criteria):
    """
    use_case: dict with keys
      function (str), data_types (list[str]), autonomy (str),
      affects_vulnerable (bool), vulnerable_groups (list[str]),
      jurisdictions (list[str]), model_type (str), is_samd (bool),
      third_party (str), monitoring (str), explainability_method (str),
      description (str)
    criteria: list of normalized criterion dicts (see load_criteria_from_db)

    Returns a dict:
      {
        "dimensions": {
            dim: {"score": float, "level": str, "matches": [criterion, ...]}
        },
        "overall_score": float,
        "overall_level": str,
        "critical_flags": [dim, ...],
      }
    """
    by_dim = {d: {"raw": 0, "matches": []} for d in DIMENSIONS}

    for c in criteria:
        if not _condition_matches(c["condition"], use_case):
            continue
        if not _keyword_matches(c["keyword_any"], use_case.get("description", "")):
            continue
        dim = c["dimension"]
        if dim not in by_dim:
            continue
        by_dim[dim]["raw"] += c["risk_weight"]
        by_dim[dim]["matches"].append(c)

    dimensions_out = {}
    for dim, data in by_dim.items():
        score = max(0, min(100, data["raw"]))
        dimensions_out[dim] = {
            "score": score,
            "level": score_to_level(score),
            "matches": data["matches"],
        }

    # Overall = half mean, half max. A pure mean lets one Critical dimension get
    # diluted into an overall "Medium" by several low-scoring dimensions, which
    # understates real exposure (a single unmitigated critical risk does not
    # become acceptable just because other dimensions are fine). Blending in the
    # single worst dimension keeps the overall level responsive to the worst
    # driver while the mean still reflects the whole risk profile.
    dim_scores = [d["score"] for d in dimensions_out.values()]
    mean_score = sum(dim_scores) / len(DIMENSIONS)
    max_score = max(dim_scores)
    overall_score = round(0.5 * mean_score + 0.5 * max_score, 1)
    overall_level = score_to_level(overall_score)
    critical_flags = [dim for dim, d in dimensions_out.items() if d["level"] == "Critical"]

    return {
        "dimensions": dimensions_out,
        "overall_score": overall_score,
        "overall_level": overall_level,
        "critical_flags": critical_flags,
    }
