"""
Stock Loan Availability page.

Fetches Interactive Brokers lending data joined with FMP reference.
Loaded data is stored in session state so the company detail page can
show per-ticker loan info without re-fetching.
"""

import streamlit as st

from ui_components import render_sidebar, set_current_page, apply_df_column_formats

set_current_page("pages/stocks.py", "Stock Loan")
render_sidebar()

st.title("Stock Loan Availability")
st.markdown("Real-time lending data from Interactive Brokers · US stocks (NYSE / NASDAQ)")

col_fetch, col_info = st.columns([1, 4])

with col_fetch:
    fetch_clicked = st.button("Fetch Latest Data", type="primary", use_container_width=True)

if fetch_clicked:
    with st.spinner("Fetching IB short-stock data..."):
        try:
            from search_modules.stock_loan import fetch_shortstock_with_market_cap
            df = fetch_shortstock_with_market_cap()
            st.session_state["stock_loan_results"] = {
                "df": df,
                "date": df["Date"].iloc[0] if "Date" in df.columns else "",
                "time": df["Time"].iloc[0] if "Time" in df.columns else "",
            }
            st.session_state["ib_data"] = df[
                [c for c in ["Symbol", "Rebate Rate (%)", "Fee Rate (%)", "Available"] if c in df.columns]
            ].copy()
        except Exception as exc:
            st.error(f"Error fetching data: {exc}")

stored = st.session_state.get("stock_loan_results")
if stored:
    result_df = stored["df"]
    data_date = stored.get("date", "")
    data_time = stored.get("time", "")

    with col_info:
        st.info(f"Data as of: {data_date} {data_time} · {len(result_df):,} stocks")

    # ── Filters ───────────────────────────────────────────────────────────────
    import pandas as pd
    filtered_df = result_df.copy()

    col_f1, col_f2, col_f3 = st.columns([1.5, 1.5, 3])
    with col_f1:
        min_mktcap_m = st.number_input(
            "Min Market Cap ($M)",
            min_value=0,
            value=0,
            step=50,
            key="stocks_min_mktcap",
        )
    with col_f2:
        max_fee = st.number_input(
            "Max Fee Rate (%)",
            min_value=0.0,
            value=999.0,
            step=1.0,
            format="%.1f",
            key="stocks_max_fee",
        )

    if "Market Cap" in filtered_df.columns and min_mktcap_m > 0:
        filtered_df = filtered_df[filtered_df["Market Cap"] >= min_mktcap_m * 1_000_000]
    if "Fee Rate (%)" in filtered_df.columns and max_fee < 999.0:
        filtered_df = filtered_df[filtered_df["Fee Rate (%)"] <= max_fee]

    st.caption(f"Showing {len(filtered_df):,} of {len(result_df):,} stocks · ETFs and funds excluded")

    display_df, column_config = apply_df_column_formats(filtered_df)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )

    csv = filtered_df.to_csv(index=False)
    st.download_button(
        "Download CSV",
        csv,
        file_name=f"stock_loan_{str(data_date).replace('/', '_')}.csv",
        mime="text/csv",
    )
