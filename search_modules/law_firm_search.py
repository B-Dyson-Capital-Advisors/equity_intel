import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from .utils import search_paginated, extract_ticker_and_clean_name, filter_important_filings
from .company_search import get_company_filings, process_single_filing, clean_firm_name
import re


def get_most_recent_lawyer_for_company(cik, company_name, firm_name, start_date, end_date):
    """
    For a given company, find the most recent lawyer from the specified firm.
    Uses the same approach as Tab 1 (company search).

    Args:
        cik: Company CIK
        company_name: Company name
        firm_name: Law firm to search for
        start_date: Start date for filings
        end_date: End date for filings

    Returns:
        Most recent lawyer name from that firm, or None
    """
    try:
        # Get company filings (same as Tab 1)
        filings = get_company_filings(cik, start_date, end_date)

        if not filings:
            return None

        # Limit to most recent 10 filings (for performance)
        filings = filings[:10]

        # Extract lawyers from filings
        firm_to_lawyers_all = {}

        for filing in filings:
            # Process filing (same as Tab 1) - but we don't have API key here
            # So we'll need to extract without GPT assistance
            try:
                accession_no_dashes = filing['accession'].replace('-', '')

                if filing['primary_doc']:
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{filing['primary_doc']}"
                else:
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{filing['accession']}.htm"

                # Extract text
                from .company_search import extract_counsel_sections, extract_lawyers_by_regex
                text = extract_counsel_sections(doc_url)

                if text:
                    # Extract lawyers using regex (same as Tab 1)
                    firm_to_lawyers = extract_lawyers_by_regex(text, company_name)

                    # Merge with overall results
                    for firm, lawyers in firm_to_lawyers.items():
                        if firm not in firm_to_lawyers_all:
                            firm_to_lawyers_all[firm] = set()
                        firm_to_lawyers_all[firm].update(lawyers)
            except:
                continue

        # Now find lawyers from the specific firm we're searching for
        firm_normalized = clean_firm_name(firm_name).lower()
        firm_base = re.sub(r'\s+(llp|llc|p\.c\.|p\.a\.)$', '', firm_normalized, flags=re.IGNORECASE).strip()

        for firm, lawyers in firm_to_lawyers_all.items():
            firm_clean = clean_firm_name(firm).lower()
            firm_clean_base = re.sub(r'\s+(llp|llc|p\.c\.|p\.a\.)$', '', firm_clean, flags=re.IGNORECASE).strip()

            # Check if this is the same firm (fuzzy match)
            if (firm_base in firm_clean_base or
                firm_clean_base in firm_base or
                firm_normalized == firm_clean):
                if lawyers:
                    # Return the first lawyer (alphabetically sorted)
                    return sorted(lawyers)[0]

        return None

    except Exception as e:
        return None


def search_law_firm_for_companies(firm_name, start_date, end_date, progress_callback=None):
    """
    Search for companies represented by a law firm, including most recent lawyer

    Args:
        firm_name: Name of the law firm
        start_date: Start date for search
        end_date: End date for search
        progress_callback: Optional progress callback function

    Returns:
        DataFrame with companies, tickers, market cap, and most recent lawyer
    """

    # First, get the basic company results
    if progress_callback:
        progress_callback(f"Searching for companies represented by {firm_name}...")

    # Get raw filing data instead of processed results
    results, total = search_paginated(firm_name, start_date, end_date, max_total=10000)

    if not results:
        raise ValueError(f"No results found for law firm: {firm_name}")

    df = pd.DataFrame(results)

    if progress_callback:
        progress_callback(f"Total filings found: {len(df)}")

    df_filtered = filter_important_filings(df)

    if progress_callback:
        progress_callback(f"After filtering to relevant filing types: {len(df_filtered)}")

    if df_filtered.empty:
        raise ValueError(f"No relevant filings found for law firm: {firm_name}")

    df_filtered[['clean_company_name', 'ticker']] = df_filtered['company_name'].apply(
        lambda x: pd.Series(extract_ticker_and_clean_name(x))
    )

    df_filtered['filing_date'] = pd.to_datetime(df_filtered['filing_date'])

    # Keep all filings for now (we'll need them for lawyer extraction)
    df_sorted = df_filtered.sort_values('filing_date', ascending=False)

    # Get unique companies with their most recent filing (preserve CIK and accession data)
    df_unique = df_sorted.drop_duplicates(subset=['clean_company_name'], keep='first')

    if progress_callback:
        progress_callback(f"Unique companies: {len(df_unique)}")

    # Now enrich with market cap and stock loan data
    from .stock_reference import filter_and_enrich_tickers
    from .stock_loan import fetch_shortstock_data

    result_df = df_unique[['clean_company_name', 'ticker', 'filing_date']].copy()
    result_df.columns = ['Company', 'Ticker', 'Filing Date']

    result_df = result_df[result_df['Ticker'] != ""].copy()

    # Clean ticker
    result_df['Ticker_Clean'] = result_df['Ticker'].str.replace(' US Equity', '', regex=False).str.strip().str.upper()

    if progress_callback:
        progress_callback(f"Filtering to reference tickers and adding market cap...")

    # Filter by reference tickers and add market cap
    result_df = filter_and_enrich_tickers(result_df, ticker_column='Ticker_Clean')

    if result_df.empty:
        raise ValueError(f"No companies found with tickers in stock reference file")

    if progress_callback:
        progress_callback(f"Adding stock loan availability data...")

    # Fetch stock loan data
    try:
        stock_loan_df = fetch_shortstock_data()
        stock_loan_df['Symbol_Clean'] = stock_loan_df['Symbol'].str.strip().str.upper()

        result_df = result_df.merge(
            stock_loan_df[['Symbol_Clean', 'Rebate Rate (%)', 'Fee Rate (%)', 'Available']],
            left_on='Ticker_Clean',
            right_on='Symbol_Clean',
            how='left'
        )
        result_df = result_df.drop('Symbol_Clean', axis=1)
    except Exception as e:
        if progress_callback:
            progress_callback(f"Note: Could not fetch stock loan data ({str(e)})")

    # Add back " US Equity" suffix for Bloomberg format
    result_df['Ticker'] = result_df['Ticker_Clean'] + ' US Equity'

    # Extract most recent lawyer for each company (using Tab 1's approach)
    if progress_callback:
        progress_callback(f"Extracting most recent lawyer for each company...")

    # Build company CIK mapping from df_unique
    company_cik_map = {}
    for _, row in df_unique.iterrows():
        company = row['clean_company_name']
        cik = row.get('cik', '')
        if company and cik:
            company_cik_map[company] = str(cik).zfill(10)

    # Add Most Recent Lawyer column
    result_df['Most Recent Lawyer'] = None

    # Extract lawyers in parallel (limit to 5 concurrent to respect SEC)
    def extract_lawyer_for_row(row):
        """Extract most recent lawyer for a company"""
        company = row['Company']
        cik = company_cik_map.get(company)

        if not cik:
            return None

        # Use Tab 1's approach: fetch company filings and extract lawyers
        lawyer = get_most_recent_lawyer_for_company(
            cik, company, firm_name, start_date, end_date
        )
        return lawyer

    # Process in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(extract_lawyer_for_row, row): idx
                   for idx, row in result_df.iterrows()}

        completed = 0
        for future in as_completed(futures):
            completed += 1
            if progress_callback and completed % 10 == 0:
                progress_callback(f"Lawyer extraction: {completed}/{len(result_df)} companies...")

            try:
                idx = futures[future]
                lawyer = future.result()
                if lawyer:
                    result_df.at[idx, 'Most Recent Lawyer'] = lawyer
            except:
                pass

    # Fill None with "Not Found"
    result_df['Most Recent Lawyer'] = result_df['Most Recent Lawyer'].fillna('Not Found')

    # Format Filing Date
    result_df['Filing Date'] = pd.to_datetime(result_df['Filing Date']).dt.strftime('%Y-%m-%d')

    # Reorder columns: Company, Ticker, Most Recent Lawyer, Market Cap, 52wk High/Low, Stock Loan columns, Filing Date
    final_columns = ['Company', 'Ticker', 'Most Recent Lawyer', 'Market Cap']

    if '52wk High' in result_df.columns:
        final_columns.append('52wk High')
    if '52wk Low' in result_df.columns:
        final_columns.append('52wk Low')

    if 'Rebate Rate (%)' in result_df.columns:
        final_columns.extend(['Rebate Rate (%)', 'Fee Rate (%)', 'Available'])

    final_columns.append('Filing Date')

    # Drop internal columns (cik, adsh) before final output
    result_df = result_df[final_columns]

    if progress_callback:
        progress_callback(f"Search complete: {len(result_df)} companies")

    return result_df
