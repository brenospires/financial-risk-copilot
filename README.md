# Financial Risk Copilot

Financial Risk Copilot is a local agentic system for assessing company financial risk. It combines company financial statements, calculated risk metrics, and macroeconomic context to produce grounded analytical responses.

The project is designed as a portfolio MVP: small enough to run locally, explicit enough to review, and structured so additional markets and data providers can be added without rewriting the analysis layer.

> This project is under active development and does not provide investment advice.

## Intended Use

Financial Risk Copilot is intended for personal, low-frequency analysis on a local machine. A typical user may already have a company or bond portfolio, review existing positions periodically, and occasionally investigate a new company before making an allocation decision.

The expected workload is small: a few requests per month, repeated analysis of a limited set of companies, and periodic data refreshes. SQLite persistence exists to avoid unnecessary external API calls and make repeated analysis faster; it is not intended to support high-volume or real-time workloads.

The project also has an explicit study and portfolio purpose. It demonstrates:

- Agentic workflow design with LangGraph
- Separation between planning, retrieval, persistence, calculation, and writing
- Provider-specific normalization into canonical financial data
- Financial ratio, trend, and risk-score development
- Missing-data and confidence-aware analytical design
- Local language-model execution with Ollama
- Iterative architecture and test-driven development of a financial application

## Intended Analysis

The copilot is being built to support:

- Company overview
- Company risk analysis
- Company trend analysis
- Company comparison
- Macroeconomic conditions analysis
- Full risk overview

These actions are represented by the `Intent` type in `graph/state.py` and documented in `docs/supported_actions.md`.

## Core Design

```text
User query
    ↓
Planner selects intent, ticker, market, period, and data requirements
    ↓
Research layer retrieves cached data and fills missing coverage
    ↓
Provider-specific responses become canonical data models
    ↓
Financial metrics and time-series trends are calculated
    ↓
Company and macroeconomic risk signals are combined
    ↓
Writer produces a grounded risk assessment
```

The application keeps retrieval, persistence, calculations, and agent orchestration separate. Provider implementations do not calculate risk metrics, repositories do not call external APIs, and workflow nodes do not contain low-level numerical logic.

## Provider-Agnostic Financial Statements

Different providers describe the same accounting concept with different field names. SEC filings add another layer of variation because companies may use US GAAP or IFRS taxonomies and may select different valid XBRL tags for the same concept.

The SEC provider addresses this with a candidate mapping:

```python
FinancialStatementMeasure.REVENUE: (
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
    ("us-gaap", "Revenues"),
    ("us-gaap", "SalesRevenueNet"),
    ("ifrs-full", "Revenue"),
)
```

Provider-specific facts are mapped into canonical measures such as:

- Assets, liabilities, cash, debt, and equity
- Revenue, gross profit, operating income, and net income
- EBIT, EBITDA, and interest expense
- Operating cash flow, capital expenditures, and free cash flow

The rest of the project consumes `FinancialStatement` models rather than SEC tag names. This keeps metric formulas independent from the selected provider and creates a clear extension point for providers outside the United States.

Some measures cannot be trusted as universal direct facts. Debt, working capital, EBIT, EBITDA, and free cash flow may require controlled derivation from available statement values. Missing values remain explicit when they cannot be safely retrieved or derived.

## Time-Series Strategy

Retrieval and persistence use typed observations:

```python
list[FinancialStatement]
```

The calculation layer will convert these observations into an ordered pandas DataFrame, pivot measures into columns, and calculate ratios and trends with vectorized operations. This preserves a clean domain boundary without sacrificing performance.

The intended cache workflow is:

1. Retrieve the requested period from SQLite.
2. Detect missing observations inside the requested period.
3. Make the smallest practical number of provider requests.
4. Upsert observed provider data.
5. Re-query the completed dataset.
6. Apply clearly flagged fallback logic only when gaps remain.

Imputed values must remain distinguishable from provider observations, and analytical output should report the percentage of data affected by fallback handling.

## Data Sources

- [SEC EDGAR](https://www.sec.gov/edgar) for company metadata and financial statements
- [FRED](https://fred.stlouisfed.org/) for macroeconomic indicators

SEC coverage is limited to entities that file with the SEC. This includes US issuers and some foreign private issuers, but not arbitrary companies listed on every global exchange. Foreign SEC filers may report with IFRS, which requires different taxonomy mappings from US GAAP.

Bond pricing, yield, duration, and maturity data require a separate provider and are outside the current retrieval implementation.

## Current Status

Implemented:

- Canonical company, provider, and financial-statement models
- SQLite repositories and cold-start table initialization
- Provider-domain interfaces for company and financial-statement retrieval
- Shared ticker normalization
- SEC HTTP foundation, ticker-to-CIK resolution, response caching, and company retrieval
- US GAAP and IFRS candidate mappings for financial-statement measures
- Unit and repository tests for the new data and persistence layers

In progress:

- SEC fact extraction, period classification, and deduplication
- Derived financial-statement measures
- Database-first ingestion coordination
- Vectorized financial metric and trend calculations
- Migration of the FRED and risk-scoring layers
- LangGraph workflow integration
- Streamlit interface

The `src/` directory contains the previous working implementation and remains a migration reference while the new flat architecture is completed.

## Project Structure

```text
financial-risk-copilot/
├── agents/                         # Future agent implementations
├── config/
│   └── settings.py                 # Environment and runtime configuration
├── data/                           # Local SQLite cache
├── data_models/
│   ├── company.py
│   ├── data_domain.py
│   ├── data_provider.py
│   ├── financial_statement.py
│   ├── financial_statement_measure.py
│   ├── observation_type.py
│   └── time_series_frequency.py
├── database/
│   ├── base_repository.py
│   ├── company_repository.py
│   ├── data_provider_repository.py
│   ├── financial_statement_repository.py
│   └── initialize.py
├── docs/
│   ├── supported_actions.md
│   └── TODO.md
├── graph/
│   ├── nodes.py
│   └── state.py
├── src/                             # Legacy implementation being migrated
├── tests/
│   ├── data_models/
│   └── databases/
├── tools/
│   ├── analysis/                    # Financial metrics and risk calculations
│   ├── data_domains_retrieval/      # Provider interface contracts
│   └── data_providers/              # SEC and future provider implementations
├── utils/
│   └── identifiers.py
├── .env.example
├── requirements.txt
└── README.md
```

## Technology

- Python
- LangGraph and LangChain
- Ollama for local language-model execution
- Pydantic for canonical data models
- SQLite for local caching
- pandas and NumPy for numerical and time-series calculations
- Requests, SEC EDGAR, and FRED
- Streamlit planned for the local interface

## Local Configuration

Create a local environment file:

```bash
cp .env.example .env
```

Configure your provider credentials and identification:

```dotenv
FRED_API_KEY=your_fred_api_key
SEC_USER_AGENT="financial-risk-copilot your_email@example.com"
SEC_REQUEST_DELAY_SECONDS=0.2
SEC_REQUEST_TIMEOUT_SECONDS=30
```

Never commit `.env` or the generated SQLite database.

## Database Initialization

Run commands from the project root in the `financial-risk-copilot` conda environment:

```bash
conda activate financial-risk-copilot
python -c "from database.initialize import initialize_database; initialize_database()"
```

The database is a disposable local cache. It is not an audit log and may be recreated as schemas evolve during MVP development.

## Tests

Run targeted tests from the project root:

```bash
conda activate financial-risk-copilot
python -m unittest discover -s tests/data_models -p 'test_*.py' -v
python -m unittest discover -s tests/databases -p 'test_*.py' -v
```

Network-dependent provider tests should be run separately from deterministic unit and repository tests.

Run SEC tests explicitly:

```bash
python tests/data_providers/test_sec.py
python tests/data_providers/test_sec_provider.py
python tests/data_providers/test_sec_coverage.py
```

The coverage diagnostic compares quarterly SEC data for ten companies over
2023–2024, then repeats the best-covered quarter as a single-date request. It
reports coverage by company and measure without writing to SQLite. Live SEC
facts may be revised, so exact counts can change while the comparison method
remains reproducible.

## Scope and Limitations

- The project is intended for local, low-frequency personal analysis.
- It is a portfolio demonstration, not a production risk platform.
- It does not currently recommend portfolio allocations.
- Data availability varies by provider, company, taxonomy, and reporting frequency.
- Calculated scores must expose reduced confidence when required inputs are unavailable.
- Generated analysis must not be treated as financial or investment advice.

### Intentional Limitations

The following capabilities are intentionally excluded from the MVP rather than accidentally overlooked:

- **Audit history:** The database does not preserve every filing revision or historical version of an observation. A newer canonical provider value may update the existing record.
- **Usage logging:** The application does not record user sessions, generated reports, or historical recommendations for later consistency audits.
- **Multi-user operation:** There is no authentication, authorization, tenant isolation, or concurrent-user design.
- **Production resilience:** The project does not target uptime guarantees, distributed processing, automatic failover, or enterprise monitoring.
- **High-frequency analysis:** It does not support trading infrastructure, streaming market data, intraday signals, or real-time portfolio monitoring.
- **Regulatory compliance:** It is not designed as a regulated credit-rating, advisory, accounting, or compliance system.
- **Complete global coverage:** SEC and FRED are the initial providers. Companies without compatible provider coverage may not be analyzable.
- **Accounting reconciliation:** The application normalizes the measures required for risk analysis; it does not reproduce or reconcile complete audited financial statements.
- **Automatic allocation decisions:** Risk assessments provide analytical context, not instructions to buy, sell, or size portfolio positions.

These choices keep the implementation aligned with its real use case: a lightweight local copilot and a focused demonstration of financial-data and agentic-system design.

## License

MIT
