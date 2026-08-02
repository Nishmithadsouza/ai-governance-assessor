import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.assessment_service import list_assessments
from src.bootstrap import init_app
from src.db import query
from src.options import INDUSTRIES, LEVEL_COLORS, level_badge
from src.scoring_engine import DIMENSIONS, score_to_level
from src.theme import ACCENTS, hero, inject_css, stat_tiles

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
conn, backend = init_app()
inject_css()

hero(
    "📊", "Dashboard",
    "Every assessment ever run is persisted here — this view proves the app processes and "
    "retains many cases, not one hard-coded demo.",
)

assessments = list_assessments(conn)

if not assessments:
    st.info("No assessments yet. Run one from the New Assessment page.")
    st.stop()

df = pd.DataFrame(assessments)
# Curated industries first, then everything else (presets or freely typed
# names) actually present in the data, alphabetically.
present = set(df["industry"].unique())
industries_present = [i for i in INDUSTRIES if i in present] + sorted(present - set(INDUSTRIES))

col_f1, col_f2 = st.columns(2)
with col_f1:
    industry_filter = st.multiselect("Filter by industry", industries_present, default=industries_present)
with col_f2:
    level_filter = st.multiselect("Filter by overall risk level", ["Low", "Medium", "High", "Critical"], default=["Low", "Medium", "High", "Critical"])

df_view = df[df["overall_level"].isin(level_filter) & df["industry"].isin(industry_filter)]

stat_tiles(
    [
        ("Total assessments", len(df), ACCENTS[0]),
        ("Shown after filter", len(df_view), ACCENTS[1]),
        ("Critical-flag assessments (filtered)", int((df_view["critical_flags"].str.len() > 0).sum()), LEVEL_COLORS["Critical"]),
    ]
)

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🚦 Risk-level distribution")
    counts = df_view["overall_level"].value_counts().reindex(["Low", "Medium", "High", "Critical"]).fillna(0)
    fig = go.Figure(
        go.Bar(
            x=counts.index,
            y=counts.values,
            marker_color=[LEVEL_COLORS[l] for l in counts.index],
            text=counts.values.astype(int),
            textposition="outside",
            hovertemplate="%{x}: %{y} assessment(s)<extra></extra>",
        )
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="Assessments", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    label = industry_filter[0] if len(industry_filter) == 1 else f"{len(industry_filter)} industries"
    st.subheader(f"📐 Average score by dimension ({label})")
    dim_rows = query(
        conn,
        """SELECT ad.dimension, ad.score, u.industry
           FROM assessment_dimensions ad
           JOIN assessments a ON a.id = ad.assessment_id
           JOIN use_cases u ON u.id = a.use_case_id""",
    )
    dim_df = pd.DataFrame(dim_rows, columns=["dimension", "score", "industry"])
    dim_df = dim_df[dim_df["industry"].isin(industry_filter)]
    avg_by_dim = dim_df.groupby("dimension")["score"].mean().to_dict()
    scores = [round(avg_by_dim.get(d, 0), 1) for d in DIMENSIONS]
    levels = [score_to_level(s) for s in scores]
    fig2 = go.Figure(
        go.Bar(
            x=scores,
            y=DIMENSIONS,
            orientation="h",
            marker_color=[LEVEL_COLORS[l] for l in levels],
            text=[f"{s}/100" for s in scores],
            textposition="outside",
            hovertemplate="%{y}: %{x}/100 avg<extra></extra>",
        )
    )
    fig2.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(range=[0, 105], title="Average score"), yaxis=dict(autorange="reversed"), showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.subheader("🗂️ All assessments")
display_df = df_view.copy()
display_df["overall_level"] = display_df["overall_level"].apply(level_badge)
display_df["critical_flags"] = display_df["critical_flags"].apply(lambda fl: ", ".join(fl) if fl else "—")
display_df = display_df[["assessment_id", "created_at", "industry", "use_case_name", "function", "overall_score", "overall_level", "critical_flags", "narrative_source"]]
display_df.columns = ["ID", "Created", "Industry", "Use Case", "Function", "Score", "Level", "Critical Flags", "Narrative"]
st.dataframe(display_df, use_container_width=True, hide_index=True)
st.caption("Open any row's ID in the Assessment Detail page to see its full, cited breakdown.")
