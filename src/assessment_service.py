"""Glue between intake -> rule engine -> narrative -> persistence.
Shared by the seed loader and the New Assessment page so both go through
the exact same code path (no special-casing of demo data)."""

import json
from datetime import datetime, timezone

from src.db import query, query_one, run
from src.llm_explainer import generate_narrative
from src.options import resolve_rule_profile
from src.scoring_engine import evaluate, load_criteria_from_db


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save_use_case(conn, use_case, is_seed=False, commit=True):
    cur = run(
        conn,
        """INSERT INTO use_cases
           (name, industry, function, data_types_json, autonomy, affects_vulnerable,
            vulnerable_groups_json, jurisdictions_json, model_type, is_samd, third_party,
            monitoring, explainability_method, description, is_seed, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            use_case["name"],
            use_case.get("industry", "Healthcare & Life Sciences"),
            use_case["function"],
            json.dumps(use_case["data_types"]),
            use_case["autonomy"],
            1 if use_case["affects_vulnerable"] else 0,
            json.dumps(use_case.get("vulnerable_groups", [])),
            json.dumps(use_case["jurisdictions"]),
            use_case["model_type"],
            1 if use_case["is_samd"] else 0,
            use_case["third_party"],
            use_case["monitoring"],
            use_case["explainability_method"],
            use_case.get("description", ""),
            1 if is_seed else 0,
            _now(),
        ),
        commit=commit,
    )
    return cur.lastrowid


def run_and_persist_assessment(conn, use_case, is_seed=False, force_template=False):
    """use_case: dict of intake fields (see save_use_case). Returns assessment_id.

    All of this use case's writes (use_cases + assessments + N dimension rows —
    11+ statements) are one transaction, committed once at the end. Committing
    per-statement (the original approach) meant every assessment cost as many
    fsyncs as it had rows; at 1,000 assessments that was the difference between
    ~15s and ~3 minutes end to end (measured) — the fix is this batching, not a
    different database."""
    use_case_id = save_use_case(conn, use_case, is_seed=is_seed, commit=False)

    rule_profile = resolve_rule_profile(use_case.get("industry", "Healthcare & Life Sciences"))
    criteria = load_criteria_from_db(conn, rule_profile)
    result = evaluate(use_case, criteria)
    narrative, narrative_source = generate_narrative(use_case, result, conn, force_template=force_template)

    cur = run(
        conn,
        """INSERT INTO assessments
           (use_case_id, created_at, overall_score, overall_level, critical_flags_json,
            narrative, narrative_source, model_used)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            use_case_id,
            _now(),
            result["overall_score"],
            result["overall_level"],
            json.dumps(result["critical_flags"]),
            narrative,
            narrative_source,
            "" if narrative_source == "template" else "gemini",
        ),
        commit=False,
    )
    assessment_id = cur.lastrowid

    dims = list(result["dimensions"].items())
    for i, (dim, data) in enumerate(dims):
        matched_ids = [m["id"] for m in data["matches"]]
        run(
            conn,
            """INSERT INTO assessment_dimensions
               (assessment_id, dimension, score, level, matched_criteria_json)
               VALUES (?, ?, ?, ?, ?)""",
            (assessment_id, dim, data["score"], data["level"], json.dumps(matched_ids)),
            commit=(i == len(dims) - 1),  # only the last statement in the batch commits
        )

    return {
        "assessment_id": assessment_id,
        "use_case_id": use_case_id,
        "result": result,
        "narrative": narrative,
        "narrative_source": narrative_source,
    }


def use_case_row_to_dict(row):
    (uc_id, name, industry, function, data_types_json, autonomy, affects_vulnerable,
     vulnerable_groups_json, jurisdictions_json, model_type, is_samd, third_party,
     monitoring, explainability_method, description, is_seed, created_at) = row
    return {
        "id": uc_id, "name": name, "industry": industry, "function": function,
        "data_types": json.loads(data_types_json), "autonomy": autonomy,
        "affects_vulnerable": bool(affects_vulnerable),
        "vulnerable_groups": json.loads(vulnerable_groups_json),
        "jurisdictions": json.loads(jurisdictions_json), "model_type": model_type,
        "is_samd": bool(is_samd), "third_party": third_party, "monitoring": monitoring,
        "explainability_method": explainability_method, "description": description,
        "is_seed": bool(is_seed), "created_at": created_at,
    }


def list_assessments(conn):
    """Flat list for the Dashboard, newest first."""
    rows = query(
        conn,
        """SELECT a.id, a.created_at, a.overall_score, a.overall_level, a.critical_flags_json,
                  a.narrative_source, u.name, u.function, u.id, u.industry
           FROM assessments a JOIN use_cases u ON u.id = a.use_case_id
           ORDER BY a.id DESC""",
    )
    return [
        {
            "assessment_id": r[0], "created_at": r[1], "overall_score": r[2], "overall_level": r[3],
            "critical_flags": json.loads(r[4]), "narrative_source": r[5],
            "use_case_name": r[6], "function": r[7], "use_case_id": r[8], "industry": r[9],
        }
        for r in rows
    ]


def load_assessment_full(conn, assessment_id):
    """Reconstructs the same {dimensions, overall_score, overall_level, critical_flags}
    shape evaluate() produces, but from persisted rows, plus the use case and narrative."""
    a_row = query_one(
        conn,
        """SELECT id, use_case_id, created_at, overall_score, overall_level,
                  critical_flags_json, narrative, narrative_source, model_used
           FROM assessments WHERE id = ?""",
        (assessment_id,),
    )
    if not a_row:
        return None
    (_, use_case_id, created_at, overall_score, overall_level,
     critical_flags_json, narrative, narrative_source, model_used) = a_row

    uc_row = query_one(conn, "SELECT * FROM use_cases WHERE id = ?", (use_case_id,))
    use_case = use_case_row_to_dict(uc_row)

    criteria_by_id = {c["id"]: c for c in load_criteria_from_db(conn, resolve_rule_profile(use_case["industry"]))}

    dim_rows = query(
        conn,
        "SELECT dimension, score, level, matched_criteria_json FROM assessment_dimensions WHERE assessment_id = ?",
        (assessment_id,),
    )
    dimensions = {}
    for dim, score, level, matched_json in dim_rows:
        matched_ids = json.loads(matched_json)
        matches = [criteria_by_id[cid] for cid in matched_ids if cid in criteria_by_id]
        dimensions[dim] = {"score": score, "level": level, "matches": matches}

    return {
        "assessment_id": assessment_id,
        "created_at": created_at,
        "use_case": use_case,
        "narrative": narrative,
        "narrative_source": narrative_source,
        "result": {
            "dimensions": dimensions,
            "overall_score": overall_score,
            "overall_level": overall_level,
            "critical_flags": json.loads(critical_flags_json),
        },
    }
