# Risk Analysis Framework

This document defines the financial measures, calculated metrics, risk
signals, and outputs used by the company-risk analysis actions.

## Supported actions

- `company_risk_analysis`
- `company_comparison`
- `company_trend_analysis`
- `company_overview`
- `full_risk_overview`

## Financial statement measures

- Assets
- Current assets
- Cash
- Inventory
- Accounts receivable
- Liabilities
- Current liabilities
- Debt
- Long-term debt
- Accounts payable
- Equity
- Retained earnings
- Working capital
- Revenue
- Gross profit
- Operating income
- Net income
- EBIT
- EBITDA
- Interest expense
- Operating cash flow
- Capital expenditures
- Free cash flow

## Liquidity metrics

- `current_ratio = current_assets / current_liabilities`
- `quick_ratio = (current_assets - inventory) / current_liabilities`
- `cash_ratio = cash / current_liabilities`
- `working_capital = current_assets - current_liabilities`
- `working_capital_to_assets = working_capital / assets`
- `operating_cash_flow_to_current_liabilities = operating_cash_flow / current_liabilities`

## Leverage and solvency metrics

- `debt_to_assets = debt / assets`
- `liabilities_to_assets = liabilities / assets`
- `debt_to_equity = debt / equity`
- `long_term_debt_to_total_debt = long_term_debt / debt`
- `equity_ratio = equity / assets`
- `net_debt = debt - cash`
- `net_debt_to_ebitda = net_debt / ebitda`
- `debt_to_ebitda = debt / ebitda`
- `interest_coverage = ebit / interest_expense`

## Profitability metrics

- `gross_margin = gross_profit / revenue`
- `operating_margin = operating_income / revenue`
- `ebit_margin = ebit / revenue`
- `ebitda_margin = ebitda / revenue`
- `net_margin = net_income / revenue`
- `return_on_assets = net_income / assets`
- `return_on_equity = net_income / equity`

## Cash-flow metrics

- `operating_cash_flow_margin = operating_cash_flow / revenue`
- `free_cash_flow_margin = free_cash_flow / revenue`
- `free_cash_flow_to_debt = free_cash_flow / debt`
- `operating_cash_flow_to_debt = operating_cash_flow / debt`
- `operating_cash_flow_to_net_income = operating_cash_flow / net_income`
- `capex_intensity = abs(capital_expenditures) / revenue`
- `free_cash_flow = operating_cash_flow - abs(capital_expenditures)`

`cash_conversion_quality` is an alias for
`operating_cash_flow_to_net_income`. `free_cash_flow_after_capex` is an alias
for the calculated free-cash-flow value and must not subtract capital
expenditures twice.

## Distress proxy metrics

- `retained_earnings_to_assets = retained_earnings / assets`
- `ebit_to_assets = ebit / assets`
- `working_capital_to_assets = working_capital / assets`
- `revenue_to_assets = revenue / assets`
- `equity_to_liabilities = equity / liabilities`
- `altman_style_risk_proxy`

## Efficiency metrics

- `asset_turnover = revenue / assets`
- `inventory_turnover = (revenue - gross_profit) / inventory`
- `receivables_turnover = revenue / accounts_receivable`
- `payables_turnover = (revenue - gross_profit) / accounts_payable`

## Trend metrics

Growth:

- Revenue
- Gross profit
- Operating income
- EBITDA
- EBIT
- Net income
- Operating cash flow
- Free cash flow
- Assets
- Debt
- Equity

Margin, leverage, liquidity, and cash-flow trends:

- Gross, operating, EBITDA, EBIT, net, FCF, and OCF margin trends
- Debt-to-assets, debt-to-equity, liabilities-to-assets, net-debt-to-EBITDA,
  interest-coverage, and equity-ratio trends
- Current, quick, cash, working-capital, working-capital-to-assets, and
  OCF-to-current-liabilities trends
- OCF growth versus net-income growth
- FCF growth versus net-income growth
- Cash-conversion-quality and capex-intensity trends
- Negative FCF periods

Stability and summary calculations:

- Revenue, net-income, EBITDA, OCF, FCF, margin, and debt-growth volatility
- One-year change
- Three-year CAGR
- Five-year CAGR
- Rolling average
- Trend slope
- Maximum deterioration from the previous period
- Consecutive periods of deterioration

## Comparison metrics

- Raw scale: revenue, assets, equity, debt, cash, EBITDA, net income, OCF, FCF
- Profitability, balance-sheet, cash-generation, and efficiency metrics
- Peer percentile rank
- Peer-group z-score
- Risk rank
- Best- and worst-metric flags
- Composite-risk-score difference

## Overview risk flags

- Negative net income, OCF, or FCF
- Current ratio below 1
- Debt greater than equity
- Interest coverage below 2
- High net-debt-to-EBITDA
- Declining revenue or margins
- Rising leverage

## Full risk overview

The full assessment combines these pillars:

- Liquidity risk
- Solvency risk
- Profitability risk
- Cash-flow quality
- Efficiency
- Trend risk
- Distress risk

Final outputs:

- `risk_score`
- `risk_level`
- `main_risk_drivers`
- `main_positive_factors`
- `deteriorating_metrics`
- `improving_metrics`
- `suggested_areas_for_user_attention`

Risk levels defined by the framework:

- `very_low_risk`
- `low_risk`
- `moderate_risk`
- `high_risk`
- `very_high_risk`

## First implementation

The MVP calculation layer should prioritize:

- `current_ratio`
- `quick_ratio`
- `cash_ratio`
- `debt_to_assets`
- `debt_to_equity`
- `liabilities_to_assets`
- `equity_ratio`
- `net_debt_to_ebitda`
- `interest_coverage`
- `gross_margin`
- `operating_margin`
- `ebitda_margin`
- `net_margin`
- `return_on_assets`
- `return_on_equity`
- `operating_cash_flow_margin`
- `free_cash_flow_margin`
- `operating_cash_flow_to_net_income`
- `free_cash_flow_to_debt`
- `working_capital_to_assets`
- `retained_earnings_to_assets`
- `revenue_growth`
- `net_income_growth`
- `ebitda_growth`
- `free_cash_flow_growth`
- `debt_growth`
- `margin_trend`
- `leverage_trend`
- `liquidity_trend`

Metrics must be calculated only when their required measures are available.
Risk scores must expose reduced confidence when missing data affects their
inputs.
