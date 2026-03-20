"""
Company detail page.

Reached by clicking a company row from the lawyer or firm pages, or by searching
a company directly from the search page.

Shows:
  1. Financial snapshot (immediate, from FMP reference CSV)
  2. Stock loan data (from IB FTP, if loaded)
  3. Legal Counsel — lawyers / firms found in SEC filings (lazy, cached in SQLite)

From the Legal Counsel section, clicking a lawyer's pivot button navigates to
their lawyer page (showing all companies they represent).
"""

import streamlit as st
import pandas as pd

from ui_components import (
    render_sidebar,
    render_breadcrumbs,
    fmt_currency,
    add_to_targets,
    get_api_key,
    nav_to_lawyer,
    nav_to_firm,
)
from search_modules.stock_reference import load_stock_reference
from search_modules.company_search import search_company_for_lawyers
from search_modules.cache import get_cached, set_cached

render_sidebar()
render_breadcrumbs()

company: dict = st.session_state.get("current_company") or {}
ticker: str = company.get("ticker", "").replace(" US Equity", "").strip().upper()
company_name: str = company.get("name", "")
cik = company.get("cik")
search_start = st.session_state.get("search_start")
search_end = st.session_state.get("search_end")

if not ticker and not company_name:
    st.warning("No company selected.")
    if st.button("← Back to Search"):
        st.switch_page("pages/search.py")
    st.stop()

# ── Load FMP data for this ticker ─────────────────────────────────────────────
ref_df = load_stock_reference()
company_data: dict | None = None
if ref_df is not None and ticker:
    matches = ref_df[ref_df["Symbol"] == ticker]
    if not matches.empty:
        company_data = matches.iloc[0].to_dict()

display_name = (
    company_data.get("Company Name", company_name) if company_data else company_name
) or ticker

# ── Page header ───────────────────────────────────────────────────────────────
col_title, col_target = st.columns([5, 1])
with col_title:
    exchange_badge = (
        f" · **{company_data.get('Exchange', '')}**" if company_data else ""
    )
    st.title(f"🏢  {display_name}")
    st.markdown(
        f"**{ticker}**{exchange_badge}"
        + (f" · {company_data.get('Sector', '')}" if company_data and company_data.get("Sector") else "")
    )

with col_target:
    st.markdown("")
    st.markdown("")
    already_in = any(
        t.get("ticker") == ticker for t in st.session_state.get("targets", [])
    )
    if already_in:
        st.success("✓ In Targets")
    else:
        if st.button("＋ Add to Targets", type="primary", use_container_width=True):
            add_to_targets(ticker, display_name)
            st.toast(f"Added {display_name} to Targets")
            st.rerun()

st.divider()

# ── Financial metrics ─────────────────────────────────────────────────────────
if company_data:
    mktcap = company_data.get("Market Cap") or 0
    ev = company_data.get("Enterprise Value TTM") or 0
    ceo_val = company_data.get("CEO", "") or ""
    industry_val = company_data.get("Industry", "") or ""
    ipo_date = company_data.get("IPO Date", "") or ""

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Market Cap", fmt_currency(mktcap))
    c2.metric("Enterprise Value", fmt_currency(ev))
    c3.metric("CEO", ceo_val or "—")
    c4.metric("Industry", industry_val or "—")
    c5.metric("IPO Date", str(ipo_date) if ipo_date else "—")
    st.divider()

# ── Stock loan snapshot ───────────────────────────────────────────────────────
# If we already loaded IB data (stored in session from stocks page), show a row
ib_data = None
if ticker:
    stored_ib = st.session_state.get("ib_data")
    if stored_ib is not None and not stored_ib.empty:
        match = stored_ib[stored_ib["Symbol"].str.upper() == ticker]
        if not match.empty:
            row = match.iloc[0]
            ib_data = {
                "rebate": row.get("Rebate Rate (%)"),
                "fee": row.get("Fee Rate (%)"),
                "available": row.get("Available"),
            }

if ib_data:
    st.subheader("📊 Stock Loan (Interactive Brokers)")
    l1, l2, l3 = st.columns(3)
    rebate = ib_data["rebate"]
    fee = ib_data["fee"]
    avail = ib_data["available"]
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

# ── Legal Counsel section ─────────────────────────────────────────────────────
st.subheader("⚖️ Legal Counsel")
st.caption(
    "Lawyers and law firms extracted from SEC filings. "
    "Click **→ See companies** to explore a lawyer's other clients."
)

cache_key_lawyers = f"company_lawyers::{ticker}::{search_start}::{search_end}"
lawyers_df = st.session_state.get("results", {}).get(cache_key_lawyers)

if lawyers_df is None:
    lawyers_df = get_cached("company_lawyers", ticker, search_start, search_end)
    if lawyers_df is not None:
        if "results" not in st.session_state:
            st.session_state["results"] = {}
        st.session_state["results"][cache_key_lawyers] = lawyers_df

if lawyers_df is not None and not lawyers_df.empty:
    _render_counsel = True
else:
    _render_counsel = False

if _render_counsel:
    _render_df = lawyers_df
else:
    api_key = get_api_key()
    if not api_key:
        st.info(
            "OpenAI API key not configured — legal counsel search is unavailable. "
            "Contact your administrator."
        )
    else:
        if not search_start or not search_end:
            st.info(
                "Set a date range on the Search page, then return here to load legal counsel."
            )
        else:
            if st.button("🔍  Find Legal Counsel", type="primary"):
                with st.spinner("Searching SEC filings…"):
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
                        st.session_state["results"][cache_key_lawyers] = lawyers_df
                        st.rerun()
                    except Exception as exc:
                        prog.empty()
                        st.error(f"Search failed: {exc}")

if _render_counsel and lawyers_df is not None:
    st.success(f"Found **{len(lawyers_df)}** lawyer / firm entries")
    st.markdown("")

    # Render each row as a card with pivot button
    for i, row in lawyers_df.iterrows():
        lawyer = str(row.get("Lawyer", "") or "").strip()
        firm = str(row.get("Law Firm", "") or "").strip()
        is_firm_only = not lawyer or lawyer == "(Firm only - no lawyer name listed)"

        col_lawyer, col_firm, col_action = st.columns([2, 2.5, 1.2])

        if is_firm_only:
            col_lawyer.markdown("*(Firm only)*")
        else:
            col_lawyer.markdown(f"**{lawyer}**")

        col_firm.markdown(firm or "—")

        action_label = "→ See companies"
        if not is_firm_only and lawyer:
            if col_action.button(action_label, key=f"pivot_lawyer_{i}", use_container_width=True):
                nav_to_lawyer(lawyer)
        elif firm:
            if col_action.button(action_label, key=f"pivot_firm_{i}", use_container_width=True):
                nav_to_firm(firm)

    st.divider()

    csv = lawyers_df.to_csv(index=False)
    st.download_button(
        "⬇ Download Counsel CSV",
        csv,
        file_name=f"{ticker}_legal_counsel.csv",
        mime="text/csv",
    )
