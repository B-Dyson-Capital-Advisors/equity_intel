# Legal Counsel Finder - Enhancement Plan

## Current Application

**What It Does:**
- **Search by Lawyer:** Find all companies that used a specific lawyer in SEC filings
- **Search by Law Firm:** Find all companies that used a specific law firm
- **Stock Loan Availability:** View lending data for all US stocks (rebate rates, fee rates, availability)
- **Date Range Filtering:** Search filings within specific time periods
- **Data Export:** Download results as CSV

**Workflow:** Scrapes SEC EDGAR for legal counsel in filings → Enriches with FMP financial data (price, market cap, metrics) → Merges with stock loan data → Displays unified results

**Current Data Displayed:**
- Company Name, Ticker, Exchange, Price
- Market Cap ($MM), Enterprise Value ($MM)
- CEO, Sector, Industry
- Stock Loan Data (Rebate Rate, Fee Rate, Available Shares)
- Filing Date

---

## Planned Enhancements

### 1. **Lawyer Dropdown Menu**
**Current:** Text input (manual typing)
**Enhancement:** Pre-populated dropdown list
- Faster selection, no typos
- Option for multi-select

### 2. **Additional Financial Metrics (FMP)**
**Add Key Metrics:**
- Valuation: P/E Ratio, EV/EBITDA, Price/Book
- Performance: Revenue, Net Income, Free Cash Flow
- Profitability: Profit Margin, ROE
- Growth: Revenue Growth %, Earnings Growth %

**Decision Needed:** Which metrics are priority?

### 3. **Interactive Drill-Down**
**Current:** Search results → Must switch tabs to see details
**Enhancement:** Click company name → Instant detailed view

**Detail View Shows:**
- All recent SEC filings & dates
- Complete financial metrics
- Stock loan history & trends
- Direct links to SEC filings
- "Back to Results" button

**Benefit:** No tab switching, faster research

---

## Timeline
- Phase 1: Dropdown (2 days)
- Phase 2: Additional metrics (4 days)
- Phase 3: Interactive drill-down (7 days)

**Total: ~2 weeks**
