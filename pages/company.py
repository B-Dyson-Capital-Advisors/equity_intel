"""
Company detail page.

Shows financial snapshot (immediate, from FMP reference) and legal counsel
(lazy, requires SEC search + OpenAI extraction, cached in SQLite).

Pivot buttons next to each lawyer let you jump to their other companies.
"""

import streamlit as st
import pandas as pd

from ui_components import (
    render_sidebar,
    render_back_button,
    set_current_page,
    fmt_currency,
    add_to_targets,
    get_api_key,
    nav_to_lawyer,
    nav_to_firm,
)
from search_modules.stock_reference import load_stock_reference
from search_modules.company_search import search_company_for_lawyers
from search_modules.cache import get_cached, set_cached

company: dict = st.session_state.get("current_company") or {}
ticker: str = company.get("ticker", "").replace(" US Equity", "").strip().upper()
company_name: str = company.get("name", "")

set_current_page("pages/company.py", company_name or ticker)
render_sidebar()
render_back_button()

cik = company.get("cik")
search_start = st.session_state.get("search_start")
search_end = st.session_state.get("search_end")

if not ticker and not company_name:
    st.warning("No company selected.")
    if st.button("Back to Search"):
        st.switch_page("pages/search.py")
    st.stop()

# ── Load FMP data ─────────────────────────────────────────────────────────────
ref_df = load_stock_reference()
company_data: dict | None = None
if ref_df is not None and ticker:
    matches = ref_df[ref_df["Symbol"] == ticker]
    if not matches.empty:
        company_data = matches.iloc[0].to_dict()

display_name = (
    company_data.get("Company Name", company_name) if company_data else company_name
) or ticker

# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_target = st.columns([5, 1])
with col_title:
    st.title(display_name)
    exchange = company_data.get("Exchange", "") if company_data else ""
    sector = company_data.get("Sector", "") if company_data else ""
    subtitle_parts = [p for p in [ticker, exchange, sector] if p]
    if subtitle_parts:
        st.markdown(" · ".join(subtitle_parts))

with col_target:
    st.markdown("")
    st.markdown("")
    already_in = any(
        t.get("ticker") == ticker for t in st.session_state.get("targets", [])
    )
    if already_in:
        st.success("In Targets")
    else:
        if st.button("Add to Targets", type="primary", use_container_width=True):
            add_to_targets(ticker, display_name)
            st.toast(f"Added {display_name} to Targets")
            st.rerun()

st.divider()

# ── Financial metrics ─────────────────────────────────────────────────────────
if company_data:
    mktcap = company_data.get("Market Cap") or 0
    ev = company_data.get("Enterprise Value TTM") or 0
    price = company_data.get("Price")
    ceo_val = company_data.get("CEO", "") or ""
    industry_val = company_data.get("Industry", "") or ""

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Market Cap", fmt_currency(mktcap))
    c2.metric("Enterprise Value", fmt_currency(ev))
    c3.metric(
        "Price",
        f"${price:.2f}" if price and not pd.isna(price) else "—",
    )
    c4.metric("CEO", ceo_val or "—")
    c5.metric("Industry", industry_val or "—")
    st.divider()

# ── Stock loan (if IB data loaded) ───────────────────────────────────────────
ib_all = st.session_state.get("ib_data")
if ib_all is not None and ticker:
    match = ib_all[ib_all["Symbol"].str.upper() == ticker]
    if not match.empty:
        row = match.iloc[0]
        st.subheader("Stock Loan (Interactive Brokers)")
        l1, l2, l3 = st.columns(3)
        rebate = row.get("Rebate Rate (%)")
        fee = row.get("Fee Rate (%)")
        avail = row.get("Available")
        l1.metric(
            "Rebate Rate",
            f"{rebate:.2f}%" if rebate is not None and not pd.isna(rebate) else "—",
        )
        l2.metric(
            "Fee Rate",
            f"{fee:.2f}%" if fee is not None and not pd.isna(fee) else "—",
        )
        l3.metric(
            "Available Shares",
            f"{int(avail):,}" if avail is not None and not pd.isna(avail) else "—",
        )
        st.divider()

# ── Legal Counsel ─────────────────────────────────────────────────────────────
st.subheader("Legal Counsel")
st.caption(
    "Lawyers and law firms found in SEC filings. "
    "Click 'See companies' next to a lawyer to explore their other clients."
)

cache_key = f"company_lawyers::{ticker}::{search_start}::{search_end}"
lawyers_df = st.session_state.get("results", {}).get(cache_key)

if lawyers_df is None:
    lawyers_df = get_cached("company_lawyers", ticker, search_start, search_end)
    if lawyers_df is not None:
        if "results" not in st.session_state:
            st.session_state["results"] = {}
        st.session_state["results"][cache_key] = lawyers_df

if lawyers_df is not None and not lawyers_df.empty:
    st.success(f"Found {len(lawyers_df)} lawyer / firm entries")
    st.markdown("")

    for i, row in lawyers_df.iterrows():
        lawyer = str(row.get("Lawyer", "") or "").strip()
        firm = str(row.get("Law Firm", "") or "").strip()
        is_firm_only = not lawyer or lawyer == "(Firm only - no lawyer name listed)"

        col_lawyer, col_firm, col_action = st.columns([2, 2.5, 1.2])
        col_lawyer.markdown(f"**{lawyer}**" if not is_firm_only else "*(firm only)*")
        col_firm.markdown(firm or "—")

        if not is_firm_only and lawyer:
            if col_action.button("See companies", key=f"pivot_lawyer_{i}", use_container_width=True):
                nav_to_lawyer(lawyer)
        elif firm:
            if col_action.button("See companies", key=f"pivot_firm_{i}", use_container_width=True):
                nav_to_firm(firm)

    st.divider()
    csv = lawyers_df.to_csv(index=False)
    st.download_button(
        "Download Counsel CSV",
        csv,
        file_name=f"{ticker}_legal_counsel.csv",
        mime="text/csv",
    )

else:
    api_key = get_api_key()
    if not api_key:
        st.info(
            "OpenAI API key not configured — legal counsel search is unavailable."
        )
    elif not search_start or not search_end:
        st.info("Set a date range on the Search page, then return here.")
    else:
        if st.button("Find Legal Counsel", type="primary"):
            with st.spinner("Searching SEC filings..."):
                prog = st.empty()
                msgs: list[str] = []

                def _cb(msg: str):
                    msgs.append(msg)
                    prog.info(msg)

                try:
                    lawyers_df = search_company_for_lawyers(
                        company.get("display") or ticker,
                        search_start,
                        search_end,
                        api_key,
                        _cb,
                        cik=cik,
                        company_name=company_name,
                    )
                    prog.empty()
                    set_cached(
                        "company_lawyers", ticker, search_start, search_end, lawyers_df
                    )
                    if "results" not in st.session_state:
                        st.session_state["results"] = {}
                    st.session_state["results"][cache_key] = lawyers_df
                    st.rerun()
                except Exception as exc:
                    prog.empty()
                    st.error(f"Search failed: {exc}")
