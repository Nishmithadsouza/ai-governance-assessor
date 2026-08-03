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
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .gov-card.accent-left {
            border-left: 5px solid var(--gov-accent, #2a78d6);
        }
        .gov-card.hoverable:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 20px rgba(11,11,11,0.12);
        }

        .gov-navcard {
            border-radius: 14px;
            padding: 1.1rem 1.3rem 0.9rem 1.3rem;
            border: 1px solid rgba(11,11,11,0.08);
            border-top: 5px solid var(--gov-accent, #2a78d6);
            background: #fcfcfb;
            margin-bottom: 1rem;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .gov-navcard:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 24px rgba(11,11,11,0.14);
        }
        .gov-navcard .gov-navcard-title { font-size: 1.15rem; font-weight: 800; margin-bottom: 0.3rem; }
        .gov-navcard .gov-navcard-desc { color: #52514e; font-size: 0.9rem; margin-bottom: 0.5rem; }

        .st-key-home_cta a[data-testid="stPageLink-NavLink"] {
            background: linear-gradient(120deg, #2a78d6, #1baf7a) !important;
            color: #ffffff !important;
            border-radius: 12px !important;
            border: none !important;
            padding: 0.9rem 1.4rem !important;
            font-weight: 800 !important;
            font-size: 1.1rem !important;
            box-shadow: 0 6px 18px rgba(42,120,214,0.35);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .st-key-home_cta a[data-testid="stPageLink-NavLink"]:hover {
            transform: translateY(-2px) scale(1.01);
            box-shadow: 0 10px 24px rgba(42,120,214,0.45);
        }
        .st-key-home_cta a[data-testid="stPageLink-NavLink"] p { color: #ffffff !important; font-weight: 800 !important; }
        .st-key-home_cta a[data-testid="stPageLink-NavLink"] span[data-testid="stIconEmoji"] { filter: brightness(10); }

        .gov-chip {
            border-radius: 12px;
            padding: 0.8rem 0.5rem;
            text-align: center;
            color: #ffffff;
            font-weight: 700;
            font-size: 0.85rem;
            height: 100%;
            transition: transform 0.15s ease;
        }
        .gov-chip:hover { transform: translateY(-3px); }
        .gov-chip .gov-chip-icon { font-size: 1.5rem; display: block; margin-bottom: 0.25rem; }

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
    st.markdown(
        f"""<div class="gov-navcard" style="--gov-accent:{color};">
                <div class="gov-navcard-title">{icon} {title}</div>
                <div class="gov-navcard-desc">{description}</div>
            </div>""",
        unsafe_allow_html=True,
    )
    st.page_link(page, label=f"Open {title}", icon="➡️")


def big_cta(label, page, icon="🚀"):
    with st.container(key="home_cta"):
        st.page_link(page, label=label, icon=icon)


def dimension_showcase(dimensions_plain):
    """items: list of (icon, label) tuples — a colorful, informational grid
    (identity/decoration only, no data encoded) introducing what gets checked."""
    cols = st.columns(3)
    for i, (icon, label) in enumerate(dimensions_plain):
        color = ACCENTS[i % len(ACCENTS)]
        with cols[i % 3]:
            st.markdown(
                f"""<div class="gov-chip" style="background:{color};">
                        <span class="gov-chip-icon">{icon}</span>{label}
                    </div>""",
                unsafe_allow_html=True,
            )
            st.write("")


def tier_badge(tier_label, color):
    st.markdown(
        f'<span class="gov-badge" style="background:{color};">{tier_label}</span>',
        unsafe_allow_html=True,
    )
