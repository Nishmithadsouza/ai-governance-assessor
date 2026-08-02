"""
Narrative layer, deliberately kept downstream of the rule engine.

generate_narrative() is handed ONLY the already-computed scores, levels, and
matched citations from scoring_engine.evaluate() — never the raw use case
alone. The prompt explicitly forbids introducing new regulatory claims. If no
GEMINI_API_KEY secret is configured (or the call fails for any reason), a
deterministic string-template narrative is produced instead, built from the
exact same structured data, so the app never depends on an external API to
function.
"""

from src.db import get_secret
from src.scoring_engine import DIMENSIONS


def _source_lookup(conn):
    from src.db import query

    rows = query(conn, "SELECT id, title, publisher, source_type FROM sources")
    return {r[0]: {"title": r[1], "publisher": r[2], "source_type": r[3]} for r in rows}


def _citation_lines(matches, sources_by_id):
    lines = []
    for m in matches:
        cite = "; ".join(
            f"{sources_by_id.get(sid, {}).get('title', sid)} ({sources_by_id.get(sid, {}).get('source_type', 'Unknown')})"
            for sid in m["source_ids"]
        )
        lines.append(f"- [{m['id']}] {m['rationale']} Source(s): {cite}")
    return lines


def _template_narrative(use_case, result, sources_by_id):
    parts = [
        f"**Overall assessment: {result['overall_level']}** (composite score {result['overall_score']}/100) "
        f"for '{use_case['name']}', a {use_case['function'].lower()} use case."
    ]
    if result["critical_flags"]:
        parts.append(
            "**Critical flags requiring immediate attention:** " + ", ".join(result["critical_flags"]) + "."
        )
    ranked = sorted(result["dimensions"].items(), key=lambda kv: kv[1]["score"], reverse=True)
    parts.append("\n**Top risk drivers, most severe first:**")
    for dim, data in ranked[:5]:
        if data["score"] <= 0:
            continue
        parts.append(f"\n*{dim} — {data['level']} ({data['score']}/100)*")
        parts.extend(_citation_lines(data["matches"], sources_by_id))
    parts.append(
        "\n**Recommended next steps:** address the highest-scoring dimensions first, starting with any "
        "dimension flagged Critical; prioritize adding human-oversight and monitoring controls, since those "
        "reduce risk across several dimensions at once."
    )
    return "\n".join(parts)


def generate_narrative(use_case, result, conn, api_key=None, model_name=None, force_template=False):
    """Returns (narrative_text, narrative_source) where narrative_source is 'gemini' or 'template'."""
    sources_by_id = _source_lookup(conn)
    api_key = api_key or get_secret("GEMINI_API_KEY", "")

    if force_template or not api_key:
        return _template_narrative(use_case, result, sources_by_id), "template"

    model_name = model_name or get_secret("GEMINI_MODEL", "gemini-2.5-flash")

    try:
        from google import genai

        evidence = []
        for dim, data in result["dimensions"].items():
            if data["score"] <= 0:
                continue
            evidence.append(f"{dim}: score {data['score']}/100, level {data['level']}")
            evidence.extend(_citation_lines(data["matches"], sources_by_id))

        prompt = f"""You are drafting the narrative section of an AI governance risk assessment report.
A deterministic rule engine has ALREADY computed every score and citation below. Do not invent, soften,
or add any regulatory claim that is not already present in this evidence. Do not change any score or level.

Use case: {use_case['name']}
Function: {use_case['function']}
Description: {use_case.get('description', '(none provided)')}

Overall level: {result['overall_level']} (score {result['overall_score']}/100)
Critical flags: {', '.join(result['critical_flags']) or 'None'}

Evidence (dimension: score/level, then matched criteria with citations):
{chr(10).join(evidence)}

Write a concise report narrative (250-350 words) for a compliance reviewer with two sections:
1. Executive Summary — plain-English summary of the overall risk posture and why, referencing the
   evidence above by dimension.
2. Recommended Mitigations — 3 to 5 concrete, prioritized actions, each tied to a specific dimension
   from the evidence above.
Do not use markdown headers other than bold text for the two section titles."""

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model_name, contents=prompt)
        text = (response.text or "").strip()
        if not text:
            raise ValueError("empty response from Gemini")
        return text, "gemini"
    except Exception as exc:  # noqa: BLE001 - never let a narrative failure break the assessment
        fallback = _template_narrative(use_case, result, sources_by_id)
        fallback += f"\n\n*(Gemini narrative unavailable — using deterministic template. Reason: {exc})*"
        return fallback, "template"
