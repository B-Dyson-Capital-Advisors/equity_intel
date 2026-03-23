"""
Shared UI components used across all pages.
"""

import os
import streamlit as st
import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_REFERENCE_XLSX = os.path.join(_DATA_DIR, "lawyer_names_final.xlsx")


PRESET_OPTIONS = [
    "Last 30 days",
    "Last 1 year",
    "Last 3 years",
    "Last 5 years",
    "Last 10 years",
    "All (since 2001)",
    "Custom",
]


def get_date_range(preset: str):
    """Return (start_date, end_date) for a preset label."""
    end = pd.Timestamp.now()
    offsets = {
        "Last 30 days": pd.DateOffset(days=30),
        "Last 1 year": pd.DateOffset(years=1),
        "Last 3 years": pd.DateOffset(years=3),
        "Last 5 years": pd.DateOffset(years=5),
        "Last 10 years": pd.DateOffset(years=10),
    }
    if preset in offsets:
        return (end - offsets[preset]).date(), end.date()
    if preset == "All (since 2001)":
        return pd.Timestamp("2001-01-01").date(), end.date()
    # Custom — caller handles
    return (end - pd.DateOffset(years=1)).date(), end.date()


def load_reference_names() -> tuple[list[str], list[str]]:
    """
    Load lawyer names and law firm EDGAR search terms from the reference Excel.
    Results are cached in session state so the file is only read once per session.
    Returns (lawyer_names, firm_search_terms) as sorted lists.
    """
    cache_key = "_reference_names"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    lawyer_names: list[str] = []
    firm_terms: list[str] = []

    try:
        lawyers_df = pd.read_excel(_REFERENCE_XLSX, sheet_name="Lawyer Names", usecols=["Name"])
        lawyer_names = (
            lawyers_df["Name"]
            .dropna()
            .drop_duplicates()
            .str.strip()
            .sort_values()
            .tolist()
        )
    except Exception:
        pass

    try:
        firms_df = pd.read_excel(_REFERENCE_XLSX, sheet_name="Law Firms", usecols=["EDGAR Search Term"])
        firm_terms = (
            firms_df["EDGAR Search Term"]
            .dropna()
            .drop_duplicates()
            .str.strip()
            .sort_values()
            .tolist()
        )
    except Exception:
        pass

    st.session_state[cache_key] = (lawyer_names, firm_terms)
    return lawyer_names, firm_terms


def get_api_key() -> str | None:
    try:
        return st.secrets["OPENAI_API_KEY"]
    except (KeyError, FileNotFoundError):
        return None


def render_sidebar():
    """Sidebar: app name + navigation buttons."""
    with st.sidebar:
        st.markdown("## EquityIntel")
        st.divider()

        if st.button("New Search", use_container_width=True, key="sb_search"):
            st.session_state.back_page = None
            st.switch_page("pages/search.py")

        if st.button("Stock Loan", use_container_width=True, key="sb_stocks"):
            st.session_state.back_page = None
            st.switch_page("pages/stocks.py")


def render_back_button():
    """
    Show a single 'Back to [page]' link based on st.session_state.back_page.
    Replaces the breadcrumb trail that caused infinite nav loops.
    """
    back = st.session_state.get("back_page")
    if not back:
        return
    if st.button(f"<- Back to {back['label']}", key="back_btn"):
        # Clear back_page so the destination page doesn't show a stale back link
        st.session_state.back_page = back.get("prev_back")
        st.switch_page(back["page"])
    st.markdown("")  # spacing


def fmt_currency(value, suffix="") -> str:
    """Format a numeric value as $XB or $XM."""
    if value is None or pd.isna(value) or value == 0:
        return "—"
    if abs(value) >= 1e9:
        return f"${value/1e9:.2f}B{suffix}"
    if abs(value) >= 1e6:
        return f"${value/1e6:.0f}M{suffix}"
    return f"${value:,.0f}{suffix}"


def apply_df_column_formats(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Scale market cap / EV to $MM and return (display_df, column_config).
    Keeps original df untouched.
    """
    display_df = df.copy()
    column_config = {}

    if "Price" in display_df.columns:
        column_config["Price"] = st.column_config.NumberColumn("Price ($)", format="$%.2f")
    if "Market Cap" in display_df.columns:
        display_df["Market Cap"] = (display_df["Market Cap"] / 1_000_000).round(1)
        column_config["Market Cap"] = st.column_config.NumberColumn(
            "Mkt Cap ($MM)", format="localized"
        )
    if "Enterprise Value" in display_df.columns:
        display_df["Enterprise Value"] = (
            display_df["Enterprise Value"] / 1_000_000
        ).round(1)
        column_config["Enterprise Value"] = st.column_config.NumberColumn(
            "EV ($MM)", format="localized"
        )
    if "Rebate Rate (%)" in display_df.columns:
        column_config["Rebate Rate (%)"] = st.column_config.NumberColumn(
            "Rebate Rate (%)", format="%.2f"
        )
    if "Fee Rate (%)" in display_df.columns:
        column_config["Fee Rate (%)"] = st.column_config.NumberColumn(
            "Fee Rate (%)", format="%.2f"
        )
    if "Available" in display_df.columns:
        display_df["Available"] = display_df["Available"].round(0)
        column_config["Available"] = st.column_config.NumberColumn(
            "Available Shares", format="localized"
        )

    return display_df, column_config



def _nav(page: str, label: str, entity_key: str, entity_value):
    """
    Core navigation helper.
    Saves current back_page so the destination can render a correct Back button,
    then updates the entity and switches page.
    """
    # The destination's back button should point back to the CURRENT page
    current_back = st.session_state.get("back_page")
    st.session_state[entity_key] = entity_value
    st.session_state.back_page = {
        "page": _current_page(),
        "label": _current_label(),
        "prev_back": current_back,   # allows chaining: back → back → back
    }
    st.switch_page(page)


def _current_page() -> str:
    """Best-effort guess at the currently-running page path."""
    # Streamlit doesn't expose this directly; we store it ourselves
    return st.session_state.get("_this_page", "pages/search.py")


def _current_label() -> str:
    return st.session_state.get("_this_label", "Search")


def set_current_page(page: str, label: str):
    """Call at the top of each page to register it as the current page."""
    st.session_state["_this_page"] = page
    st.session_state["_this_label"] = label


def nav_to_lawyer(lawyer_name: str):
    _nav(
        "pages/lawyer.py",
        lawyer_name.strip(),
        "current_lawyer",
        lawyer_name.strip(),
    )


def nav_to_company(ticker: str, name: str, cik=None):
    ticker = ticker.replace(" US Equity", "").strip().upper()
    _nav(
        "pages/company.py",
        name,
        "current_company",
        {
            "ticker": ticker,
            "name": name,
            "cik": cik,
            "display": f"{name} ({ticker})" if ticker else name,
        },
    )


def nav_to_firm(firm_name: str):
    _nav(
        "pages/firm.py",
        firm_name.strip(),
        "current_firm",
        firm_name.strip(),
    )
