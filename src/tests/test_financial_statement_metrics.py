import sys
from pathlib import Path
from pprint import pprint
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.tools.sec_tool import SECTool
from src.tools.financial_statement_metrics import FinancialStatementMetrics

RAW_METRICS_TO_PRINT = [
    "revenue",
    "gross_profit",
    "operating_income",
    "net_income",
    "assets",
    "liabilities",
    "equity",
    "current_assets",
    "current_liabilities",
    "cash",
    "debt",
    "long_term_debt",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "ebit",
]

CALCULATED_METRICS_TO_PRINT = [
    "current_ratio",
    "quick_ratio",
    "cash_ratio",
    "debt_to_equity",
    "debt_to_assets",
    "liabilities_to_assets",
    "interest_coverage",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "return_on_assets",
    "return_on_equity",
    "operating_cash_flow_margin",
    "free_cash_flow",
    "free_cash_flow_margin",
    "asset_turnover",
    "debt_to_capital",
    "cash_to_assets",
]

EXPECTED_CALCULATED_CATEGORIES = [
    "liquidity_metrics",
    "leverage_metrics",
    "profitability_metrics",
    "cash_flow_metrics",
    "efficiency_metrics",
    "capital_structure_metrics",
]

def flatten_calculated_metrics(
    calculated_metrics: dict,
) -> dict:
    flat_metrics = {}

    for category_metrics in calculated_metrics.values():
        if not isinstance(category_metrics, dict):
            continue

        for metric_name, value in category_metrics.items():
            flat_metrics[metric_name] = value

    return flat_metrics

def print_selected_raw_metrics(
    raw_metrics: dict,
) -> None:
    for metric_name in RAW_METRICS_TO_PRINT:
        print(f"{metric_name}: {raw_metrics.get(metric_name)}")

def print_selected_calculated_metrics(
    calculated_metrics: dict,
) -> None:
    flat_metrics = flatten_calculated_metrics(calculated_metrics)

    for metric_name in CALCULATED_METRICS_TO_PRINT:
        print(f"{metric_name}: {flat_metrics.get(metric_name)}")

def print_trend_examples(
    period_metrics: dict,
) -> None:
    raw_trends = period_metrics.get("raw_financial_statement_metric_trends", {})
    calculated_trends = period_metrics.get(
        "calculated_financial_metric_trends",
        {},
    )

    print("\nRaw financial statement trend examples:")
    for metric_name in [
        "revenue",
        "net_income",
        "operating_income",
        "assets",
        "liabilities",
        "equity",
        "debt",
        "operating_cash_flow",
    ]:
        print(metric_name)
        pprint(raw_trends.get(metric_name))

    print("\nCalculated financial metric trend examples:")
    for metric_name in [
        "current_ratio",
        "debt_to_equity",
        "debt_to_assets",
        "net_margin",
        "return_on_assets",
        "return_on_equity",
        "free_cash_flow",
        "free_cash_flow_margin",
    ]:
        print(metric_name)
        pprint(calculated_trends.get(metric_name))

def assert_snapshot_shape(
    snapshot_metrics: dict,
    ticker: str,
) -> None:
    assert snapshot_metrics.get("ticker") == ticker
    assert snapshot_metrics.get("company_name") is not None

    assert isinstance(snapshot_metrics.get("selected_period"), dict)
    assert snapshot_metrics["selected_period"].get("end_date") is not None

    assert isinstance(
        snapshot_metrics.get("raw_financial_statement_metrics"),
        dict,
    )
    assert isinstance(
        snapshot_metrics.get("calculated_financial_metrics"),
        dict,
    )
    assert isinstance(snapshot_metrics.get("diagnostics"), dict)

    calculated_metrics = snapshot_metrics["calculated_financial_metrics"]

    for category in EXPECTED_CALCULATED_CATEGORIES:
        assert category in calculated_metrics
        assert isinstance(calculated_metrics[category], dict)

    assert "current_ratio" in calculated_metrics["liquidity_metrics"]
    assert "working_capital" in calculated_metrics["liquidity_metrics"]

    assert "debt_to_equity" in calculated_metrics["leverage_metrics"]
    assert "debt_to_assets" in calculated_metrics["leverage_metrics"]
    assert "interest_coverage" in calculated_metrics["leverage_metrics"]

    assert "net_margin" in calculated_metrics["profitability_metrics"]
    assert "return_on_assets" in calculated_metrics["profitability_metrics"]
    assert "return_on_equity" in calculated_metrics["profitability_metrics"]

    assert "free_cash_flow" in calculated_metrics["cash_flow_metrics"]
    assert "free_cash_flow_margin" in calculated_metrics["cash_flow_metrics"]

    assert "asset_turnover" in calculated_metrics["efficiency_metrics"]

    assert "debt_to_capital" in calculated_metrics["capital_structure_metrics"]
    assert "cash_to_assets" in calculated_metrics["capital_structure_metrics"]

def assert_period_shape(
    period_metrics: dict,
    ticker: str,
    comparison_method: str,
) -> None:
    assert period_metrics.get("ticker") == ticker
    assert period_metrics.get("company_name") is not None
    assert period_metrics.get("comparison_method") == comparison_method

    assert period_metrics.get("period_count") > 0
    assert isinstance(period_metrics.get("periods"), list)
    assert isinstance(period_metrics.get("latest_period"), dict)

    assert isinstance(
        period_metrics.get("raw_financial_statement_metric_trends"),
        dict,
    )
    assert isinstance(
        period_metrics.get("calculated_financial_metric_trends"),
        dict,
    )
    assert isinstance(period_metrics.get("growth_metrics"), dict)
    assert isinstance(period_metrics.get("diagnostics"), dict)

    raw_trends = period_metrics["raw_financial_statement_metric_trends"]
    calculated_trends = period_metrics["calculated_financial_metric_trends"]

    assert "revenue" in raw_trends
    assert "net_income" in raw_trends

    assert "current_ratio" in calculated_trends
    assert "debt_to_equity" in calculated_trends
    assert "net_margin" in calculated_trends

def test_financial_statement_metrics():
    print("\nRetrieving SEC company data...")

    sec_tool = SECTool()
    ticker = "AAPL"

    company_data = sec_tool.get_company_data(
        ticker=ticker,
        start_date="2020-01-01",
        end_date="2024-12-31",
        refresh=True,
    )

    print("\nSEC company data response:")
    pprint(
        {
            "ticker": company_data.get("ticker"),
            "company_name": company_data.get("company_name"),
            "cik": company_data.get("cik"),
            "sic": company_data.get("sic"),
            "sic_description": company_data.get("sic_description"),
            "source": company_data.get("source"),
            "start_date": company_data.get("start_date"),
            "end_date": company_data.get("end_date"),
            "years_available": company_data.get("years_available"),
            "periods_available_count": len(
                company_data.get("periods_available", [])
            ),
            "financial_rows_count": len(company_data.get("financials", [])),
            "missing_years": company_data.get("missing_years"),
            "missing_core_metrics": company_data.get("missing_core_metrics"),
            "errors": company_data.get("errors"),
        }
    )

    assert company_data.get("ticker") == ticker
    assert company_data.get("company_name") is not None
    assert isinstance(company_data.get("financials"), list)
    assert len(company_data.get("financials", [])) > 0

    metrics_calculator = FinancialStatementMetrics()

    print("\nCalculating financial statement snapshot metrics...")

    snapshot_metrics = metrics_calculator.calculate_snapshot(
        company_data=company_data,
        as_of_date="2024-12-31",
    )

    print("\nSnapshot company metadata:")
    pprint(
        {
            "ticker": snapshot_metrics.get("ticker"),
            "company_name": snapshot_metrics.get("company_name"),
            "cik": snapshot_metrics.get("cik"),
            "sic": snapshot_metrics.get("sic"),
            "sic_description": snapshot_metrics.get("sic_description"),
            "as_of_date": snapshot_metrics.get("as_of_date"),
        }
    )

    print("\nSnapshot selected period:")
    pprint(snapshot_metrics.get("selected_period"))

    print("\nSnapshot raw financial statement metrics:")
    print_selected_raw_metrics(
        snapshot_metrics.get("raw_financial_statement_metrics", {})
    )

    print("\nSnapshot calculated financial metrics:")
    print_selected_calculated_metrics(
        snapshot_metrics.get("calculated_financial_metrics", {})
    )

    print("\nSnapshot diagnostics:")
    pprint(snapshot_metrics.get("diagnostics"))

    assert_snapshot_shape(
        snapshot_metrics=snapshot_metrics,
        ticker=ticker,
    )

    print("\nTesting calculate_metrics alias...")

    alias_snapshot_metrics = metrics_calculator.calculate_metrics(
        company_data=company_data,
        as_of_date="2024-12-31",
    )

    assert_snapshot_shape(
        snapshot_metrics=alias_snapshot_metrics,
        ticker=ticker,
    )

    print("\nCalculating financial statement period metrics with linear trend...")

    period_metrics_linear = metrics_calculator.calculate_period(
        company_data=company_data,
        start_date="2020-01-01",
        end_date="2024-12-31",
        comparison_method="linear_trend",
    )

    print("\nLinear trend period metrics summary:")
    pprint(
        {
            "ticker": period_metrics_linear.get("ticker"),
            "company_name": period_metrics_linear.get("company_name"),
            "start_date": period_metrics_linear.get("start_date"),
            "end_date": period_metrics_linear.get("end_date"),
            "comparison_method": period_metrics_linear.get("comparison_method"),
            "period_count": period_metrics_linear.get("period_count"),
        }
    )

    print("\nLatest period:")
    pprint(period_metrics_linear.get("latest_period", {}).get("period"))

    print("\nAvailable periods:")
    for period_snapshot in period_metrics_linear.get("periods", []):
        pprint(period_snapshot.get("period"))

    print_trend_examples(period_metrics_linear)

    assert_period_shape(
        period_metrics=period_metrics_linear,
        ticker=ticker,
        comparison_method="linear_trend",
    )

    revenue_linear_trend = period_metrics_linear[
        "raw_financial_statement_metric_trends"
    ]["revenue"]

    assert isinstance(revenue_linear_trend, dict)
    assert "linear_trend" in revenue_linear_trend
    assert "first_to_last_change" in revenue_linear_trend

    print("\nCalculating financial statement period metrics with period-over-period changes...")

    period_metrics_pop = metrics_calculator.calculate_period(
        company_data=company_data,
        start_date="2020-01-01",
        end_date="2024-12-31",
        comparison_method="period_over_period",
    )

    print_trend_examples(period_metrics_pop)

    assert_period_shape(
        period_metrics=period_metrics_pop,
        ticker=ticker,
        comparison_method="period_over_period",
    )

    revenue_pop_trends = period_metrics_pop[
        "raw_financial_statement_metric_trends"
    ]["revenue"]

    current_ratio_pop_trends = period_metrics_pop[
        "calculated_financial_metric_trends"
    ]["current_ratio"]

    assert isinstance(revenue_pop_trends, list)
    assert isinstance(current_ratio_pop_trends, list)

    if revenue_pop_trends:
        assert "date" in revenue_pop_trends[0]
        assert "previous_date" in revenue_pop_trends[0]
        assert "absolute_change" in revenue_pop_trends[0]
        assert "percentage_change" in revenue_pop_trends[0]
        assert "frequency" in revenue_pop_trends[0]

    print("\nCalculating financial statement period metrics with YoY changes...")

    period_metrics_yoy = metrics_calculator.calculate_period(
        company_data=company_data,
        start_date="2020-01-01",
        end_date="2024-12-31",
        comparison_method="yoy",
    )

    print_trend_examples(period_metrics_yoy)

    assert_period_shape(
        period_metrics=period_metrics_yoy,
        ticker=ticker,
        comparison_method="yoy",
    )

    revenue_yoy_trend = period_metrics_yoy[
        "raw_financial_statement_metric_trends"
    ]["revenue"]

    current_ratio_yoy_trend = period_metrics_yoy[
        "calculated_financial_metric_trends"
    ]["current_ratio"]

    assert isinstance(revenue_yoy_trend, dict)
    assert isinstance(current_ratio_yoy_trend, dict)

    assert "comparison_type" in revenue_yoy_trend
    assert "date" in revenue_yoy_trend
    assert "previous_date" in revenue_yoy_trend
    assert "absolute_change" in revenue_yoy_trend
    assert "percentage_change" in revenue_yoy_trend

    print("\nCalculating financial statement period metrics with quarter-over-quarter changes...")

    period_metrics_qoq = metrics_calculator.calculate_period(
        company_data=company_data,
        start_date="2020-01-01",
        end_date="2024-12-31",
        comparison_method="quarter_over_quarter",
    )

    print_trend_examples(period_metrics_qoq)

    assert_period_shape(
        period_metrics=period_metrics_qoq,
        ticker=ticker,
        comparison_method="quarter_over_quarter",
    )

    revenue_qoq_trend = period_metrics_qoq[
        "raw_financial_statement_metric_trends"
    ]["revenue"]

    current_ratio_qoq_trend = period_metrics_qoq[
        "calculated_financial_metric_trends"
    ]["current_ratio"]

    assert isinstance(revenue_qoq_trend, dict)
    assert isinstance(current_ratio_qoq_trend, dict)

    assert "comparison_type" in revenue_qoq_trend
    assert "date" in revenue_qoq_trend
    assert "previous_date" in revenue_qoq_trend
    assert "absolute_change" in revenue_qoq_trend
    assert "percentage_change" in revenue_qoq_trend

    print("\nFinancial statement metrics test completed successfully.")

if __name__ == "__main__":
    test_financial_statement_metrics()