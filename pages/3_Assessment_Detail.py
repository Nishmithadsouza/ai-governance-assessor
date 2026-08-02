import streamlit as st

from src.assessment_service import list_assessments, load_assessment_full
from src.bootstrap import init_app
from src.options import get_industry_config, is_curated, level_badge
from src.render import render_dimension_breakdown, render_overall_summary, source_lookup
from src.theme import hero, inject_css, tier_badge

st.set_page_config(page_title="Assessment Detail", page_icon="🔎", layout="wide")
conn, backend = init_app()
inject_css()

hero(
    "🔎", "Assessment Detail",
    "Re-open any past assessment exactly as it was computed and persisted — full traceability, "
    "not just a live-session view.",
)

assessments = list_assessments(conn)
if not assessments:
    st.info("No assessments yet. Run one from the New Assessment page.")
    st.stop()

options = {f"#{a['assessment_id']} — {a['use_case_name']} ({a['industry']}, {a['created_at']})": a["assessment_id"] for a in assessments}
choice = st.selectbox("Select an assessment", list(options.keys()))
assessment_id = options[choice]

full = load_assessment_full(conn, assessment_id)
use_case = full["use_case"]
result = full["result"]
regulated_label = get_industry_config(use_case["industry"])["regulated_flag_label"]
curated = is_curated(use_case["industry"])

st.subheader(use_case["name"])
tcol1, tcol2 = st.columns([3, 1])
with tcol1:
    st.caption(f"Assessed {full['created_at']} · Industry: {use_case['industry']} · Function: {use_case['function']}")
with tcol2:
    tier_badge("✅ Curated" if curated else "🌐 Generic baseline", "#1baf7a" if curated else "#2a78d6")

with st.expander("🧾 Intake details", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Data types:**", ", ".join(use_case["data_types"]) or "—")
        st.write("**Model type:**", use_case["model_type"])
        st.write("**Build ownership:**", use_case["third_party"])
        st.write(f"**{regulated_label}:**", "Yes" if use_case["is_samd"] else "No")
    with c2:
        st.write("**Autonomy:**", use_case["autonomy"])
        st.write("**Jurisdictions:**", ", ".join(use_case["jurisdictions"]) or "—")
        st.write("**Monitoring:**", use_case["monitoring"])
        st.write("**Explainability:**", use_case["explainability_method"])
    st.write("**Affects vulnerable group(s):**", ", ".join(use_case["vulnerable_groups"]) if use_case["affects_vulnerable"] else "No")
    st.write("**Description:**", use_case["description"])

render_overall_summary(result["overall_score"], result["overall_level"], result["critical_flags"])

st.subheader("📐 Dimension-by-dimension breakdown, with citations")
render_dimension_breakdown(result["dimensions"], source_lookup(conn))

st.subheader(f"🗣️ Narrative ({'Gemini-generated' if full['narrative_source'] == 'gemini' else 'template-generated'})")
st.markdown(full["narrative"])
