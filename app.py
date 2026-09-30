"""Anveshak — SAT-SA. Router entry point: sets page config once and wires up
the site navigation; each page's content lives in views/."""

import streamlit as st

from ui_common import APP_TITLE, LOGO_ICON_PATH, inject_css

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=str(LOGO_ICON_PATH) if LOGO_ICON_PATH.exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

if LOGO_ICON_PATH.exists():
    st.logo(str(LOGO_ICON_PATH), size="large", icon_image=str(LOGO_ICON_PATH))

pages = [
    st.Page("views/overview.py", title="Overview", default=True),
    st.Page("views/entity_detail.py", title="Entity Detail"),
    st.Page("views/review_queue.py", title="Review Queue"),
    st.Page("views/trend_view.py", title="Trend View"),
    st.Page("views/methodology.py", title="Methodology"),
]

pg = st.navigation(pages, position="sidebar")
pg.run()
