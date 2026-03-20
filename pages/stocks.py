"""
Stock Loan Availability page.

Fetches real-time Interactive Brokers lending data and joins with FMP reference.
Loaded data is stored in session state so other pages (company detail) can
show per-ticker loan info without re-fetching.
"""

import streamlit as st

from ui_components import render_sidebar, apply_df_column_formats

render_sidebar()

st.title("📈  Stock Loan Availability")
st.markdown(
    "Real-time lending data from Interactive Brokers · US stocks (NYSE / NASDAQ only)"
)

col_fetch, col_info = st.columns([1, 4])

with col_fetch:
    fetch_clicked = st.button("Fetch Latest Data", type="primary", use_container_width=True)

if fetch_clicked:
    with st.spinner("Fetching IB short-stock data and enriching with FMP…"):
        try:
            from search_modules.stock_loan import fetch_shortstock_with_market_cap
            df = fetch_shortstock_with_market_cap()
            st.session_state["stock_loan_results"] = {
                "df": df,
                "date": df["Date"].iloc[0] if "Date" in df.columns else "",
                "time": df["Time"].iloc[0] if "Time" in df.columns else "",
            }
            # Also store raw IB keyed by Symbol for use in company detail page
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
        st.info(f"Data as of: **{data_date} {data_time}** · {len(result_df):,} stocks")

    display_df, column_config = apply_df_column_formats(result_df)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )

    csv = result_df.to_csv(index=False)
    st.download_button(
        "⬇ Download CSV",
        csv,
        file_name=f"stock_loan_{str(data_date).replace('/', '_')}.csv",
        mime="text/csv",
    )
