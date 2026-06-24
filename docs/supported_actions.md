# Supported Actions

This page describes the active implementation only. Legacy code under `src/`
and planned `Intent` values are not treated as working product features.

## Working component pipeline

The project can currently execute this pipeline through Python components:

```text
Ticker and annual/quarterly date range
    ↓
Load matching financial observations from SQLite
    ↓
Fetch SEC data when temporal coverage is incomplete
    ↓
Normalize and persist SEC observations
    ↓
Calculate one financial-metric snapshot per reporting date
    ↓
Adjust metrics present in the final snapshot using historical trends
```

This is not yet exposed as an end-to-end natural-language or LangGraph action.

## SEC retrieval

The active SEC provider can:

- Retrieve basic company name and ticker metadata for an SEC-listed company.
- Retrieve annual and quarterly financial observations for an exact reporting
  date or an inclusive date range.
- Map supported US GAAP and IFRS facts into canonical financial measures.
- Select one canonical fact when SEC data contains competing tags or filing
  revisions.
- Derive working capital, free cash flow, debt, EBIT, and EBITDA when compatible
  source facts are available.

Company metadata retrieval is not currently connected to company persistence.
SEC financial observations may therefore be stored without a company ID.

## Persistence and coverage

The active SQLite layer can:

- Initialize provider, company, and financial-observation tables.
- Upsert and retrieve providers, companies, and financial observations.
- Retrieve observations for an exact reporting date or inclusive date range.
- Filter financial observations by measure.
- Load cached financial data before requesting SEC data.
- Detect temporal gaps, fetch SEC data once, upsert the result, and re-query the
  requested range.

Gap detection currently checks reporting-date coverage. A missing measure
inside an otherwise observed reporting period does not trigger another SEC
request.

## Financial metrics

The active metric calculator converts long-form `FinancialStatement`
observations into an ordered DataFrame with one row per reporting date. It
calculates:

- Liquidity: current ratio, quick ratio, cash ratio, and working capital to
  assets.
- Leverage and solvency: debt to assets, debt to equity, liabilities to assets,
  equity ratio, net debt to EBITDA, and interest coverage.
- Profitability: gross margin, operating margin, EBITDA margin, net margin,
  return on assets, and return on equity.
- Cash flow: operating cash-flow margin, free cash-flow margin, operating cash
  flow to net income, and free cash flow to debt.
- Distress input: retained earnings to assets.

Missing inputs and zero denominators produce null metrics rather than zero.

## Trend adjustment

The active trend method returns a flat dictionary containing one adjusted
value or `None` for every calculated metric.

- Only values present in the final snapshot are eligible for scoring output.
- A metric missing from the final snapshot remains `None`; an older value is
  not substituted.
- Intermediate gaps may be carried forward inside the trend history but do not
  increase the count of real observations.
- Fewer than three real observations leave the final value unchanged.
- Three through twenty real observations use the latest movement of EMA-smoothed
  levels: QoQ for quarterly statements and YoY for annual statements.
- More than twenty real observations use timestamp-aware linear-regression pace
  per reporting interval.
- Expected reporting grids tolerate ordinary fiscal-date drift and insert
  completely missing intermediate periods for internal carry-forward.
- Contextual metrics remain at their final observed value rather than receiving
  a directional adjustment.
- Adjustments are limited by `INVESTMENT_PROFILE`: 10% for `CONSERVATIVE`, 15%
  for `MODERATE`, and 20% for `AGGRESSIVE`.

This output is ready to become input for company risk scoring, but the active
risk scorer does not exist yet.

## Available time-series helpers

Generic utilities exist for calendar-aligned DoD, MoM, QoQ, and YoY changes,
carry-forward provenance, periodic-grid alignment, exponential smoothing,
linear pace, and CAGR. Company adjustment currently selects QoQ for quarterly
statements and YoY for annual statements. DoD, MoM, and CAGR remain independent
utilities.

Realized volatility is not implemented.

## Not currently supported

The following `Intent` values exist in `graph/state.py`, but none is currently
executable through the active agent workflow:

- Company overview
- Company risk analysis
- Company trend analysis
- Company comparison
- Macroeconomic conditions analysis
- Full risk overview
- Unsupported-request routing

The active architecture also does not yet provide:

- Company risk scores or score confidence
- Macroeconomic retrieval or scoring
- FRED integration beyond its configured provider record
- Bond or credit-market data
- Sector-relative Bayesian analysis
- An active planner, researcher, or LLM writer
- A compiled LangGraph workflow
- A user-facing application entry point
