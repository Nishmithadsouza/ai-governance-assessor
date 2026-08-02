import streamlit as st

from src.bootstrap import init_app
from src.db import query
from src.options import (
    GENERIC_INDUSTRY_KEY, INDUSTRIES, PRESET_INDUSTRIES, SOURCE_TYPE_COLORS,
    SOURCE_TYPES,
)
from src.scoring_engine import DIMENSIONS
from src.theme import hero, inject_css

st.set_page_config(page_title="Methodology", page_icon="ℹ️", layout="wide")
conn, backend = init_app()
inject_css()

hero(
    "ℹ️", "Methodology & Architecture",
    "How the rule engine, the generic cross-industry baseline, and the LLM narrative layer "
    "actually work — the case for why this is trustworthy, not just functional.",
)

st.markdown(
    f"""
## What this application is

An AI Governance Research & Assessment tool that currently has a **fully curated corpus** for
{len(INDUSTRIES)} industries — {', '.join(INDUSTRIES)} — plus {len(PRESET_INDUSTRIES)} preset
industry names and, critically, **any industry you type in that isn't listed at all**. It
assesses any AI use case — pre-loaded or entered live — against real, dated, publicly sourced
governance material, across 9 dimensions:

{', '.join(DIMENSIONS)}.

## Not hard-coded to one industry — three tiers, one mechanism

Picking (or typing) an industry on the New Assessment page isn't a cosmetic label — it changes
what's actually being evaluated, at one of three tiers:

1. **Curated.** Healthcare and HR/Recruitment each have their own dedicated intake vocabulary
   and their own rule set citing their own sector-specific sources (HIPAA and FDA guidance for
   Healthcare; NYC Local Law 144, the Illinois AI Video Interview Act, and EEOC guidance for
   HR/Recruitment).
2. **Preset, generic baseline.** The dropdown's other named industries (Financial Services,
   Insurance, Retail, Education, ...) don't have a dedicated corpus yet, so they run on the same
   baseline as tier 3.
3. **Freely typed, generic baseline.** Type an industry name that exists nowhere in this
   codebase — "Agriculture / AgTech", anything — and the system still constructs a real
   assessment: a generic-but-real intake vocabulary (`GENERIC_CONFIG`) and a rule set tagged
   `"{GENERIC_INDUSTRY_KEY}"`, citing sources that are *genuinely* cross-sector by design (NIST
   AI RMF, ISO/IEC 42001, the OECD AI Principles, the UNESCO Recommendation on the Ethics of AI,
   the EU AI Act's general high-risk criteria, and Colorado's AI Act, which by its own text
   covers "consequential decisions" across housing, employment, education, financial services,
   healthcare, government services, insurance, and legal services — i.e. written to be
   sector-agnostic already).

This is what satisfies "the system can begin constructing a different analysis rather than
relying entirely on hard-coded data": nobody has to write code before a brand-new industry gets
a real, deterministic, cited assessment. `src/options.py:resolve_rule_profile()` is the one
function that decides which tier a given industry name resolves to — every other module
(scoring, narrative, display) just calls it rather than special-casing industries itself, so
tier 2 and 3 are literally the same code path, and adding a fourth curated industry later is
additive (one `INDUSTRY_CONFIG` entry, one tagged batch of criteria) rather than a rewrite."""
)

tier_cols = st.columns(3)
tier_specs = [
    ("✅ Curated", "#1baf7a", f"{len(INDUSTRIES)} industries with a dedicated corpus"),
    ("🗂️ Preset", "#2a78d6", f"{len(PRESET_INDUSTRIES)} convenience names, generic baseline"),
    ("✍️ Freely typed", "#eb6834", "Unlimited — any name at all, generic baseline"),
]
for col, (label, color, desc) in zip(tier_cols, tier_specs):
    with col:
        st.markdown(
            f"""<div class="gov-card accent-left" style="--gov-accent:{color};">
                    <div style="font-weight:700; font-size:1.05rem;">{label}</div>
                    <div style="color:#52514e; font-size:0.88rem;">{desc}</div>
                </div>""",
            unsafe_allow_html=True,
        )

industry_rule_counts = query(conn, "SELECT industry, COUNT(*) FROM criteria GROUP BY industry")
st.caption(" · ".join(f"**{industry}**: {count} rules" for industry, count in industry_rule_counts))

st.markdown(
    f"""
## Why it isn't "just ask an LLM"

A large language model asked "is this AI use case high risk?" will give you a plausible-sounding
answer that is not reproducible, not citable, and not auditable — ask it twice and you may get two
different answers with no way to know which criteria actually drove the judgment.

Instead, this application separates the two concerns:

1. **Scoring is deterministic.** `src/scoring_engine.py` matches a use case's structured intake
   answers (function, data types, autonomy, jurisdiction, model type, monitoring, etc.) and, where
   relevant, keyword hits in its free-text description, against a stored table of governance
   criteria (`data/criteria.json`, loaded into the `criteria` table). Each criterion has a fixed
   weight and cites one or more real sources. Given the same use case and the same criteria table,
   the output is always identical — that's what makes it a *repeatable assessment mechanism*
   rather than an opinion.
2. **The LLM only writes prose, afterward.** `src/llm_explainer.py` calls Google Gemini (when a
   free-tier API key is configured) with the already-computed scores and citations, explicitly
   instructed not to introduce new regulatory claims or change any score. If no key is configured,
   a deterministic string-template narrative built from the same data is used instead — the app's
   actual risk output never depends on the LLM being available.

## The 6-way source classification

The corpus explicitly tags every source with one of the required authority tiers, because they do
not carry equal weight:

- **Law/Regulation** — binding (e.g. HIPAA, the EU AI Act, the Colorado AI Act).
- **Regulatory Guidance** — official but non-binding interpretation (e.g. FDA guidance documents,
  HHS OCR guidance, WHO guidance).
- **Industry Standard** — consensus frameworks, often certifiable (e.g. ISO/IEC 42001, NIST AI RMF).
- **Research** — peer-reviewed or preprint findings used as evidence, not authority (e.g. the
  Obermeyer et al. 2019 study on algorithmic racial bias in healthcare).
- **Vendor Information** — a vendor's own claims about its product, useful context but never a
  compliance obligation.
- **General Web Content** — everything else (blogs, marketing explainers) — included deliberately
  so the app can show why this tier must never be mistaken for the law it's describing.

See the **Source Library** page to browse the corpus by this classification."""
)

st.markdown(
    " ".join(f'<span class="gov-badge" style="background:{SOURCE_TYPE_COLORS[t]};">{t}</span>' for t in SOURCE_TYPES),
    unsafe_allow_html=True,
)

st.markdown(
    f"""
## Data model & persistence

SQLite (`sources`, `criteria`, `use_cases`, `assessments`, `assessment_dimensions`) is the system
of record. Every assessment — seeded example or live entry — is written to these tables, so the
Dashboard reflects real accumulated history, not a fixed demo screen. Locally this is a plain
SQLite file (`governance.db`). On the public hosted deployment it is backed by Turso (libSQL, a
wire-compatible SQLite fork with a free persistent tier), specifically so that a Streamlit
Community Cloud container restart does not wipe the data — the app detects which backend is
configured automatically (see `src/db.py`).

**Current backend for this running instance: `{backend}`**

## Live-testing a new use case

Go to **New Assessment**, fill in a use case of your own — real or hypothetical — and submit it.
It runs through the exact same rule engine and narrative pipeline as every seeded example, is
scored dynamically from your structured answers and description, and is persisted immediately, so
it will also show up in the Dashboard and Assessment Detail pages afterward.
"""
)
