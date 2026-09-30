"""Shared UI constants and helpers used across every page: brand palette,
CSS injection, and data loading."""

import base64
from pathlib import Path

import pandas as pd
import streamlit as st

from analytics.engine import build_analytics
from analytics.db import DB_PATH

APP_TITLE = "Anveshak"
APP_SUBTITLE = "See what the reports don't show."

ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_ICON_PATH = ASSETS_DIR / "logo_icon.png"


@st.cache_data(show_spinner=False)
def _logo_icon_data_uri() -> str:
    if not LOGO_ICON_PATH.exists():
        return ""
    b64 = base64.b64encode(LOGO_ICON_PATH.read_bytes()).decode()
    return f"data:image/png;base64,{b64}"

# Brand palette
NAVY_900 = "#071739"
SLATE_700 = "#4B6382"
BLUEGRAY_400 = "#A4B5C4"
PALE_200 = "#CDD5DB"
TAN_600 = "#A68868"
CREAM_200 = "#E3C39D"
WHITE = "#FFFFFF"
CREAM_BG = "#F7F2EA"
INK = "#12213D"
SIDEBAR_TEXT = "#D7DEE6"
SIDEBAR_TEXT_MUTED = "#93A2B5"

# Severity / risk-band colors stay semantic (red/amber/green) — a supervisory
# risk tool loses its at-a-glance clarity if "critical" and "clean" share a hue.
BAND_COLORS = {"Severe": "#C4324D", "Moderate": "#D98E2B", "Clean": "#2E9E6B"}
SEVERITY_COLORS = {"critical": "#C4324D", "high": "#E07A3F", "medium": "#D98E2B", "low": "#5FA36B"}

# Brand-palette chart colors for non-severity dimensions
SECTOR_COLORS = {"Power": NAVY_900, "Banking": SLATE_700, "Telecom": TAN_600}
CATEGORY_LABELS = {"execution_gap": "Execution Gap", "negative_space": "Negative Space",
                    "audit_supervision": "Audit Supervision"}
CATEGORY_COLORS = {"execution_gap": NAVY_900, "negative_space": SLATE_700, "audit_supervision": TAN_600}

PLOTLY_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor=WHITE,
    plot_bgcolor=WHITE,
    font=dict(color=INK, family="Inter, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"),
    colorway=[NAVY_900, SLATE_700, TAN_600, BLUEGRAY_400],
)


def load_data():
    if not Path(DB_PATH).exists():
        with st.spinner("First run: generating the synthetic demo dataset..."):
            import data_generator
            data_generator.build_database()
            data_generator.write_issue_seed_sheet()
    return build_analytics(str(DB_PATH))


def apply_chart_theme(fig):
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_xaxes(gridcolor=PALE_200, zerolinecolor=BLUEGRAY_400)
    fig.update_yaxes(gridcolor=PALE_200, zerolinecolor=BLUEGRAY_400)
    return fig


def inject_css():
    st.markdown(f"""
    <style>
    html, body, [class*="css"] {{
        font-family: Inter, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }}
    .stApp {{
        background: {CREAM_BG};
    }}
    [data-testid="stHeader"] {{
        background: transparent;
        height: 2.5rem;
    }}
    [data-testid="stMain"] .block-container {{
        padding-top: 1.5rem;
    }}

    /* ---- Sidebar: dark navy panel, all text forced to a light color ---- */
    [data-testid="stSidebar"] {{
        background: {NAVY_900};
    }}
    [data-testid="stSidebar"] * {{
        color: {SIDEBAR_TEXT};
    }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: {WHITE} !important;
    }}
    [data-testid="stSidebar"] hr {{
        border-color: {SLATE_700};
    }}
    [data-testid="stSidebarNav"] a {{
        border-radius: 8px;
        margin: 2px 8px;
        color: {SIDEBAR_TEXT} !important;
    }}
    [data-testid="stSidebarNav"] a * {{
        color: {SIDEBAR_TEXT} !important;
        font-weight: 500;
    }}
    [data-testid="stSidebarNav"] a:hover {{
        background: {SLATE_700}66;
    }}
    [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background: {TAN_600};
    }}
    [data-testid="stSidebarNav"] a[aria-current="page"] * {{
        color: {NAVY_900} !important;
        font-weight: 700;
    }}
    /* radio / multiselect / selectbox controls inside the dark sidebar */
    [data-testid="stSidebar"] [data-baseweb="select"] > div {{
        background: {SLATE_700}55;
        border-color: {SLATE_700};
    }}
    [data-testid="stSidebar"] [data-baseweb="tag"] {{
        background: {TAN_600} !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="tag"] * {{
        color: {NAVY_900} !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] label {{
        background: {SLATE_700}33;
        border-radius: 8px;
        padding: 6px 8px;
        margin-bottom: 4px;
    }}
    [data-testid="stSidebar"] input {{
        color: {INK} !important;
    }}

    /* ---- Header banner ---- */
    .anv-header {{
        background: linear-gradient(135deg, {NAVY_900} 0%, {SLATE_700} 100%);
        color: {WHITE};
        padding: 24px 36px;
        border-radius: 14px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 20px;
    }}
    .anv-header img {{
        height: 64px;
        width: 64px;
        flex-shrink: 0;
    }}
    .anv-header h1 {{
        color: {WHITE};
        margin: 0 0 4px 0;
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }}
    .anv-header p {{
        color: {PALE_200};
        margin: 0;
        font-size: 0.95rem;
        opacity: 0.95;
    }}

    /* ---- Cards / metrics on the light main area ---- */
    .anv-card {{
        background: {WHITE};
        border: 1px solid {PALE_200};
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(7,23,57,0.06);
    }}
    [data-testid="stMetric"] {{
        background: {WHITE};
        border: 1px solid {PALE_200};
        border-left: 3px solid {TAN_600};
        border-radius: 12px;
        padding: 14px 16px 10px 16px;
        box-shadow: 0 1px 3px rgba(7,23,57,0.06);
    }}
    [data-testid="stMetricLabel"] {{
        color: {SLATE_700};
    }}
    [data-testid="stMetricValue"] {{
        color: {NAVY_900};
    }}
    h1, h2, h3 {{
        color: {NAVY_900};
        letter-spacing: -0.01em;
    }}
    .stButton > button, .stDownloadButton > button {{
        background: {NAVY_900};
        color: {WHITE};
        border-radius: 8px;
        border: none;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        background: {SLATE_700};
        color: {WHITE};
    }}
    [data-testid="stDataFrame"] {{
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid {PALE_200};
    }}
    div[data-testid="stExpander"] {{
        background: {WHITE};
        border: 1px solid {PALE_200};
        border-radius: 10px;
    }}
    hr {{
        border-color: {PALE_200};
    }}
    </style>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    logo_uri = _logo_icon_data_uri()
    img_html = f'<img src="{logo_uri}" alt="" />' if logo_uri else ""
    st.markdown(f"""
    <div class="anv-header">
        {img_html}
        <div>
            <h1>{title}</h1>
            {sub_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def severity_badge(sev: str) -> str:
    color = SEVERITY_COLORS.get(sev, "#6B7280")
    return f"<span style='background:{color}1A;color:{color};border:1px solid {color};" \
           f"border-radius:4px;padding:1px 8px;font-size:0.8em;font-weight:600'>{sev.upper()}</span>"


def band_badge(band: str) -> str:
    color = BAND_COLORS.get(band, "#6B7280")
    return f"<span style='background:{color}1A;color:{color};border:1px solid {color};" \
           f"border-radius:4px;padding:2px 10px;font-size:0.85em;font-weight:700'>{band.upper()}</span>"


def evidence_table(tables: dict, evidence_type: str, evidence_ids) -> pd.DataFrame:
    """Look up raw records for a list of evidence IDs, for drill-down display."""
    ids = list(evidence_ids)
    if not ids:
        return pd.DataFrame()
    key_map = {
        "alert": ("alerts", "alert_id"),
        "case": ("cases", "case_id"),
        "audit": ("audit_logs", "audit_id"),
        "asset": ("assets", "asset_id"),
    }
    table_name, key = key_map.get(evidence_type, (None, None))
    if table_name is None:
        return pd.DataFrame()
    df = tables[table_name]
    return df[df[key].isin(ids)].reset_index(drop=True)


def rule_catalog_markdown() -> str:
    from analytics.detectors import RULE_WEIGHTS
    lines = ["| Rule | Category | Base pts | Saturates at | Fires above |",
             "|---|---|---|---|---|"]
    cat_map = {"EG": "Execution Gap", "NS": "Negative Space", "AS": "Audit Supervision"}
    for code, w in RULE_WEIGHTS.items():
        cat = cat_map.get(code[:2], "")
        lines.append(f"| {code} | {cat} | {w['base']} | {w['saturation']:.0%} | {w['floor']:.0%} |")
    return "\n".join(lines)
