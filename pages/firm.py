"""
Law Firm detail page.

Shows all companies that a specific law firm has appeared in SEC filings for.
Clicking a company row navigates to company.py.
"""

import streamlit as st

from ui_components import (
    render_sidebar,
    render_breadcrumbs,
    apply_df_column_formats,
    add_to_targets,
    nav_to_company,
)
from search_modules.law_firm_search import search_law_firm_for_companies
from search_modules.cache import get_cached, set_cached

render_sidebar()
render_breadcrumbs()

firm_name: str = st.session_state.get("current_firm", "") or ""
search_start = st.session_state.get("search_start")
search_end = st.session_state.get("search_end")

if not firm_name:
    st.warning("No law firm selected.")
    if st.button("← Back to Search"):
        st.switch_page("pages/search.py")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.title(f"⚖️  {firm_name}")
if search_start and search_end:
    st.caption(f"SEC filings · {search_start} → {search_end}")

# ── Load results ──────────────────────────────────────────────────────────────
mem_key = f"firm::{firm_name}::{search_start}::{search_end}"
result_df = st.session_state.get("results", {}).get(mem_key)

if result_df is None:
    result_df = get_cached("firm", firm_name, search_start, search_end)
    if result_df is not None:
        st.session_state["results"][mem_key] = result_df

if result_df is None:
    with st.spinner(f"Searching SEC filings for {firm_name}…"):
        prog = st.empty()

        def _cb(msg: str):
            prog.info(msg)

        try:
            result_df = search_law_firm_for_companies(
                firm_name,
                search_start,
                search_end,
                _cb,
                include_lawyers=False,  # fast mode — lawyers available per-company
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
col_stat, col_add, col_dl = st.columns([4, 1.2, 1.2])
col_stat.success(f"Found **{len(result_df)}** companies")

if col_add.button("＋ Add all to Targets", use_container_width=True):
    added = 0
    for _, row in result_df.iterrows():
        t = str(row.get("Ticker", "")).replace(" US Equity", "").strip().upper()
        n = str(row.get("Company", ""))
        if add_to_targets(t, n):
            added += 1
    st.toast(f"Added {added} new companies to Targets")

csv = result_df.to_csv(index=False)
col_dl.download_button(
    "⬇ CSV",
    csv,
    file_name=f"{firm_name.lower().replace(' ', '_').replace('&', 'and')}_companies.csv",
    mime="text/csv",
    use_container_width=True,
)

st.divider()
st.caption("Click a row to open the company detail view (financials + legal counsel).")

# ── Selectable table ──────────────────────────────────────────────────────────
display_df, column_config = apply_df_column_formats(result_df)

event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config=column_config,
    key="firm_results_table",
)

if event.selection.rows:
    idx = event.selection.rows[0]
    row = result_df.iloc[idx]
    ticker = str(row.get("Ticker", "")).replace(" US Equity", "").strip().upper()
    name = str(row.get("Company", ""))
    nav_to_company(ticker, name)
