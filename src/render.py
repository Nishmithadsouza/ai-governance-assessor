"""Shared rendering for an assessment result — used by both the New Assessment
page (fresh in-memory result) and the Assessment Detail page (result
reconstructed from the database), so both show identical output."""

import plotly.graph_objects as go
import streamlit as st

from src.options import LEVEL_COLORS, SOURCE_TYPE_COLORS, level_badge
from src.plain_language import plain_dimension, plain_level
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


def render_simple_summary(use_case_name, overall_score, overall_level, critical_flags, dimensions):
    """The default, non-technical view: one big plain-English verdict, no
    numbers or jargon required to understand it."""
    word, icon = {"Low": ("Low", "🟢"), "Medium": ("Medium", "🟡"), "High": ("High", "🟠"), "Critical": ("Critical", "🔴")}[overall_level]
    color = LEVEL_COLORS[overall_level]

    worst_dim = max(dimensions.items(), key=lambda kv: kv[1]["score"])[0]
    worst_icon, worst_label = plain_dimension(worst_dim)

    if critical_flags:
        flag_labels = ", ".join(plain_dimension(f)[1] for f in critical_flags)
        detail = f"It has at least one <b>critical</b> concern that needs attention: <b>{flag_labels}</b>."
    elif overall_level in ("Low",):
        detail = "No major concerns were found — this looks like a low-risk use case."
    else:
        detail = f"The biggest concern is <b>{worst_label.lower()}</b> ({worst_icon})."

    st.markdown(
        f"""<div class="gov-card" style="border-left:8px solid {color}; padding:1.2rem 1.4rem;">
                <div style="font-size:0.95rem; color:#52514e; font-weight:600; text-transform:uppercase; letter-spacing:0.03em;">Overall result for "{use_case_name}"</div>
                <div style="font-size:2.1rem; font-weight:800; margin:0.2rem 0;">{icon} {word} Risk</div>
                <div style="font-size:1rem;">{detail}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def render_simple_dimension_grid(dimensions):
    """3-column grid of plain-language cards — a glance, not a chart."""
    dims = list(dimensions.items())
    cols = st.columns(3)
    for i, (dim, data) in enumerate(dims):
        icon, label = plain_dimension(dim)
        word, level_icon = {"Low": "Good", "Medium": "Watch", "High": "Risk", "Critical": "Critical"}[data["level"]], \
            {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}[data["level"]]
        color = LEVEL_COLORS[data["level"]]
        with cols[i % 3]:
            st.markdown(
                f"""<div class="gov-card" style="text-align:center; border-top:4px solid {color}; margin-bottom:1rem;">
                        <div style="font-size:1.6rem;">{icon}</div>
                        <div style="font-weight:700; font-size:0.92rem; margin:0.15rem 0;">{label}</div>
                        <div style="font-size:0.95rem;">{level_icon} {word}</div>
                    </div>""",
                unsafe_allow_html=True,
            )


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
