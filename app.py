import streamlit as st

st.set_page_config(
    page_title="EquityIntel",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global session-state defaults ────────────────────────────────────────────
_defaults = {
    "back_page": None,        # {page, label, prev_back} — drives the Back button
    "_this_page": "pages/search.py",
    "_this_label": "Search",
    "targets": [],            # list of {ticker, name}
    "results": {},            # in-memory result cache keyed by search string
    "current_lawyer": None,
    "current_company": None,
    "current_firm": None,
    "search_start": None,
    "search_end": None,
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Multi-page navigation ─────────────────────────────────────────────────────
pg = st.navigation(
    [
        st.Page("pages/search.py",  title="Search",   url_path="search"),
        st.Page("pages/lawyer.py",  title="Lawyer",   url_path="lawyer"),
        st.Page("pages/company.py", title="Company",  url_path="company"),
        st.Page("pages/firm.py",    title="Law Firm", url_path="firm"),
        st.Page("pages/targets.py", title="Targets",  url_path="targets"),
        st.Page("pages/stocks.py",  title="Stocks",   url_path="stocks"),
    ],
    position="hidden",
)
pg.run()
