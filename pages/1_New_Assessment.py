import streamlit as st

from src.assessment_service import run_and_persist_assessment
from src.bootstrap import init_app
from src.nlp_utils import matched_keywords
from src.options import (
    AUTONOMY_OPTIONS, EXPLAINABILITY_OPTIONS, GENERIC_CONFIG, INDUSTRIES,
    JURISDICTIONS, MODEL_TYPES, MONITORING_OPTIONS, OTHER_INDUSTRY_OPTION,
    PRESET_INDUSTRIES, THIRD_PARTY_OPTIONS, get_industry_config, is_curated,
    resolve_rule_profile,
)
from src.render import render_dimension_breakdown, render_overall_summary, source_lookup
from src.scoring_engine import load_criteria_from_db
from src.theme import hero, inject_css

st.set_page_config(page_title="New Assessment", page_icon="📋", layout="wide")
conn, backend = init_app()
inject_css()

hero(
    "📋", "New Assessment",
    "The live-test surface: enter any AI use case — including one you make up right now — "
    "and the deterministic rule engine will score it dynamically. Nothing here is hard-coded per use case.",
)

# Outside the form so changing it immediately swaps which functions/data types/
# groups appear below — proof the app constructs a different analysis per
# industry rather than relying on one hard-coded framework. Three tiers:
# curated (own corpus), preset (convenience name, generic baseline), and a
# fully free-typed industry (also generic baseline) — the system never
# refuses an industry it wasn't specifically pre-coded for.
industry_choices = INDUSTRIES + PRESET_INDUSTRIES + [OTHER_INDUSTRY_OPTION]


def _format_industry(i):
    if i == OTHER_INDUSTRY_OPTION:
        return f"✍️ {i}"
    return f"{get_industry_config(i)['icon']} {i}"


selected = st.selectbox("Industry", industry_choices, format_func=_format_industry, key="industry_select")

if selected == OTHER_INDUSTRY_OPTION:
    industry = st.text_input(
        "Type the industry",
        placeholder="e.g. Agriculture / AgTech, Legal Services, Energy & Utilities...",
        key="custom_industry",
    ).strip()
else:
    industry = selected

cfg = get_industry_config(industry) if industry else GENERIC_CONFIG

if industry and is_curated(industry):
    st.success(f"✅ **Curated tier** — showing the dedicated intake questions and rule set built specifically for **{industry}**.")
elif industry:
    st.info(
        f"🌐 **Generic cross-industry baseline** — no dedicated corpus exists yet for **{industry}**, so the assessment is "
        "constructed from universal, real, cited governance sources (NIST AI RMF, ISO/IEC 42001, OECD AI Principles, the "
        "UNESCO AI Ethics Recommendation, the EU AI Act, and Colorado's AI Act) that apply across sectors. Scoring is still "
        "fully deterministic and citation-backed — just less deep than a dedicated corpus would be."
    )
else:
    st.warning("Type an industry name above to continue.")

with st.form("intake_form"):
    st.subheader("📝 Use case")
    name = st.text_input("Use case name*", placeholder="e.g. AI-Assisted Diabetic Retinopathy Screening")
    function = st.selectbox("Primary function*", cfg["functions"])
    description = st.text_area(
        "Describe the use case*",
        placeholder="What does it do, who uses it, what data does it see, how autonomous is it...",
        height=120,
    )

    st.subheader("🗄️ Data & model")
    col1, col2 = st.columns(2)
    with col1:
        data_types = st.multiselect("Data types processed*", cfg["data_types"])
        model_type = st.selectbox("Model type*", MODEL_TYPES)
        is_samd = st.checkbox(cfg["regulated_flag_label"])
    with col2:
        third_party = st.selectbox("Build ownership*", THIRD_PARTY_OPTIONS)
        explainability_method = st.selectbox("Explainability method available*", EXPLAINABILITY_OPTIONS)
        monitoring = st.selectbox("Post-deployment monitoring in place*", MONITORING_OPTIONS)

    st.subheader("⚖️ Decision context")
    col3, col4 = st.columns(2)
    with col3:
        autonomy = st.selectbox("Decision autonomy*", AUTONOMY_OPTIONS)
        jurisdictions = st.multiselect("Deployment jurisdiction(s)*", JURISDICTIONS)
    with col4:
        affects_vulnerable = st.checkbox("Affects a vulnerable / historically underserved population")
        vulnerable_groups = st.multiselect("Which group(s)?", cfg["vulnerable_groups"], disabled=False)

    submitted = st.form_submit_button("Run Assessment", type="primary")

if submitted:
    if not industry:
        st.error("Please type an industry name (you selected \"Other\").")
    elif not name.strip() or not description.strip() or not data_types or not jurisdictions:
        st.error("Please fill in the use case name, description, at least one data type, and at least one jurisdiction.")
    else:
        use_case = {
            "name": name.strip(),
            "industry": industry,
            "function": function,
            "data_types": data_types,
            "autonomy": autonomy,
            "affects_vulnerable": affects_vulnerable,
            "vulnerable_groups": vulnerable_groups if affects_vulnerable else [],
            "jurisdictions": jurisdictions,
            "model_type": model_type,
            "is_samd": is_samd,
            "third_party": third_party,
            "monitoring": monitoring,
            "explainability_method": explainability_method,
            "description": description.strip(),
        }
        with st.spinner("Running the rule engine and generating the narrative..."):
            outcome = run_and_persist_assessment(conn, use_case)
        st.session_state["last_assessment"] = outcome
        st.session_state["last_use_case"] = use_case

if "last_assessment" in st.session_state:
    st.divider()
    outcome = st.session_state["last_assessment"]
    use_case = st.session_state["last_use_case"]
    result = outcome["result"]

    st.success(f"Assessment #{outcome['assessment_id']} saved for **{use_case['name']}** ({use_case['industry']}).")
    render_overall_summary(result["overall_score"], result["overall_level"], result["critical_flags"])

    st.subheader("📐 Dimension-by-dimension breakdown, with citations")
    render_dimension_breakdown(result["dimensions"], source_lookup(conn))

    with st.expander("🔑 Which keywords in your description triggered a rule?"):
        criteria = load_criteria_from_db(conn, resolve_rule_profile(use_case["industry"]))
        hits = matched_keywords(use_case["description"], criteria)
        if hits:
            for cid, kws in hits.items():
                st.write(f"`{cid}` matched on: {', '.join(kws)}")
        else:
            st.caption("No free-text keyword rules fired — all matches for this use case came from the structured fields.")

    st.subheader(f"🗣️ Narrative ({'Gemini-generated' if outcome['narrative_source'] == 'gemini' else 'template-generated, no LLM key configured'})")
    st.markdown(outcome["narrative"])
