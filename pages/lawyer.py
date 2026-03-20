"""
Lawyer detail page.

Shows all companies that a specific lawyer has appeared in SEC filings for,
within the selected date range. Clicking a company row navigates to company.py.
"""

import streamlit as st

from ui_components import (
    render_sidebar,
    render_breadcrumbs,
    apply_df_column_formats,
    add_to_targets,
    nav_to_company,
)
from search_modules.lawyer_search import search_lawyer_for_companies
from search_modules.cache import get_cached, set_cached

render_sidebar()
render_breadcrumbs()

lawyer_name: str = st.session_state.get("current_lawyer", "") or ""
search_start = st.session_state.get("search_start")
search_end = st.session_state.get("search_end")

if not lawyer_name:
    st.warning("No lawyer selected.")
    if st.button("← Back to Search"):
        st.switch_page("pages/search.py")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.title(f"👤  {lawyer_name}")
if search_start and search_end:
    st.caption(f"SEC filings · {search_start} → {search_end}")

# ── Load results (cache → SEC) ────────────────────────────────────────────────
mem_key = f"lawyer::{lawyer_name}::{search_start}::{search_end}"
result_df = st.session_state.get("results", {}).get(mem_key)

if result_df is None:
    result_df = get_cached("lawyer", lawyer_name, search_start, search_end)
    if result_df is not None:
        st.session_state["results"][mem_key] = result_df

if result_df is None:
    with st.spinner(f"Searching SEC filings for {lawyer_name}…"):
        progress_placeholder = st.empty()
        last_msg = {"text": ""}

        def _cb(msg: str):
            last_msg["text"] = msg
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

# ── Stats + bulk-add button ───────────────────────────────────────────────────
col_stat, col_add, col_dl = st.columns([4, 1.2, 1.2])
col_stat.success(f"Found **{len(result_df)}** companies")

if col_add.button("＋ Add all to Targets", use_container_width=True):
    added = 0
    for _, row in result_df.iterrows():
        ticker = str(row.get("Ticker", "")).replace(" US Equity", "").strip().upper()
        name = str(row.get("Company", ""))
        if add_to_targets(ticker, name):
            added += 1
    st.toast(f"Added {added} new companies to Targets")

csv = result_df.to_csv(index=False)
col_dl.download_button(
    "⬇ CSV",
    csv,
    file_name=f"{lawyer_name.lower().replace(' ', '_')}_companies.csv",
    mime="text/csv",
    use_container_width=True,
)

st.divider()

# ── Instructions ──────────────────────────────────────────────────────────────
st.caption("Click a row to open the company detail view.")

# ── Selectable results table ──────────────────────────────────────────────────
display_df, column_config = apply_df_column_formats(result_df)

event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config=column_config,
    key="lawyer_results_table",
)

# ── Handle row click → navigate to company page ───────────────────────────────
if event.selection.rows:
    idx = event.selection.rows[0]
    row = result_df.iloc[idx]
    ticker = str(row.get("Ticker", "")).replace(" US Equity", "").strip().upper()
    name = str(row.get("Company", ""))
    nav_to_company(ticker, name)
