"""
Search page — unified entry point.

The user picks an entity type (Lawyer / Company / Law Firm), enters a query,
sets a date range, and hits Search. The app stores the query in session state
and navigates to the matching detail page.
"""

import streamlit as st
import pandas as pd

from ui_components import (
    render_sidebar,
    render_breadcrumbs,
    get_date_range,
    PRESET_OPTIONS,
    nav_to_lawyer,
    nav_to_company,
    nav_to_firm,
)
from search_modules.company_search import load_all_companies
from search_modules.law_firm_reference import MAJOR_LAW_FIRMS

render_sidebar()

st.title("EquityIntel")
st.markdown(
    "Find investment targets through legal relationships in SEC filings. "
    "Search a lawyer, company, or law firm to explore connections."
)
st.divider()

# ── Entity type picker ────────────────────────────────────────────────────────
entity_type = st.radio(
    "Search by",
    ["👤  Lawyer", "🏢  Company", "⚖️  Law Firm"],
    horizontal=True,
    label_visibility="collapsed",
    key="search_entity_type",
)

col_input, col_preset, col_from, col_to = st.columns([3, 1.2, 1, 1])

# ── Input widget (depends on entity type) ────────────────────────────────────
with col_input:
    query = ""
    selected_company_obj = None

    if entity_type == "👤  Lawyer":
        query = st.text_input(
            "Lawyer name",
            placeholder="e.g. Michael Penney",
            label_visibility="collapsed",
            key="search_lawyer_input",
        )

    elif entity_type == "🏢  Company":
        companies = load_all_companies()
        if companies:
            options = [""] + [c["display"] for c in companies]
            selected_display = st.selectbox(
                "Company",
                options=options,
                label_visibility="collapsed",
                key="search_company_select",
                help="Type to search by company name, ticker, or CIK",
            )
            if selected_display:
                query = selected_display
                selected_company_obj = next(
                    (c for c in companies if c["display"] == selected_display), None
                )
        else:
            query = st.text_input(
                "Company name or ticker",
                placeholder="e.g. Enovix Corp",
                label_visibility="collapsed",
                key="search_company_text",
            )

    else:  # Law Firm
        firm_options = (
            [""]
            + sorted(MAJOR_LAW_FIRMS)
            + ["── Enter a different firm below ──"]
        )
        selected_firm = st.selectbox(
            "Law Firm",
            firm_options,
            label_visibility="collapsed",
            key="search_firm_select",
        )
        if selected_firm and selected_firm != "── Enter a different firm below ──":
            query = selected_firm
        else:
            query = st.text_input(
                "Enter firm name",
                placeholder="e.g. Cooley LLP",
                label_visibility="collapsed",
                key="search_firm_custom",
            )

# ── Date range ────────────────────────────────────────────────────────────────
with col_preset:
    preset = st.selectbox(
        "Date range",
        PRESET_OPTIONS,
        index=1,  # default: Last 1 year
        label_visibility="collapsed",
        key="search_preset",
    )

date_from_default, date_to_default = get_date_range(preset)

with col_from:
    date_from = st.date_input(
        "From",
        value=date_from_default,
        max_value=pd.Timestamp.now().date(),
        disabled=(preset != "Custom"),
        label_visibility="visible",
        key="search_from",
    )

with col_to:
    date_to = st.date_input(
        "To",
        value=date_to_default,
        max_value=pd.Timestamp.now().date(),
        disabled=(preset != "Custom"),
        label_visibility="visible",
        key="search_to",
    )

# Use widget dates for Custom, preset dates otherwise
effective_from = date_from if preset == "Custom" else date_from_default
effective_to = date_to if preset == "Custom" else date_to_default

# ── Search button ─────────────────────────────────────────────────────────────
st.markdown("")
_, btn_col, _ = st.columns([0.2, 0.6, 0.2])
search_clicked = btn_col.button("Search", type="primary", use_container_width=True)

if search_clicked:
    if not query or query.startswith("──"):
        st.error("Please enter a search term.")
    elif effective_from >= effective_to:
        st.error("Start date must be before end date.")
    else:
        st.session_state.search_start = effective_from
        st.session_state.search_end = effective_to

        if entity_type == "👤  Lawyer":
            nav_to_lawyer(query.strip())

        elif entity_type == "🏢  Company":
            if selected_company_obj:
                nav_to_company(
                    selected_company_obj["ticker"] or "",
                    selected_company_obj["name"],
                    cik=selected_company_obj["cik"],
                )
            else:
                nav_to_company("", query.strip())

        else:
            nav_to_firm(query.strip())

# ── Quick tips ────────────────────────────────────────────────────────────────
st.divider()
with st.expander("How to use EquityIntel", expanded=False):
    st.markdown("""
**Workflow examples:**

- *"I worked with Michael Penney on the Enovix deal — who else does he represent?"*
  → Search **Lawyer**: `Michael Penney`

- *"What lawyers worked on Enovix filings? Do I know any of them?"*
  → Search **Company**: `Enovix`  → click **Find Legal Counsel** on the company page

- *"Arnold & Porter works with a lot of tech companies — which ones should I approach?"*
  → Search **Law Firm**: `Arnold & Porter LLP`

**On result pages:**
- Click any company row to open its full detail view (financials + legal counsel)
- On a company page, click **→ See companies** next to any lawyer to pivot
- Use **+ Add to Targets** to save companies to your pipeline
- The **Targets** page lets you review and export your full list
""")
