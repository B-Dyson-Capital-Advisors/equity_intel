"""
Shared UI components used across all pages.
"""

import streamlit as st
import pandas as pd


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


def get_api_key() -> str | None:
    try:
        return st.secrets["OPENAI_API_KEY"]
    except (KeyError, FileNotFoundError):
        return None


def render_sidebar():
    """Sidebar: logo, navigation buttons, and targets count."""
    with st.sidebar:
        st.markdown("## EquityIntel")
        st.markdown("*Investment target intelligence*")
        st.divider()

        if st.button("🔍  New Search", use_container_width=True, key="sb_search"):
            st.session_state.nav_stack = [{"page": "pages/search.py", "label": "Search"}]
            st.switch_page("pages/search.py")

        target_count = len(st.session_state.get("targets", []))
        label = f"🎯  Targets ({target_count})" if target_count else "🎯  Targets"
        if st.button(label, use_container_width=True, key="sb_targets"):
            st.switch_page("pages/targets.py")

        st.divider()

        # Recent nav history
        stack = st.session_state.get("nav_stack", [])
        if len(stack) > 1:
            st.markdown("**Recent:**")
            # Show up to last 4 entries (excluding current)
            for i, crumb in enumerate(reversed(stack[:-1])):
                real_i = len(stack) - 2 - i
                if st.button(
                    f"↩ {crumb['label']}",
                    use_container_width=True,
                    key=f"sb_crumb_{real_i}",
                ):
                    st.session_state.nav_stack = stack[: real_i + 1]
                    st.switch_page(crumb["page"])
                if i >= 3:
                    break

        # Cache controls (collapsible)
        with st.expander("⚙️ Settings", expanded=False):
            from search_modules.cache import get_cache_stats, clear_all, clear_expired
            stats = get_cache_stats()
            st.caption(
                f"Cache: {stats['fresh']} fresh · {stats['expired']} expired entries"
            )
            col1, col2 = st.columns(2)
            if col1.button("Clear expired", use_container_width=True, key="sb_clear_exp"):
                removed = clear_expired()
                st.toast(f"Removed {removed} expired entries")
            if col2.button("Clear all", use_container_width=True, key="sb_clear_all"):
                clear_all()
                st.toast("Cache cleared")


def render_breadcrumbs():
    """Breadcrumb trail based on nav_stack."""
    stack = st.session_state.get("nav_stack", [])
    if len(stack) <= 1:
        return

    parts = []
    for i, crumb in enumerate(stack):
        if i < len(stack) - 1:
            parts.append(f"[{crumb['label']}](?crumb={i})")
        else:
            parts.append(f"**{crumb['label']}**")

    # Render as buttons in a row
    cols = st.columns(len(stack) * 2 - 1)
    for i, crumb in enumerate(stack):
        col = cols[i * 2]
        if i < len(stack) - 1:
            if col.button(crumb["label"], key=f"bc_{i}"):
                st.session_state.nav_stack = stack[: i + 1]
                st.switch_page(crumb["page"])
        else:
            col.markdown(f"**{crumb['label']}**")

        if i < len(stack) - 1 and i * 2 + 1 < len(cols):
            cols[i * 2 + 1].markdown("›")

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
    Divide market cap / EV columns to $MM and return (display_df, column_config).
    Keeps original df untouched.
    """
    display_df = df.copy()
    column_config = {}

    if "Market Cap" in display_df.columns:
        display_df["Market Cap"] = (display_df["Market Cap"] / 1_000_000).round(1)
        column_config["Market Cap"] = st.column_config.NumberColumn(
            "Mkt Cap ($MM)", format="%.1f"
        )
    if "Enterprise Value TTM" in display_df.columns:
        display_df["Enterprise Value TTM"] = (
            display_df["Enterprise Value TTM"] / 1_000_000
        ).round(1)
        column_config["Enterprise Value TTM"] = st.column_config.NumberColumn(
            "EV TTM ($MM)", format="%.1f"
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


def add_to_targets(ticker: str, name: str) -> bool:
    """Add a company to targets. Returns True if newly added, False if already present."""
    target = {"ticker": ticker, "name": name}
    if "targets" not in st.session_state:
        st.session_state.targets = []
    for t in st.session_state.targets:
        if t.get("ticker") == ticker:
            return False
    st.session_state.targets.append(target)
    return True


def nav_to_lawyer(lawyer_name: str):
    """Set state and navigate to lawyer page."""
    st.session_state.current_lawyer = lawyer_name.strip()
    stack = st.session_state.get("nav_stack", [])
    stack.append({"page": "pages/lawyer.py", "label": lawyer_name.strip()})
    st.session_state.nav_stack = stack
    st.switch_page("pages/lawyer.py")


def nav_to_company(ticker: str, name: str, cik=None):
    """Set state and navigate to company page."""
    ticker = ticker.replace(" US Equity", "").strip().upper()
    st.session_state.current_company = {
        "ticker": ticker,
        "name": name,
        "cik": cik,
        "display": f"{name} ({ticker})" if ticker else name,
    }
    stack = st.session_state.get("nav_stack", [])
    stack.append({"page": "pages/company.py", "label": name})
    st.session_state.nav_stack = stack
    st.switch_page("pages/company.py")


def nav_to_firm(firm_name: str):
    """Set state and navigate to firm page."""
    st.session_state.current_firm = firm_name.strip()
    stack = st.session_state.get("nav_stack", [])
    stack.append({"page": "pages/firm.py", "label": firm_name.strip()})
    st.session_state.nav_stack = stack
    st.switch_page("pages/firm.py")
