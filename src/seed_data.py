"""Idempotent seeding: safe to call on every app start.

- `sources` and `criteria` are reference data we control (curated research) —
  they are upserted every run so editing the JSON files and redeploying
  always reflects the latest corpus, with no duplication (both tables are
  keyed by a stable text id).
- The example `use_cases`/`assessments` are only created once, guarded by a
  flag in `meta`, so an evaluator's own runs (and a second load of the app)
  never get overwritten or duplicated.
"""

import json

from src.assessment_service import run_and_persist_assessment
from src.db import load_json, query_one, run

SEED_FLAG_KEY = "seed_use_cases_loaded"


def ensure_seeded(conn):
    _upsert_sources(conn)
    _upsert_criteria(conn)
    _seed_example_use_cases(conn)


def _upsert_sources(conn):
    for s in load_json("sources.json"):
        run(
            conn,
            """INSERT OR REPLACE INTO sources
               (id, title, publisher, source_type, url, jurisdiction, published_date, retrieved_date, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                s["id"], s["title"], s["publisher"], s["source_type"], s["url"],
                s["jurisdiction"], s["published_date"], s["retrieved_date"], s["summary"],
            ),
        )


def _upsert_criteria(conn):
    for c in load_json("criteria.json"):
        run(
            conn,
            """INSERT OR REPLACE INTO criteria
               (id, dimension, industry, condition_json, keyword_json, risk_weight,
                risk_level_if_matched, rationale, source_ids_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                c["id"], c["dimension"], c.get("industry", "Healthcare & Life Sciences"),
                json.dumps(c["condition"]), json.dumps(c["keyword_any"]),
                c["risk_weight"], c["risk_level_if_matched"], c["rationale"], json.dumps(c["source_ids"]),
            ),
        )


SEED_USE_CASE_FILES = ["seed_use_cases.json", "seed_use_cases_hr.json"]


def _seed_example_use_cases(conn):
    already_seeded = query_one(conn, "SELECT value FROM meta WHERE key = ?", (SEED_FLAG_KEY,))
    if already_seeded:
        return

    for filename in SEED_USE_CASE_FILES:
        for use_case in load_json(filename):
            run_and_persist_assessment(conn, use_case, is_seed=True, force_template=True)

    run(conn, "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (SEED_FLAG_KEY, "1"))
