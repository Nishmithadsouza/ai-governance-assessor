import json

import plotly.graph_objects as go
import streamlit as st

from src.bootstrap import init_app
from src.db import query
from src.options import SOURCE_TYPE_COLORS as TYPE_COLORS
from src.options import SOURCE_TYPES
from src.theme import hero, inject_css

st.set_page_config(page_title="Source Library", page_icon="📚", layout="wide")
conn, backend = init_app()
inject_css()

hero(
    "📚", "Source Library",
    "The full citation corpus behind the rule engine. The application deliberately distinguishes "
    "authority tiers — a law is not the same as a vendor blog post, even when they cover the same topic.",
)

rows = query(
    conn,
    "SELECT id, title, publisher, source_type, url, jurisdiction, published_date, retrieved_date, summary FROM sources ORDER BY source_type, published_date DESC",
)
sources = [
    dict(zip(["id", "title", "publisher", "source_type", "url", "jurisdiction", "published_date", "retrieved_date", "summary"], r))
    for r in rows
]

# Which industries actually cite each source, derived from the criteria table —
# a source isn't tagged with an industry itself, so a standard like NIST AI RMF
# correctly shows up as used by every industry whose rules cite it.
criteria_rows = query(conn, "SELECT industry, source_ids_json FROM criteria")
used_by = {}
for industry, source_ids_json in criteria_rows:
    for sid in json.loads(source_ids_json):
        used_by.setdefault(sid, set()).add(industry)

counts = {t: sum(1 for s in sources if s["source_type"] == t) for t in SOURCE_TYPES}
fig = go.Figure(
    go.Bar(
        x=SOURCE_TYPES,
        y=[counts[t] for t in SOURCE_TYPES],
        marker_color=[TYPE_COLORS[t] for t in SOURCE_TYPES],
        text=[counts[t] for t in SOURCE_TYPES],
        textposition="outside",
        hovertemplate="%{x}: %{y} source(s)<extra></extra>",
    )
)
fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), showlegend=False, yaxis_title="Sources")
st.plotly_chart(fig, use_container_width=True)

all_industries_cited = sorted({i for industries in used_by.values() for i in industries})

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    type_filter = st.multiselect("Source type", SOURCE_TYPES, default=SOURCE_TYPES)
with col2:
    industry_filter = st.multiselect("Used by industry", all_industries_cited, default=all_industries_cited)
with col3:
    search = st.text_input("Search title / publisher / summary", "")

filtered = [
    s for s in sources
    if s["source_type"] in type_filter
    and bool(used_by.get(s["id"], set()) & set(industry_filter))
    and (search.lower() in (s["title"] + s["publisher"] + s["summary"]).lower() if search else True)
]

st.caption(f"Showing {len(filtered)} of {len(sources)} sources.")

for s in filtered:
    badge = f'<span class="gov-badge" style="background:{TYPE_COLORS[s["source_type"]]};">{s["source_type"]}</span>'
    industries_str = ", ".join(sorted(used_by.get(s["id"], set()))) or "not currently cited by any rule"
    with st.expander(f"{s['source_type']} — {s['title']}"):
        st.markdown(f"{badge} &nbsp; **{s['publisher']}**", unsafe_allow_html=True)
        st.write(s["summary"])
        c1, c2, c3 = st.columns(3)
        c1.caption(f"Jurisdiction: {s['jurisdiction']}")
        c2.caption(f"Published: {s['published_date']}")
        c3.caption(f"Retrieved: {s['retrieved_date']}")
        st.caption(f"Used by: {industries_str}")
        st.markdown(f"[Open source]({s['url']})")
