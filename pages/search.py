"""
Search page — unified entry point.
"""

import streamlit as st
import pandas as pd

from ui_components import (
    render_sidebar,
    set_current_page,
    get_date_range,
    PRESET_OPTIONS,
    load_reference_names,
    nav_to_lawyer,
    nav_to_company,
    nav_to_firm,
)
from search_modules.company_search import load_all_companies

set_current_page("pages/search.py", "Search")
render_sidebar()

st.title("EquityIntel")
st.markdown(
    "Search a lawyer, company, or law firm to find related investment targets via SEC filings."
)
st.divider()

# ── Entity type picker ────────────────────────────────────────────────────────
entity_type = st.radio(
    "Search by",
    ["Lawyer", "Company", "Law Firm"],
    horizontal=True,
    label_visibility="collapsed",
    key="search_entity_type",
)

# ── Input + date range (all on one row) ──────────────────────────────────────
col_input, col_preset, col_from, col_to = st.columns([3, 1.2, 1, 1])

with col_preset:
    preset = st.selectbox(
        "Date range",
        PRESET_OPTIONS,
        index=1,
        label_visibility="visible",
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

effective_from = date_from if preset == "Custom" else date_from_default
effective_to = date_to if preset == "Custom" else date_to_default

lawyer_names, firm_terms = load_reference_names()

with col_input:
    query = ""
    selected_company_obj = None

    if entity_type == "Lawyer":
        selected_lawyer = st.selectbox(
            "Lawyer name",
            options=[""] + lawyer_names,
            label_visibility="hidden",
            key="search_lawyer_input",
        )
        query = selected_lawyer or ""

    elif entity_type == "Company":
        companies = load_all_companies()
        if companies:
            options = [""] + [c["display"] for c in companies]
            selected_display = st.selectbox(
                "Company",
                options=options,
                label_visibility="hidden",
                key="search_company_select",
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
                label_visibility="hidden",
                key="search_company_text",
            )

    else:  # Law Firm
        selected_firm = st.selectbox(
            "Law firm name",
            options=[""] + firm_terms,
            label_visibility="hidden",
            key="search_firm_input",
        )
        query = selected_firm or ""

# ── Search button ─────────────────────────────────────────────────────────────
st.markdown("")
_, btn_col, _ = st.columns([0.2, 0.6, 0.2])
search_clicked = btn_col.button("Search", type="primary", use_container_width=True)

if search_clicked:
    if not query or query.startswith("--"):
        st.error("Please enter a search term.")
    elif effective_from >= effective_to:
        st.error("Start date must be before end date.")
    else:
        st.session_state.search_start = effective_from
        st.session_state.search_end = effective_to
        st.session_state.back_page = None

        if entity_type == "Lawyer":
            st.session_state["_this_page"] = "pages/search.py"
            st.session_state["_this_label"] = "Search"
            nav_to_lawyer(query.strip())

        elif entity_type == "Company":
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
