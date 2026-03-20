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

    slider_cols = st.columns(3)

    # ── Fee Rate slider ────────────────────────────────────────────────────
    _fee_breaks = {
        "0.1%": 0.1,  "0.25%": 0.25, "0.5%": 0.5,
        "1%": 1,      "5%": 5,        "10%": 10,
        "25%": 25,    "50%": 50,      "100%": 100,
        "250%": 250,  "500%": 500,    "1,000%+": 9_999,
    }
    _fee_labels = list(_fee_breaks.keys())
    with slider_cols[0]:
        fee_lo, fee_hi = st.select_slider(
            "Fee Rate (%)",
            options=_fee_labels,
            value=("0.1%", "1,000%+"),
            key="stocks_fee_range",
        )
    fee_lo_v = _fee_breaks[fee_lo]
    fee_hi_v = _fee_breaks[fee_hi]
    if "Fee Rate (%)" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Fee Rate (%)"] >= fee_lo_v) &
            (filtered_df["Fee Rate (%)"] <= fee_hi_v)
        ]

    # ── Available slider ───────────────────────────────────────────────────
    _avail_breaks = {
        "100": 100,         "500": 500,         "1K": 1_000,
        "5K": 5_000,        "10K": 10_000,      "50K": 50_000,
        "100K": 100_000,    "500K": 500_000,    "1M": 1_000_000,
        "5M": 5_000_000,    "10M+": 999_999_999,
    }
    _avail_labels = list(_avail_breaks.keys())
    with slider_cols[1]:
        avail_lo, avail_hi = st.select_slider(
            "Available",
            options=_avail_labels,
            value=("100", "10M+"),
            key="stocks_avail_range",
        )
    avail_lo_v = _avail_breaks[avail_lo]
    avail_hi_v = _avail_breaks[avail_hi]
    if "Available" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["Available"] >= avail_lo_v) &
            (filtered_df["Available"] <= avail_hi_v)
        ]

    # ── Market Cap slider ──────────────────────────────────────────────────
    if "Market Cap" in result_df.columns:
        _cap_breaks = {
            "$0":    0,      "$100M": 0.1,   "$250M": 0.25,
            "$500M": 0.5,   "$1B":   1,     "$2B":   2,
            "$5B":   5,     "$10B":  10,    "$25B":  25,
            "$50B":  50,    "$100B": 100,   "$250B": 250,
            "$500B": 500,   "$1T+":  9_999,
        }
        _labels = list(_cap_breaks.keys())
        with slider_cols[2]:
            lo_label, hi_label = st.select_slider(
                "Market Cap",
                options=_labels,
                value=("$0", "$1T+"),
                key="stocks_mktcap_range",
            )
        lo_b = _cap_breaks[lo_label]
        hi_b = _cap_breaks[hi_label]
        filtered_df = filtered_df[
            (filtered_df["Market Cap"] >= lo_b * 1_000_000_000) &
            (filtered_df["Market Cap"] <= hi_b * 1_000_000_000)
        ]

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
