import streamlit as st

from src.bootstrap import init_app
from src.db import query, query_one
from src.options import INDUSTRIES, INDUSTRY_CONFIG, PRESET_INDUSTRIES
from src.plain_language import DIMENSION_PLAIN
from src.theme import ACCENTS, big_cta, dimension_showcase, hero, inject_css, nav_card, stat_tiles

st.set_page_config(page_title="AI Governance Assessor", page_icon="🛡️", layout="wide")

conn, backend = init_app()
inject_css()

hero(
    "🛡️",
    "AI Governance Assessor",
    "Describe any AI system in one sentence and get an instant, cited risk check — for any industry.",
)

big_cta("Try it now — assess an AI system in 10 seconds", "pages/1_New_Assessment.py", icon="🚀")

st.write("")
st.subheader("🧭 What we check")
dimension_showcase(list(DIMENSION_PLAIN.values()))

st.write("")
n_sources = query_one(conn, "SELECT COUNT(*) FROM sources")[0]
n_criteria = query_one(conn, "SELECT COUNT(*) FROM criteria")[0]
n_use_cases = query_one(conn, "SELECT COUNT(*) FROM use_cases")[0]
n_assessments = query_one(conn, "SELECT COUNT(*) FROM assessments")[0]

stat_tiles(
    [
        ("Cited sources in corpus", n_sources, ACCENTS[0]),
        ("Governance criteria (rules)", n_criteria, ACCENTS[1]),
        ("Use cases assessed", n_use_cases, ACCENTS[2]),
        ("Assessments on record", n_assessments, ACCENTS[3]),
    ]
)

with st.expander("ℹ️ How does this work, exactly?"):
    st.markdown(
        f"""
This application assesses AI use cases against a curated, citation-backed corpus of real
AI governance sources, across **9 governance dimensions** (shown above) — for whichever
industry you select, or type in yourself.

**How it decides risk — and how it doesn't.** Every score comes from a deterministic rule
engine that matches a use case's structured intake answers (and keyword hits in its
description) against a stored table of governance criteria, each tied to a real, dated
public source. An LLM (Google Gemini, when configured) is only used *afterward*, to turn
the already-computed scores and citations into readable prose — it cannot originate a risk
judgment or invent a citation. See **Methodology** for the full explanation.

**Not hard-coded to one industry.** Picking a different industry on the New Assessment page
swaps in a different intake vocabulary and a different rule set — it constructs a genuinely
different analysis, not a relabeled copy of the same one. {len(INDUSTRIES)} industries
({', '.join(INDUSTRIES)}) have a full dedicated corpus. Every other industry — pick one of
{len(PRESET_INDUSTRIES)} presets, or **type any industry name that doesn't exist in the
dropdown at all** — is scored against a real, cited, industry-agnostic baseline (NIST AI RMF,
ISO/IEC 42001, OECD AI Principles, the UNESCO AI Ethics Recommendation, the EU AI Act,
Colorado's AI Act) instead of being refused or faked.
"""
    )
    industry_counts = query(conn, "SELECT industry, COUNT(*) FROM criteria GROUP BY industry")
    st.caption(" · ".join(f"{i}: {n} rules" for i, n in industry_counts))

st.divider()
st.subheader("Where to go")

r1c1, r1c2 = st.columns(2)
r2c1, r2c2 = st.columns(2)

with r1c1:
    nav_card(
        "📋", "New Assessment",
        "Enter any AI use case, including one you make up on the spot, and get a dynamic, "
        "dimension-by-dimension risk assessment with citations.",
        "pages/1_New_Assessment.py", ACCENTS[0],
    )
with r1c2:
    nav_card(
        "📊", "Dashboard",
        "See every assessment run so far, aggregated across dimensions and risk levels.",
        "pages/2_Dashboard.py", ACCENTS[1],
    )
with r2c1:
    nav_card(
        "🔎", "Assessment Detail",
        "Reopen and fully trace any past assessment, exactly as it was computed.",
        "pages/3_Assessment_Detail.py", ACCENTS[2],
    )
with r2c2:
    nav_card(
        "📚", "Source Library",
        "Browse the underlying citation corpus, filterable by the 6 required source-authority types.",
        "pages/4_Source_Library.py", ACCENTS[3],
    )

nav_card(
    "ℹ️", "Methodology",
    "How the rule engine, the generic cross-industry baseline, and the LLM narrative layer actually work.",
    "pages/5_About.py", "#4a3aa7",
)

st.divider()
st.caption(f"Storage backend: {backend} · Data persists across restarts on this backend.")
