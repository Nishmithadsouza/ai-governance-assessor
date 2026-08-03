"""Shared rendering for an assessment result — used by both the New Assessment
page (fresh in-memory result) and the Assessment Detail page (result
reconstructed from the database), so both show identical output."""

import plotly.graph_objects as go
import streamlit as st

from src.options import LEVEL_COLORS, SOURCE_TYPE_COLORS, level_badge
from src.scoring_engine import DIMENSIONS


def source_lookup(conn):
    from src.db import query

    rows = query(conn, "SELECT id, title, publisher, source_type, url, jurisdiction, published_date FROM sources")
    return {
        r[0]: {
            "title": r[1], "publisher": r[2], "source_type": r[3],
            "url": r[4], "jurisdiction": r[5], "published_date": r[6],
        }
        for r in rows
    }


def dimension_bar_chart(dimensions):
    scores = [dimensions[d]["score"] for d in DIMENSIONS]
    levels = [dimensions[d]["level"] for d in DIMENSIONS]
    colors = [LEVEL_COLORS[l] for l in levels]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=DIMENSIONS,
            orientation="h",
            marker_color=colors,
            text=[f"{s}/100 · {l}" for s, l in zip(scores, levels)],
            textposition="outside",
            hovertemplate="%{y}: %{x}/100<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis=dict(range=[0, 105], title="Risk score (0-100)"),
        yaxis=dict(autorange="reversed"),
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
    )
    return fig


def render_overall_summary(overall_score, overall_level, critical_flags):
    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric("Overall risk score", f"{overall_score}/100", label_visibility="visible")
        st.markdown(f"### {level_badge(overall_level)}")
    with c2:
        if critical_flags:
            st.error(
                "**Critical flags** (surfaced regardless of the overall average — a single critical "
                "dimension is never diluted away): " + ", ".join(critical_flags)
            )
        else:
            st.success("No dimension reached the Critical band.")


def render_dimension_breakdown(dimensions, sources_by_id):
    st.plotly_chart(dimension_bar_chart(dimensions), use_container_width=True)

    ranked = sorted(dimensions.items(), key=lambda kv: kv[1]["score"], reverse=True)
    for dim, data in ranked:
        with st.expander(f"{level_badge(data['level'])} — {dim} ({data['score']}/100)"):
            if not data["matches"]:
                st.caption("No criteria matched for this dimension.")
                continue
            for m in data["matches"]:
                weight = m.get("risk_weight")
                weight_str = f" ({'+' if weight and weight > 0 else ''}{weight})" if weight is not None else ""
                st.markdown(f"**[{m['id']}]{weight_str}** {m['rationale']}")
                for sid in m["source_ids"]:
                    src = sources_by_id.get(sid)
                    if src:
                        color = SOURCE_TYPE_COLORS.get(src["source_type"], "#898781")
                        st.markdown(
                            f'↳ <span class="gov-badge" style="background:{color};">{src["source_type"]}</span> '
                            f'[{src["title"]}]({src["url"]}) — {src["publisher"]} ({src["published_date"]})',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption(f"↳ source `{sid}` (not found in corpus)")
