"""
Law Firm detail page.

Shows companies represented by this firm in SEC filings.
Clicking a row in the results table navigates to the company detail page.
"""

import streamlit as st

from ui_components import (
    render_sidebar,
    render_back_button,
    set_current_page,
    fmt_currency,
    nav_to_company,
)
from search_modules.law_firm_search import search_law_firm_for_companies
from search_modules.cache import get_cached, set_cached

firm_name: str = st.session_state.get("current_firm", "") or ""
set_current_page("pages/firm.py", firm_name)
render_sidebar()
render_back_button()

search_start = st.session_state.get("search_start")
search_end = st.session_state.get("search_end")

if not firm_name:
    st.warning("No law firm selected.")
    if st.button("Back to Search"):
        st.switch_page("pages/search.py")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.title(firm_name)
if search_start and search_end:
    st.caption(f"SEC filings · {search_start} to {search_end}")

# ── Load results ──────────────────────────────────────────────────────────────
mem_key = f"firm::{firm_name}::{search_start}::{search_end}"
result_df = st.session_state.get("results", {}).get(mem_key)

if result_df is None:
    result_df = get_cached("firm", firm_name, search_start, search_end)
    if result_df is not None:
        st.session_state["results"][mem_key] = result_df

if result_df is None:
    with st.spinner(f"Searching SEC filings for {firm_name}..."):
        prog = st.empty()

        def _cb(msg: str):
            prog.info(msg)

        try:
            result_df = search_law_firm_for_companies(
                firm_name,
                search_start,
                search_end,
                _cb,
                include_lawyers=False,
            )
            prog.empty()
            set_cached("firm", firm_name, search_start, search_end, result_df)
            if "results" not in st.session_state:
                st.session_state["results"] = {}
            st.session_state["results"][mem_key] = result_df
        except Exception as exc:
            prog.empty()
            st.error(f"Search failed: {exc}")
            st.stop()

# ── Stats + actions ───────────────────────────────────────────────────────────
col_stat, col_dl = st.columns([5, 1.2])
col_stat.success(f"Found {len(result_df)} companies")

csv = result_df.to_csv(index=False)
col_dl.download_button(
    "Download CSV",
    csv,
    file_name=f"{firm_name.lower().replace(' ', '_').replace('&', 'and')}_companies.csv",
    mime="text/csv",
    use_container_width=True,
)

st.divider()

# ── Results table ─────────────────────────────────────────────────────────────
COL = [3.5, 1, 1, 1.2, 0.7]

h1, h2, h3, h4, h5 = st.columns(COL)
h1.markdown("**Company**")
h2.markdown("**Ticker**")
h3.markdown("**Exchange**")
h4.markdown("**Mkt Cap**")

st.markdown(
    '<hr style="margin:4px 0 8px 0; border:none; border-top:2px solid rgba(49,51,63,0.2);">',
    unsafe_allow_html=True,
)

for i, row in result_df.iterrows():
    ticker = str(row.get("Ticker", "")).replace(" US Equity", "").strip().upper()
    name = str(row.get("Company", ""))
    exchange = str(row.get("Exchange", "") or "")
    mktcap = row.get("Market Cap")

    c1, c2, c3, c4, c5 = st.columns(COL)
    c1.markdown(name)
    c2.markdown(f"`{ticker}`" if ticker else "")
    c3.markdown(exchange)
    c4.markdown(fmt_currency(mktcap))
    if c5.button("View", key=f"view_firm_{i}", use_container_width=True):
        nav_to_company(ticker, name)

    st.markdown(
        '<hr style="margin:2px 0; border:none; border-top:1px solid rgba(49,51,63,0.08);">',
        unsafe_allow_html=True,
    )
