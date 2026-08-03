import streamlit as st

from src.assessment_service import run_and_persist_assessment
from src.bootstrap import init_app
from src.detector import ICON, detect, summarize
from src.nlp_utils import matched_keywords
from src.options import (
    AUTONOMY_OPTIONS, EXPLAINABILITY_OPTIONS, GENERIC_CONFIG, INDUSTRIES,
    JURISDICTIONS, MODEL_TYPES, MONITORING_OPTIONS, OTHER_INDUSTRY_OPTION,
    PRESET_INDUSTRIES, THIRD_PARTY_OPTIONS, get_industry_config, is_curated,
    resolve_rule_profile,
)
from src.render import (
    render_dimension_breakdown, render_overall_summary, render_simple_dimension_grid,
    render_simple_summary, source_lookup,
)
from src.scoring_engine import load_criteria_from_db
from src.theme import hero, inject_css

st.set_page_config(page_title="New Assessment", page_icon="📋", layout="wide")
conn, backend = init_app()
inject_css()

hero(
    "📋", "New Assessment",
    "Describe an AI system in one sentence and get an instant risk check — no forms required "
    "unless you want to fine-tune the details yourself.",
)

FALLBACK_INDUSTRY_NAME = "General / Unspecified Use Case"


def _auto_name(description):
    text = description.strip().rstrip(". ")
    return (text[:60] + "…") if len(text) > 60 else text


def _use_case_from_detection(description, detected, name=None):
    industry_value = detected["industry"][0] or FALLBACK_INDUSTRY_NAME
    return {
        "name": name or _auto_name(description),
        "industry": industry_value,
        "function": detected["function"][0],
        "data_types": detected["data_types"][0],
        "autonomy": detected["autonomy"][0],
        "affects_vulnerable": detected["affects_vulnerable"][0],
        "vulnerable_groups": detected["vulnerable_groups"][0],
        "jurisdictions": detected["jurisdictions"][0],
        "model_type": detected["model_type"][0],
        "is_samd": detected["is_samd"][0],
        "third_party": detected["third_party"][0],
        "monitoring": detected["monitoring"][0],
        "explainability_method": detected["explainability_method"][0],
        "description": description.strip(),
    }


# ---------------------------------------------------------------------------
# The default path: one sentence, one click, straight to a result. No jargon
# form is ever required — detection (src/detector.py, plain keyword matching,
# no LLM, no risk judgment) always resolves every field to *something*
# sensible, so there's nothing left that can block submission.
# ---------------------------------------------------------------------------
st.subheader("⚡ Describe it, get your result")
st.caption("Type one or two plain sentences about what the AI system does — that's all that's required.")
quick_text = st.text_area(
    "What does the AI system do?",
    placeholder="e.g. AI screens resumes and recommends candidates.",
    height=70,
    key="quick_description_input",
)

run_now_clicked = st.button("🚀 Get My Result Now", type="primary")

if run_now_clicked:
    if not quick_text.strip():
        st.warning("Please describe the AI system first.")
    else:
        detected = detect(quick_text.strip())
        use_case = _use_case_from_detection(quick_text, detected)
        with st.spinner("Checking it against real AI governance rules..."):
            outcome = run_and_persist_assessment(conn, use_case)
        st.session_state["last_assessment"] = outcome
        st.session_state["last_use_case"] = use_case

st.divider()

# ---------------------------------------------------------------------------
# Everything below is entirely optional — for anyone (an evaluator, a power
# user) who wants to see or correct exactly what was detected before running,
# rather than trusting the one-click defaults above.
# ---------------------------------------------------------------------------
customize = st.toggle("✏️ Want to review or change the details first?")

if customize:
    if st.button("🔄 Prefill the fields below from my description"):
        if not quick_text.strip():
            st.warning("Type a description in the box above first.")
        else:
            detected = detect(quick_text.strip())
            st.session_state["detected"] = detected

            industry_value, _ = detected["industry"]
            st.session_state["industry_select"] = industry_value or OTHER_INDUSTRY_OPTION
            st.session_state["_cfg_industry"] = industry_value

            st.session_state["description_input"] = quick_text.strip()
            st.session_state["function_select"] = detected["function"][0]
            st.session_state["data_types_select"] = detected["data_types"][0]
            st.session_state["model_type_select"] = detected["model_type"][0]
            st.session_state["autonomy_select"] = detected["autonomy"][0]
            st.session_state["jurisdictions_select"] = detected["jurisdictions"][0]
            st.session_state["third_party_select"] = detected["third_party"][0]
            st.session_state["monitoring_select"] = detected["monitoring"][0]
            st.session_state["explainability_select"] = detected["explainability_method"][0]
            st.session_state["is_samd_checkbox"] = detected["is_samd"][0]
            st.session_state["affects_vulnerable_checkbox"] = detected["affects_vulnerable"][0]
            st.session_state["vulnerable_groups_select"] = detected["vulnerable_groups"][0]

    has_unresolved = False
    if "detected" in st.session_state:
        lines = summarize(st.session_state["detected"])
        has_unresolved = any(conf == "unresolved" for _, _, conf in lines)
        st.markdown("**What we understood:**")
        for label, value, conf in lines:
            st.markdown(f"{ICON[conf]} **{label}:** {value}")
        st.caption("🟡 = our best guess, ❓ = please tell us. Change anything below before running.")

    # Outside the form so changing it immediately swaps which functions/data
    # types/groups appear below — proof the app constructs a different
    # analysis per industry rather than relying on one hard-coded framework.
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

    # If the industry changed since the fields below were last populated
    # (either by a fresh prefill or a manual switch), drop the
    # industry-specific selections rather than risk handing a multiselect a
    # value that isn't in its new option list.
    if (st.session_state.get("_cfg_industry") or None) != (industry or None):
        for k in ("function_select", "data_types_select", "vulnerable_groups_select"):
            st.session_state.pop(k, None)
        st.session_state["_cfg_industry"] = industry

    cfg = get_industry_config(industry) if industry else GENERIC_CONFIG

    if industry and is_curated(industry):
        st.caption(f"✅ Using our in-depth question set for **{industry}**.")
    elif industry:
        st.caption(f"🌐 No specific question set for **{industry}** yet — using our general-purpose one instead.")
        with st.popover("What does that mean?"):
            st.write(
                "Every industry still gets scored with real, cited sources (NIST AI RMF, ISO/IEC 42001, "
                "the EU AI Act, and others that apply broadly) — it's just not as tailored as our "
                "Healthcare or HR question sets."
            )
    else:
        st.warning("Type an industry name above to continue.")

    with st.form("intake_form"):
        st.subheader("📝 Use case")
        name = st.text_input("Give it a short name*", placeholder="e.g. AI-Assisted Diabetic Retinopathy Screening")
        function = st.selectbox("What does it do?*", cfg["functions"], key="function_select")
        description = st.text_area(
            "Describe it in your own words*",
            placeholder="What does it do, who uses it, what data does it see, how autonomous is it...",
            height=120,
            key="description_input",
        )

        st.subheader("🗄️ Data & model")
        col1, col2 = st.columns(2)
        with col1:
            data_types = st.multiselect("What data does it use?*", cfg["data_types"], key="data_types_select")
            model_type = st.selectbox("What kind of AI is it?*", MODEL_TYPES, key="model_type_select")
            is_samd = st.checkbox(cfg["regulated_flag_label"], key="is_samd_checkbox")
        with col2:
            third_party = st.selectbox("Who built it?*", THIRD_PARTY_OPTIONS, key="third_party_select")
            explainability_method = st.selectbox("Can it explain its decisions?*", EXPLAINABILITY_OPTIONS, key="explainability_select")
            monitoring = st.selectbox("Is it checked after launch?*", MONITORING_OPTIONS, key="monitoring_select")

        st.subheader("⚖️ Decision context")
        col3, col4 = st.columns(2)
        with col3:
            autonomy = st.selectbox("Who makes the final call?*", AUTONOMY_OPTIONS, key="autonomy_select")
            jurisdictions = st.multiselect("Where is it used?*", JURISDICTIONS, key="jurisdictions_select")
        with col4:
            affects_vulnerable = st.checkbox("Could it affect a vulnerable group?", key="affects_vulnerable_checkbox")
            vulnerable_groups = st.multiselect("Which group(s)?", cfg["vulnerable_groups"], key="vulnerable_groups_select")

        submitted = st.form_submit_button("🚀 Run Assessment", type="primary")

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

    st.success(f"Assessment #{outcome['assessment_id']} saved.")
    render_simple_summary(use_case["name"], result["overall_score"], result["overall_level"], result["critical_flags"], result["dimensions"])
    st.write("")
    render_simple_dimension_grid(result["dimensions"])

    show_technical = st.checkbox("🔬 Show the full technical breakdown (exact scores, matched rules, cited sources, narrative)")
    if show_technical:
        render_overall_summary(result["overall_score"], result["overall_level"], result["critical_flags"])

        st.subheader("📐 Dimension-by-dimension breakdown, with citations")
        render_dimension_breakdown(result["dimensions"], source_lookup(conn))

        st.subheader("🔑 Which keywords in your description triggered a rule?")
        criteria = load_criteria_from_db(conn, resolve_rule_profile(use_case["industry"]))
        hits = matched_keywords(use_case["description"], criteria)
        if hits:
            for cid, kws in hits.items():
                st.write(f"`{cid}` matched on: {', '.join(kws)}")
        else:
            st.caption("No free-text keyword rules fired — all matches for this use case came from the structured fields.")

        st.subheader(f"🗣️ Narrative ({'Gemini-generated' if outcome['narrative_source'] == 'gemini' else 'template-generated, no LLM key configured'})")
        st.markdown(outcome["narrative"])
