"""Small text-matching helpers shared by the UI. No external NLP dependency —
this is intentionally simple/deterministic so it's easy to audit, matching
the philosophy of the rule engine it supports."""


def matched_keywords(description, criteria):
    """Returns {criterion_id: [keyword, ...]} for every keyword that actually
    appears in the free-text description, so a reviewer can see exactly why a
    keyword-based rule fired."""
    text = (description or "").lower()
    hits = {}
    for c in criteria:
        found = [kw for kw in c.get("keyword_any", []) if kw.lower() in text]
        if found:
            hits[c["id"]] = found
    return hits


def text_contains_all(haystack, needles):
    haystack = (haystack or "").lower()
    return all(n.lower() in haystack for n in needles if n)
