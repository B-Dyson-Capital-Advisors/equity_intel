"""
Targets page — saved investment target pipeline.
"""

import streamlit as st
import pandas as pd

from ui_components import (
    render_sidebar,
    set_current_page,
    apply_df_column_formats,
    nav_to_company,
)
from search_modules.stock_reference import load_stock_reference

set_current_page("pages/targets.py", "Targets")
render_sidebar()

st.title("Target Pipeline")

targets: list[dict] = st.session_state.get("targets", [])

if not targets:
    st.info(
        "No targets yet. Browse lawyers, companies, or law firms and click "
        "'Add to Targets' on any result."
    )
    if st.button("Go to Search"):
        st.switch_page("pages/search.py")
    st.stop()

# ── Enrich with FMP data ──────────────────────────────────────────────────────
ref_df = load_stock_reference()
rows = []
for t in targets:
    ticker = t.get("ticker", "")
    name = t.get("name", "")
    row: dict = {"Ticker": ticker, "Company": name}

    if ref_df is not None and ticker:
        match = ref_df[ref_df["Symbol"] == ticker]
        if not match.empty:
            fmp = match.iloc[0].to_dict()
            row["Exchange"] = fmp.get("Exchange", "")
            row["Price"] = fmp.get("Price")
            row["Market Cap"] = fmp.get("Market Cap")
            row["Enterprise Value"] = fmp.get("Enterprise Value")
            row["CEO"] = fmp.get("CEO", "")
            row["Sector"] = fmp.get("Sector", "")
            row["Industry"] = fmp.get("Industry", "")

    ib_data = st.session_state.get("ib_data")
    if ib_data is not None and ticker:
        match_ib = ib_data[ib_data["Symbol"].str.upper() == ticker.upper()]
        if not match_ib.empty:
            ib_row = match_ib.iloc[0]
            row["Rebate Rate (%)"] = ib_row.get("Rebate Rate (%)")
            row["Fee Rate (%)"] = ib_row.get("Fee Rate (%)")
            row["Available"] = ib_row.get("Available")

    rows.append(row)

target_df = pd.DataFrame(rows)

# ── Actions ───────────────────────────────────────────────────────────────────
col_count, col_clear, col_dl = st.columns([3, 1, 1])
col_count.metric("Companies in pipeline", len(targets))

if col_clear.button("Clear all", use_container_width=True):
    st.session_state.targets = []
    st.rerun()

csv = target_df.to_csv(index=False)
col_dl.download_button(
    "Export CSV",
    csv,
    file_name="equity_intel_targets.csv",
    mime="text/csv",
    use_container_width=True,
)

st.divider()
st.caption("Click a row to open the company detail view.")

display_df, column_config = apply_df_column_formats(target_df)

event = st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    column_config=column_config,
    key="targets_table",
)

if event.selection.rows:
    idx = event.selection.rows[0]
    row = target_df.iloc[idx]
    ticker = str(row.get("Ticker", "")).strip().upper()
    name = str(row.get("Company", ""))
    nav_to_company(ticker, name)

st.divider()
st.markdown("**Remove companies:**")
for i, t in enumerate(list(targets)):
    c1, c2 = st.columns([5, 1])
    c1.write(f"{t.get('name', '')} ({t.get('ticker', '')})")
    if c2.button("Remove", key=f"remove_{i}_{t.get('ticker', i)}", use_container_width=True):
        st.session_state.targets = [
            x for x in st.session_state.targets if x.get("ticker") != t.get("ticker")
        ]
        st.rerun()
