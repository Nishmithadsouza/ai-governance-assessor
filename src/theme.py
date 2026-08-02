"""Shared visual design system for every page: one CSS injection, a small set
of reusable components (hero banner, colored stat tiles, nav cards, tier
badges). Colors are pulled from the same validated palette the Plotly charts
already use (src/options.py) so the whole app reads as one system rather than
each page picking its own colors.
"""

import streamlit as st

# Categorical accents (identity only — never used to encode risk/status,
# that's what LEVEL_COLORS is for). Same fixed order as the source-type chart.
ACCENTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]


def inject_css():
    st.markdown(
        """
        <style>
        .block-container { padding-top: 2rem; }

        .gov-hero {
            background: linear-gradient(120deg, #1c5cab 0%, #2a78d6 55%, #1baf7a 100%);
            color: #ffffff;
            padding: 1.75rem 2rem;
            border-radius: 14px;
            margin-bottom: 1.25rem;
            box-shadow: 0 4px 18px rgba(42, 120, 214, 0.25);
        }
        .gov-hero h1 {
            color: #ffffff;
            font-size: 2rem;
            margin: 0 0 0.35rem 0;
            font-weight: 800;
        }
        .gov-hero p {
            color: rgba(255,255,255,0.92);
            margin: 0;
            font-size: 1.02rem;
        }

        .gov-tile {
            border-radius: 12px;
            padding: 0.9rem 1.1rem;
            color: #ffffff;
            height: 100%;
        }
        .gov-tile .gov-tile-label {
            font-size: 0.8rem;
            font-weight: 600;
            opacity: 0.92;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }
        .gov-tile .gov-tile-value {
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.15;
        }

        .gov-card {
            border-radius: 12px;
            padding: 1rem 1.2rem;
            border: 1px solid rgba(11,11,11,0.08);
            background: #fcfcfb;
            margin-bottom: 0.6rem;
        }
        .gov-card.accent-left {
            border-left: 5px solid var(--gov-accent, #2a78d6);
        }

        .gov-badge {
            display: inline-block;
            padding: 0.15rem 0.65rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            color: #ffffff;
        }

        .gov-pill-row a[data-testid="stPageLink-NavLink"] {
            border-radius: 10px;
            border: 1px solid rgba(11,11,11,0.08) !important;
        }

        [data-testid="stMetric"] {
            background: #fcfcfb;
            border: 1px solid rgba(11,11,11,0.08);
            border-radius: 12px;
            padding: 0.75rem 1rem 0.5rem 1rem;
        }

        .stTabs [data-baseweb="tab"] { font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(icon, title, subtitle):
    st.markdown(
        f"""<div class="gov-hero"><h1>{icon} {title}</h1><p>{subtitle}</p></div>""",
        unsafe_allow_html=True,
    )


def stat_tiles(items):
    """items: list of (label, value, color) tuples. Rendered as an equal-width
    colored row — decorative categorical identity, not a risk/status signal."""
    cols = st.columns(len(items))
    for col, (label, value, color) in zip(cols, items):
        with col:
            st.markdown(
                f"""<div class="gov-tile" style="background:{color};">
                        <div class="gov-tile-label">{label}</div>
                        <div class="gov-tile-value">{value}</div>
                    </div>""",
                unsafe_allow_html=True,
            )


def nav_card(icon, title, description, page, color):
    with st.container(border=True):
        st.markdown(
            f"""<div style="border-left:5px solid {color}; padding-left:0.75rem; margin-bottom:0.4rem;">
                    <span style="font-size:1.15rem; font-weight:700;">{icon} {title}</span>
                </div>""",
            unsafe_allow_html=True,
        )
        st.caption(description)
        st.page_link(page, label=f"Open {title}", icon="➡️")


def tier_badge(tier_label, color):
    st.markdown(
        f'<span class="gov-badge" style="background:{color};">{tier_label}</span>',
        unsafe_allow_html=True,
    )
