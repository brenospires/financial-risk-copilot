# MVP implementation roadmap

This roadmap covers the company financial-data workflow through financial
statement metric and trend calculation. Company risk scoring, macroeconomic
risk scoring, and LLM-based risk analysis are intentionally out of scope for
this phase.

## Priority 1: isolate financial-statement sources and units

- [ ] Add `provider_id` to financial-statement period queries so cached results
  cannot mix observations from different providers.
- [ ] Define and implement the repository/service unit-selection contract:
  either query one explicit unit or return separated unit series, but never
  combine units implicitly.
- [ ] Bind `FinancialStatementService` reads to the configured provider before
  checking temporal coverage and after provider upserts.
- [ ] Validate that fetched observations match the requested provider, ticker,
  market, frequency, date range, and selected unit before persistence.
- [ ] Add repository and service tests with the same ticker and frequency stored
  under multiple providers and units.

## 1. Confirm the workflow contracts

- [ ] Keep the planner output aligned with the supported intents in
  `graph/state.py` and the actions in `docs/supported_actions.md`.
- [ ] Define the planner date contract with `date` values and an explicit
  `TimeSeriesFrequency`; do not infer monthly financial statements because the
  SEC provider currently supports quarterly and annual observations.
- [ ] Define the researcher output per ticker as
  `list[FinancialStatement]`, returned by the selected provider.
- [ ] Keep provider retrieval separate from metric calculation, persistence,
  risk scoring, and written analysis.
- [ ] Keep the approved snapshot output contract as one combined wide
  `DataFrame` containing raw measures and calculated metrics. Define the trend
  output contract separately before implementing trends.

## 2. Connect provider retrieval to the workflow

- [ ] Update the researcher path to call the provider's
  `fetch_financial_statements(...)` method for every planned ticker.
- [ ] Pass ticker, market, frequency, start date, and end date explicitly.
- [ ] Store each ticker's `list[FinancialStatement]` without converting models
  back to provider-specific payloads.
- [ ] Treat an empty provider result as valid missing data for that ticker and
  record a diagnostic instead of failing the whole multi-company request.
- [ ] Isolate provider exceptions per ticker so one failed retrieval does not
  discard successful results for other tickers.

## 3. Implement financial snapshot calculation

- [ ] Replace the legacy provider-dictionary parsing in
  `src/tools/financial_statement_metrics.py` with an input contract based on
  `list[FinancialStatement]`.
- [ ] Keep `calculate_snapshots(statements)` restricted to
  `list[FinancialStatement]` input and return one wide row for each reporting
  period represented in the input.
- [ ] Use the generic time-series pivot to index rows by provider, ticker,
  market, unit, frequency, and end date. Represent each
  `FinancialStatementMeasure` as a column. Do not use SEC fiscal labels as row
  identity because comparative facts may inherit a later filing's context.
- [ ] Validate that observations combined in one snapshot have compatible
  units. Do not calculate a ratio from incompatible monetary units.
- [ ] Keep the public input provider-neutral and model-based; keep the generic
  pivot dictionary-based so it can support future financial and macro models.
- [ ] Raise `ValueError` for an empty statement list because it has no company
  or reporting context.
- [ ] Represent unavailable raw measures and calculated metrics as `pd.NA`
  while preserving every expected column. Never substitute zero for a missing
  observation.
- [ ] Include missing required measures and calculation errors in per-period
  diagnostics while preserving every period that can still produce useful
  metrics.
- [ ] Keep one private method per financial metric, supported by small shared
  helpers such as safe numeric division. Each method must return `None` when a
  required input is missing or its denominator is zero.

### First snapshot metrics

Implement only metrics whose inputs exist in `FinancialStatementMeasure`:

- [ ] Liquidity: `current_ratio`, `quick_ratio`, `cash_ratio`, and
  `working_capital_to_assets`.
- [ ] Leverage and solvency: `debt_to_assets`, `debt_to_equity`,
  `liabilities_to_assets`, `equity_ratio`, `net_debt_to_ebitda`, and
  `interest_coverage`.
- [ ] Profitability: `gross_margin`, `operating_margin`, `ebitda_margin`,
  `net_margin`, `return_on_assets`, and `return_on_equity`.
- [ ] Cash flow: `operating_cash_flow_margin`, `free_cash_flow_margin`,
  `operating_cash_flow_to_net_income`, and `free_cash_flow_to_debt`.
- [ ] Distress inputs: `retained_earnings_to_assets` and
  `working_capital_to_assets`.

Use these definitions consistently:

- `quick_ratio = (current_assets - inventory) / current_liabilities`
- `equity_ratio = equity / assets`
- `net_debt_to_ebitda = (debt - cash) / ebitda`
- `interest_coverage = ebit / abs(interest_expense)`

Do not implement `altman_style_risk_proxy`, flags, rankings, composite scores,
or risk levels in the metrics class. Those belong to the later company-risk
scoring phase and require separately approved definitions.

## 4. Implement financial trend calculation

- [x] Add `adjust_metrics_for_trend(snapshots)` and keep it independent from
  provider retrieval.
  retrieval.
- [x] Calculate trends separately by ticker and frequency; never mix annual
  and quarterly snapshots in one series.
- [ ] Sort observations chronologically and preserve fiscal-period metadata.
- [ ] Calculate raw-measure growth for revenue, net income, EBITDA, free cash
  flow, and debt.
- [ ] Calculate trends for the implemented margins, leverage ratios, and
  liquidity ratios rather than creating opaque aggregate trend scores.
- [ ] Support period-over-period changes and frequency-aware comparisons:
  quarter-over-quarter for quarterly data and year-over-year for matching
  fiscal periods.
- [ ] Add one-year change, CAGR, trend slope, volatility, maximum
  deterioration, and consecutive deterioration only when the required number
  of observations exists; otherwise return `None` with a diagnostic.
- [x] Define deterioration direction per metric because an increase is adverse
  for some measures, such as leverage, but favorable for others, such as
  interest coverage.
- [ ] Keep generic time-series helpers separate from the private methods that
  expose each named trend metric.

## 5. Integrate calculated metrics into graph state

- [ ] Replace the current broad `company_metrics` payload with an agreed shape
  that stores, per ticker, the statement list or most recent statement data,
  calculated snapshots, calculated trends, and diagnostics.
- [ ] Update planner, researcher, and computation nodes only after the payload
  contract is approved.
- [ ] Ensure the most recent complete snapshot can be selected without hiding
  newer incomplete periods; pass both the selected result and its missing-data
  diagnostics to downstream stages.
- [ ] Stop this implementation phase after company financial metrics and trends
  are available in graph state.

## 6. Add targeted tests

- [ ] Test every private metric method independently with complete inputs,
  missing inputs, zero denominators, negative values, and sign-normalized
  interest expense.
- [ ] Test snapshot grouping across multiple periods, tickers, and frequencies.
- [ ] Test partially populated periods and entirely empty statement lists.
- [ ] Test incompatible units and ensure no cross-unit ratio is produced.
- [ ] Test quarterly QoQ and YoY alignment, annual growth, unordered inputs,
  missing intermediate periods, and insufficient history.
- [ ] Test that one provider or ticker failure does not suppress other ticker
  results.
- [ ] Run tests only after explicit user approval and from the activated
  `financial-risk-copilot` conda environment.

## Performance guidance

`list[FinancialStatement]` remains the provider boundary. Convert it once from
long-form observations into a wide nullable `DataFrame`, then calculate each
metric with vectorized `Series` operations. Do not use row-wise `DataFrame.apply`
for formulas that pandas can evaluate column-wise. This structure also supports
later rolling averages, exponential smoothing, volatility, and other trend
calculations without changing the provider contract.

## Future Bayesian sector-relative financial risk model

Preserve this model as a future product direction after deterministic company
metrics and initial risk scoring are implemented.

### Purpose and assumption

The model assumes that companies within the same sector share common financial
behavior. Sector-level observations define prior distributions for financial
metrics such as EBITDA margin, leverage, liquidity, and cash-flow generation.
These priors represent the expected behavior and variation of comparable
companies before considering the target company's latest evidence.

When financial data is observed for a specific company, use that company's own
metrics as evidence and combine them with the appropriate sector prior. The
resulting posterior distribution estimates the company's expected financial
behavior while accounting for both peer information and company-specific data.
The hierarchical structure should allow partial pooling: companies with sparse
history receive more support from the sector prior, while companies with richer
history are influenced more strongly by their own observations.

### Risk-analysis outputs

For each modeled metric, use the posterior distribution to estimate:

- whether the company is above or below its sector expectation;
- the magnitude of its deviation from comparable companies;
- its approximate percentile within the sector distribution;
- the probability that its performance is weaker than its sector peers;
- posterior uncertainty or credible intervals around every estimate; and
- changes in relative position that may indicate improvement or deterioration.

For example, an EBITDA-margin model should estimate whether the target company
is above or below the sector average, its approximate sector percentile, and
the posterior probability that its profitability is weaker than that of
comparable companies.

### Product boundary

This is a fundamental financial-risk and relative-quality model. It should help
identify financial strength, weakness, unusual behavior, deterioration risk,
and sector-relative financial quality. It must not be presented as a valuation
model and does not determine whether a company's stock is cheap or expensive.

### Future implementation work

- [ ] Define sector taxonomy, peer eligibility, and minimum peer sample sizes.
- [ ] Select metrics whose definitions are comparable across providers,
  currencies, accounting standards, company sizes, and reporting frequencies.
- [ ] Define transformations and robust likelihoods for bounded, skewed,
  negative, or outlier-prone financial ratios.
- [ ] Design hierarchical sector priors and company-level posterior updates.
- [ ] Define how time weighting and deterioration trends enter the model.
- [ ] Cache sector priors with data lineage, sample-period metadata, model
  version, and refresh rules.
- [ ] Validate posterior calibration, credible-interval coverage, percentile
  stability, and behavior for companies with sparse data.
- [ ] Expose sector-relative estimates and uncertainty to the risk-scoring and
  writer stages without collapsing uncertainty into unsupported certainty.

## Later phases

- Add company financial-risk scoring from snapshots and trends.
- Add macroeconomic time-series support using shared grouping keys.
- Add macroeconomic risk scoring and combine it with company risk context.
- Implement the Bayesian sector-relative model described above.
