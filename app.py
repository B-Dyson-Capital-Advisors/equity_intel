import streamlit as st

st.set_page_config(
    page_title="EquityIntel",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global session-state defaults ────────────────────────────────────────────
_defaults = {
    "nav_stack": [{"page": "pages/search.py", "label": "Search"}],
    "targets": [],          # list of {ticker, name}
    "results": {},          # in-memory result cache keyed by search string
    # Current entity being viewed
    "current_lawyer": None,   # str
    "current_company": None,  # dict {ticker, name, cik, display}
    "current_firm": None,     # str
    # Date range shared across pages
    "search_start": None,
    "search_end": None,
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Multi-page navigation ─────────────────────────────────────────────────────
pg = st.navigation(
    [
        st.Page("pages/search.py",  title="Search",   icon="🔍", url_path="search"),
        st.Page("pages/lawyer.py",  title="Lawyer",   icon="👤", url_path="lawyer"),
        st.Page("pages/company.py", title="Company",  icon="🏢", url_path="company"),
        st.Page("pages/firm.py",    title="Law Firm", icon="⚖️",  url_path="firm"),
        st.Page("pages/targets.py", title="Targets",  icon="🎯", url_path="targets"),
        st.Page("pages/stocks.py",  title="Stocks",   icon="📈", url_path="stocks"),
    ],
    position="hidden",   # we render our own sidebar nav in ui_components
)
pg.run()
