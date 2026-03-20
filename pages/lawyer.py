"""
Lawyer detail page.

Shows all companies where this lawyer appears in SEC filings.
Clicking a company row navigates to the company detail page.
"""

import streamlit as st

from ui_components import (
    render_sidebar,
    render_back_button,
    set_current_page,
    apply_df_column_formats,
    nav_to_company,
)
from search_modules.lawyer_search import search_lawyer_for_companies
from search_modules.cache import get_cached, set_cached

lawyer_name: str = st.session_state.get("current_lawyer", "") or ""
set_current_page("pages/lawyer.py", lawyer_name)
render_sidebar()
render_back_button()

search_start = st.session_state.get("search_start")
search_end = st.session_state.get("search_end")

if not lawyer_name:
    st.warning("No lawyer selected.")
    if st.button("Back to Search"):
        st.switch_page("pages/search.py")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.title(lawyer_name)
if search_start and search_end:
    st.caption(f"SEC filings · {search_start} to {search_end}")

# ── Load results (memory cache -> SQLite -> SEC) ──────────────────────────────
mem_key = f"lawyer::{lawyer_name}::{search_start}::{search_end}"
result_df = st.session_state.get("results", {}).get(mem_key)

if result_df is None:
    result_df = get_cached("lawyer", lawyer_name, search_start, search_end)
    if result_df is not None:
        st.session_state["results"][mem_key] = result_df

if result_df is None:
    with st.spinner(f"Searching SEC filings for {lawyer_name}..."):
        progress_placeholder = st.empty()

        def _cb(msg: str):
            progress_placeholder.info(msg)

        try:
            result_df = search_lawyer_for_companies(
                lawyer_name, search_start, search_end, _cb
            )
            progress_placeholder.empty()
            set_cached("lawyer", lawyer_name, search_start, search_end, result_df)
            if "results" not in st.session_state:
                st.session_state["results"] = {}
            st.session_state["results"][mem_key] = result_df
        except Exception as exc:
            progress_placeholder.empty()
            st.error(f"Search failed: {exc}")
            st.stop()

# ── Stats + actions ───────────────────────────────────────────────────────────
col_stat, col_dl = st.columns([5, 1.2])
col_stat.success(f"Found {len(result_df)} companies")

csv = result_df.to_csv(index=False)
col_dl.download_button(
    "Download CSV",
    csv,
    file_name=f"{lawyer_name.lower().replace(' ', '_')}_companies.csv",
    mime="text/csv",
    use_container_width=True,
)

st.divider()

# ── Results list with View buttons ────────────────────────────────────────────
for i, row in result_df.iterrows():
    ticker = str(row.get("Ticker", "")).replace(" US Equity", "").strip().upper()
    name = str(row.get("Company", ""))

    col_name, col_btn = st.columns([4, 0.8])
    col_name.markdown(f"**{name}** &nbsp; `{ticker}`" if ticker else f"**{name}**")
    if col_btn.button("View →", key=f"view_lawyer_{i}", use_container_width=True):
        nav_to_company(ticker, name)
