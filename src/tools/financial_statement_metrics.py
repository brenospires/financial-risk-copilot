
import sys
from pathlib import Path
from typing import Any, Optional
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.tools.metrics_utils import MetricsUtils

class FinancialStatementMetrics(MetricsUtils):
    """
    Calculates company-level financial statement metrics from normalized
    financial statement dictionaries.

    Expected primary input:
        Dictionary returned by SECTool.get_company_data(...)

    Important design rules:
    - This class does not receive SECTool, FREDTool, repositories, APIs, or DBs.
    - This class does not retrieve or persist data.
    - Financial statement data is passed into method calls, not __init__.
    - Shared utilities come from MetricsUtils.
    - This class does not calculate company risk scores, macro risk scores,
      market metrics, bond metrics, written reports, or recommendations.
    """

    RAW_FINANCIAL_STATEMENT_METRICS: tuple[str, ...] = (
        "revenue",
        "net_income",
        "operating_income",
        "gross_profit",
        "interest_expense",
        "assets",
        "current_assets",
        "liabilities",
        "current_liabilities",
        "equity",
        "cash",
        "inventory",
        "accounts_receivable",
        "accounts_payable",
        "retained_earnings",
        "working_capital",
        "debt",
        "long_term_debt",
        "operating_cash_flow",
        "capital_expenditures",
        "free_cash_flow",
        "ebit",
        "shares_outstanding",
    )

    CORE_SNAPSHOT_METRICS: tuple[str, ...] = (
        "assets",
        "liabilities",
        "equity",
        "revenue",
        "net_income",
        "current_assets",
        "current_liabilities",
        "cash",
        "debt",
        "operating_income",
        "interest_expense",
        "operating_cash_flow",
        "capital_expenditures",
        "retained_earnings",
        "working_capital",
        "ebit",
    )

    FINANCIAL_ROWS_KEYS: tuple[str, ...] = (
        "financials",
        "financial_statements",
        "financial_statement_metrics",
        "metrics",
        "data",
        "rows",
    )

    METRIC_NAME_KEYS: tuple[str, ...] = (
        "metric_name",
        "name",
        "field",
        "canonical_name",
    )

    VALUE_KEYS: tuple[str, ...] = (
        "value",
        "amount",
        "numeric_value",
    )

    DATE_KEYS: tuple[str, ...] = (
        "end_date",
        "date",
        "period_end_date",
    )

    VALID_COMPARISON_METHODS: tuple[str, ...] = (
        "linear_trend",
        "period_over_period",
        "yoy",
        "quarter_over_quarter",
    )

    def calculate_metrics(
        self,
        company_data: dict[str, Any],
        as_of_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        User-facing convenience method.

        Intended usage:
            metrics_calculator = FinancialStatementMetrics()
            fin_metrics = metrics_calculator.calculate_metrics(company_data)

        This currently returns the latest available snapshot up to as_of_date.
        """

        return self.calculate_snapshot(
            company_data=company_data,
            as_of_date=as_of_date,
        )

    def calculate_snapshot(
        self,
        company_data: dict[str, Any],
        as_of_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Calculate financial statement metrics for the latest available reporting
        period up to as_of_date.

        This method intentionally uses one reporting period at a time instead
        of mixing latest values from different periods.
        """

        financial_rows = self._extract_financial_rows(company_data)
                
        normalized_rows = self._normalize_financial_rows(financial_rows)
        normalized_rows = self._deduplicate_normalized_rows(normalized_rows)
    
        latest_period_rows = self._select_latest_period_rows(
            rows=normalized_rows,
            as_of_date=as_of_date,
        )

        raw_values = self._build_metric_value_map(latest_period_rows)

        calculated_metrics = self.calculate_metrics_for_period(raw_values)

        period_metadata = self._get_period_metadata(latest_period_rows)

        available_raw_metrics = self._calculate_available_keys(raw_values)
        missing_core_metrics = self._calculate_missing_keys(
            values=raw_values,
            required_keys=list(self.CORE_SNAPSHOT_METRICS),
        )

        return {
            "ticker": company_data.get("ticker"),
            "company_name": company_data.get("company_name"),
            "cik": company_data.get("cik"),
            "sic": company_data.get("sic"),
            "sic_description": company_data.get("sic_description"),
            "as_of_date": as_of_date,
            "selected_period": period_metadata,
            "raw_financial_statement_metrics": raw_values,
            "calculated_financial_metrics": calculated_metrics,
            "diagnostics": {
                "source": company_data.get("source"),
                "rows_received": len(financial_rows),
                "rows_used_in_selected_period": len(latest_period_rows),
                "available_raw_metrics": available_raw_metrics,
                "missing_core_metrics": missing_core_metrics,
                "missing_provider_core_metrics": company_data.get(
                    "missing_core_metrics",
                    [],
                ),
                "missing_years": company_data.get("missing_years", []),
                "errors": company_data.get("errors", []),
            },
        }

    def calculate_period(
        self,
        company_data: dict[str, Any],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        comparison_method: str = "linear_trend",
    ) -> dict[str, Any]:
        """
        Calculate financial statement metrics across a date window.

        Supported comparison methods:
        - linear_trend
        - period_over_period
        - yoy
        - quarter_over_quarter
        """

        if comparison_method not in self.VALID_COMPARISON_METHODS:
            raise ValueError(
                f"Invalid comparison_method: {comparison_method}. "
                f"Expected one of: {list(self.VALID_COMPARISON_METHODS)}"
            )

        financial_rows = self._extract_financial_rows(company_data)
        
        normalized_rows = self._normalize_financial_rows(financial_rows)
        normalized_rows = self._deduplicate_normalized_rows(normalized_rows)

        filtered_rows = self._filter_by_date(
            rows=normalized_rows,
            date_key="date",
            start_date=start_date,
            end_date=end_date,
        )

        period_snapshots = self._build_period_snapshots(filtered_rows)

        raw_metric_series = self._build_raw_metric_series(filtered_rows)
        calculated_metric_series = self._build_calculated_metric_series(
            period_snapshots,
        )

        raw_metric_comparisons = self._compare_metric_series(
            series_by_metric=raw_metric_series,
            comparison_method=comparison_method,
        )

        calculated_metric_comparisons = self._compare_metric_series(
            series_by_metric=calculated_metric_series,
            comparison_method=comparison_method,
        )

        latest_period = period_snapshots[-1] if period_snapshots else None

        return {
            "ticker": company_data.get("ticker"),
            "company_name": company_data.get("company_name"),
            "start_date": start_date,
            "end_date": end_date,
            "comparison_method": comparison_method,
            "period_count": len(period_snapshots),
            "latest_period": latest_period,
            "periods": period_snapshots,
            "raw_financial_statement_metric_trends": raw_metric_comparisons,
            "calculated_financial_metric_trends": calculated_metric_comparisons,
            "growth_metrics": self._calculate_growth_metrics(
                raw_metric_series=raw_metric_series,
                calculated_metric_series=calculated_metric_series,
            ),
            "diagnostics": {
                "source": company_data.get("source"),
                "rows_received": len(financial_rows),
                "rows_used": len(filtered_rows),
                "missing_provider_core_metrics": company_data.get(
                    "missing_core_metrics",
                    [],
                ),
                "missing_years": company_data.get("missing_years", []),
                "errors": company_data.get("errors", []),
            },
        }

    def calculate_metrics_for_period(
        self,
        metrics: dict[str, Any],
    ) -> dict[str, dict[str, Optional[float]]]:
        """
        Calculate financial statement ratios and derived indicators from one
        reporting-period metric dictionary.

        Expected input example:
            {
                "revenue": 391035000000,
                "net_income": 93736000000,
                "assets": 364980000000,
                ...
            }

        The parameter is called metrics because it is the calculated-input map
        for this method, but it represents raw financial statement values.
        """

        revenue = self._safe_float(metrics.get("revenue"))
        net_income = self._safe_float(metrics.get("net_income"))
        operating_income = self._safe_float(metrics.get("operating_income"))
        gross_profit = self._safe_float(metrics.get("gross_profit"))
        interest_expense = self._safe_float(metrics.get("interest_expense"))

        assets = self._safe_float(metrics.get("assets"))
        current_assets = self._safe_float(metrics.get("current_assets"))
        liabilities = self._safe_float(metrics.get("liabilities"))
        current_liabilities = self._safe_float(metrics.get("current_liabilities"))
        equity = self._safe_float(metrics.get("equity"))
        cash = self._safe_float(metrics.get("cash"))
        inventory = self._safe_float(metrics.get("inventory"))
        accounts_receivable = self._safe_float(metrics.get("accounts_receivable"))
        accounts_payable = self._safe_float(metrics.get("accounts_payable"))
        retained_earnings = self._safe_float(metrics.get("retained_earnings"))
        working_capital = self._safe_float(metrics.get("working_capital"))

        debt = self._safe_float(metrics.get("debt"))
        long_term_debt = self._safe_float(metrics.get("long_term_debt"))

        operating_cash_flow = self._safe_float(metrics.get("operating_cash_flow"))
        capital_expenditures = self._safe_float(metrics.get("capital_expenditures"))
        free_cash_flow = self._safe_float(metrics.get("free_cash_flow"))

        ebit = self._safe_float(metrics.get("ebit"))

        if working_capital is None:
            working_capital = self._calculate_working_capital(
                current_assets=current_assets,
                current_liabilities=current_liabilities,
            )

        capital_expenditures_outflow = self._calculate_capex_outflow(
            capital_expenditures=capital_expenditures,
        )

        if free_cash_flow is None:
            free_cash_flow = self._calculate_free_cash_flow(
                operating_cash_flow=operating_cash_flow,
                capital_expenditures_outflow=capital_expenditures_outflow,
            )

        net_debt = self._calculate_net_debt(
            debt=debt,
            cash=cash,
        )

        total_capital = self._calculate_total_capital(
            debt=debt,
            equity=equity,
        )

        long_term_capital = self._calculate_total_capital(
            debt=long_term_debt,
            equity=equity,
        )

        cost_of_goods_sold = self._calculate_cost_of_goods_sold(
            revenue=revenue,
            gross_profit=gross_profit,
        )

        interest_expense_abs = self._absolute_value(interest_expense)

        return {
            "liquidity_metrics": {
                "current_ratio": self._safe_divide(
                    current_assets,
                    current_liabilities,
                ),
                "quick_ratio": self._safe_divide(
                    self._sum_available([cash, accounts_receivable]),
                    current_liabilities,
                ),
                "cash_ratio": self._safe_divide(
                    cash,
                    current_liabilities,
                ),
                "working_capital": working_capital,
                "working_capital_to_assets": self._safe_divide(
                    working_capital,
                    assets,
                ),
                "working_capital_to_revenue": self._safe_divide(
                    working_capital,
                    revenue,
                ),
            },
            "leverage_metrics": {
                "debt_to_equity": self._safe_divide(
                    debt,
                    equity,
                ),
                "debt_to_assets": self._safe_divide(
                    debt,
                    assets,
                ),
                "liabilities_to_assets": self._safe_divide(
                    liabilities,
                    assets,
                ),
                "liabilities_to_equity": self._safe_divide(
                    liabilities,
                    equity,
                ),
                "long_term_debt_to_assets": self._safe_divide(
                    long_term_debt,
                    assets,
                ),
                "long_term_debt_to_equity": self._safe_divide(
                    long_term_debt,
                    equity,
                ),
                "net_debt": net_debt,
                "net_debt_to_ebit": self._safe_divide(
                    net_debt,
                    ebit,
                ),
                "debt_to_ebit": self._safe_divide(
                    debt,
                    ebit,
                ),
                "interest_coverage": self._safe_divide(
                    ebit or operating_income,
                    interest_expense_abs,
                ),
                "equity_multiplier": self._safe_divide(
                    assets,
                    equity,
                ),
            },
            "profitability_metrics": {
                "gross_margin": self._safe_divide(
                    gross_profit,
                    revenue,
                ),
                "operating_margin": self._safe_divide(
                    operating_income,
                    revenue,
                ),
                "ebit_margin": self._safe_divide(
                    ebit,
                    revenue,
                ),
                "net_margin": self._safe_divide(
                    net_income,
                    revenue,
                ),
                "return_on_assets": self._safe_divide(
                    net_income,
                    assets,
                ),
                "return_on_equity": self._safe_divide(
                    net_income,
                    equity,
                ),
                "return_on_capital": self._safe_divide(
                    ebit,
                    total_capital,
                ),
            },
            "cash_flow_metrics": {
                "operating_cash_flow": operating_cash_flow,
                "capital_expenditures_outflow": capital_expenditures_outflow,
                "free_cash_flow": free_cash_flow,
                "operating_cash_flow_margin": self._safe_divide(
                    operating_cash_flow,
                    revenue,
                ),
                "free_cash_flow_margin": self._safe_divide(
                    free_cash_flow,
                    revenue,
                ),
                "operating_cash_flow_to_debt": self._safe_divide(
                    operating_cash_flow,
                    debt,
                ),
                "free_cash_flow_to_debt": self._safe_divide(
                    free_cash_flow,
                    debt,
                ),
                "cash_flow_return_on_assets": self._safe_divide(
                    operating_cash_flow,
                    assets,
                ),
                "capex_to_revenue": self._safe_divide(
                    capital_expenditures_outflow,
                    revenue,
                ),
                "capex_to_operating_cash_flow": self._safe_divide(
                    capital_expenditures_outflow,
                    operating_cash_flow,
                ),
            },
            "efficiency_metrics": {
                "asset_turnover": self._safe_divide(
                    revenue,
                    assets,
                ),
                "current_asset_turnover": self._safe_divide(
                    revenue,
                    current_assets,
                ),
                "receivables_turnover": self._safe_divide(
                    revenue,
                    accounts_receivable,
                ),
                "inventory_turnover": self._safe_divide(
                    cost_of_goods_sold,
                    inventory,
                ),
                "payables_turnover": self._safe_divide(
                    cost_of_goods_sold,
                    accounts_payable,
                ),
                "revenue_to_inventory": self._safe_divide(
                    revenue,
                    inventory,
                ),
            },
            "capital_structure_metrics": {
                "total_capital": total_capital,
                "long_term_capital": long_term_capital,
                "debt_to_capital": self._safe_divide(
                    debt,
                    total_capital,
                ),
                "long_term_debt_to_capital": self._safe_divide(
                    long_term_debt,
                    long_term_capital,
                ),
                "equity_to_capital": self._safe_divide(
                    equity,
                    total_capital,
                ),
                "cash_to_assets": self._safe_divide(
                    cash,
                    assets,
                ),
                "cash_to_debt": self._safe_divide(
                    cash,
                    debt,
                ),
                "retained_earnings_to_assets": self._safe_divide(
                    retained_earnings,
                    assets,
                ),
            },
        }

    def _extract_financial_rows(
        self,
        company_data: Any,
    ) -> list[dict[str, Any]]:
        """
        Extract financial statement rows from a provider dictionary.

        Current SECTool shape:
            company_data["financials"]

        Future providers may use another key, so this method checks a small set
        of common alternatives.
        """

        if isinstance(company_data, list):
            return [
                row
                for row in company_data
                if isinstance(row, dict)
            ]

        if not isinstance(company_data, dict):
            return []

        for key in self.FINANCIAL_ROWS_KEYS:
            rows = company_data.get(key)

            if isinstance(rows, list):
                return [
                    row
                    for row in rows
                    if isinstance(row, dict)
                ]

        return []

    def _normalize_financial_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Normalize provider rows into an internal shape used only by this class.

        Important:
        SEC fiscal_year / fiscal_period can refer to the filing context. The same
        historical end_date may appear again in later filings as comparative data.
        Therefore, later methods must deduplicate normalized rows by metric and
        actual statement end date.
        """

        normalized_rows: list[dict[str, Any]] = []

        for row in rows:
            metric_name = self._get_first_available_value(
                row=row,
                keys=self.METRIC_NAME_KEYS,
            )

            value = self._get_first_available_value(
                row=row,
                keys=self.VALUE_KEYS,
            )

            row_date = self._get_first_available_value(
                row=row,
                keys=self.DATE_KEYS,
            )

            normalized_date = self._normalize_date(row_date)

            if metric_name is None:
                continue

            if normalized_date is None:
                continue

            normalized_rows.append(
                {
                    "metric_name": str(metric_name),
                    "value": self._safe_float(value),
                    "date": normalized_date,
                    "fiscal_year": self._safe_int(row.get("fiscal_year")),
                    "fiscal_period": row.get("fiscal_period"),
                    "form": row.get("form"),
                    "filed": row.get("filed"),
                    "unit": row.get("unit"),
                    "frame": row.get("frame"),
                    "sec_metric_name": row.get("sec_metric_name"),
                    "source_row": row,
                }
            )

        return normalized_rows

    def _select_latest_period_rows(
        self,
        rows: list[dict[str, Any]],
        as_of_date: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Select rows from the latest available reporting period up to as_of_date.

        This avoids mixing financial statement values from different dates in
        the same snapshot.
        """

        filtered_rows = self._filter_by_date(
            rows=rows,
            date_key="date",
            end_date=as_of_date,
        )

        period_groups = self._group_rows_by_period(filtered_rows)

        if not period_groups:
            return []

        sorted_period_keys = sorted(
            period_groups.keys(),
            key=lambda period_key: (
                self._parse_date(period_key[0]),
                self._safe_int(period_key[1]) or -1,
                str(period_key[2] or ""),
            ),
        )

        latest_period_key = sorted_period_keys[-1]

        return period_groups[latest_period_key]

    def _build_period_snapshots(
        self,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Build calculated metric snapshots for each available reporting period.
        """

        period_groups = self._group_rows_by_period(rows)

        sorted_period_keys = sorted(
            period_groups.keys(),
            key=lambda period_key: (
                self._parse_date(period_key[0]),
                self._safe_int(period_key[1]) or -1,
                str(period_key[2] or ""),
            ),
        )

        period_snapshots: list[dict[str, Any]] = []

        for period_key in sorted_period_keys:
            period_rows = period_groups[period_key]
            raw_values = self._build_metric_value_map(period_rows)
            calculated_metrics = self.calculate_metrics_for_period(raw_values)

            period_snapshots.append(
                {
                    "period": self._get_period_metadata(period_rows),
                    "raw_financial_statement_metrics": raw_values,
                    "calculated_financial_metrics": calculated_metrics,
                    "flat_calculated_financial_metrics": (
                        self._flatten_metric_categories(calculated_metrics)
                    ),
                }
            )

        return period_snapshots

    def _group_rows_by_period(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[tuple[Any, Any, Any], list[dict[str, Any]]]:
        """
        Group normalized rows by reporting period.
        """

        period_groups: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}

        for row in rows:
            period_key = (
                row.get("date"),
                row.get("fiscal_year"),
                row.get("fiscal_period"),
            )

            if period_key[0] is None:
                continue

            period_groups.setdefault(period_key, [])
            period_groups[period_key].append(row)

        return period_groups

    def _build_metric_value_map(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, Optional[float]]:
        """
        Build one metric_name -> value dictionary from rows in the same period.
        """

        metric_value_map: dict[str, Optional[float]] = {
            metric_name: None
            for metric_name in self.RAW_FINANCIAL_STATEMENT_METRICS
        }

        for row in rows:
            metric_name = row.get("metric_name")

            if metric_name is None:
                continue

            metric_value_map[str(metric_name)] = self._safe_float(
                row.get("value")
            )

        return metric_value_map

    def _build_raw_metric_series(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Build metric_name -> time series for raw financial statement values.

        Missing values are skipped because trend methods should compare available
        observations, not artificial None placeholders.
        """

        series_by_metric: dict[str, list[dict[str, Any]]] = {}

        for row in rows:
            metric_name = row.get("metric_name")
            value = self._safe_float(row.get("value"))

            if metric_name is None:
                continue

            if value is None:
                continue

            series_by_metric.setdefault(str(metric_name), [])
            series_by_metric[str(metric_name)].append(
                {
                    "date": row.get("date"),
                    "value": value,
                    "fiscal_year": row.get("fiscal_year"),
                    "fiscal_period": row.get("fiscal_period"),
                }
            )

        return series_by_metric

    def _build_calculated_metric_series(
        self,
        period_snapshots: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Build metric_name -> time series for calculated financial metrics.

        Missing calculated values are skipped because a ratio should only enter a
        trend calculation when its numerator and denominator are both available.
        """

        series_by_metric: dict[str, list[dict[str, Any]]] = {}

        for snapshot in period_snapshots:
            period = snapshot.get("period", {})
            flat_metrics = snapshot.get("flat_calculated_financial_metrics", {})

            for metric_name, value in flat_metrics.items():
                numeric_value = self._safe_float(value)

                if numeric_value is None:
                    continue

                series_by_metric.setdefault(metric_name, [])
                series_by_metric[metric_name].append(
                    {
                        "date": period.get("end_date"),
                        "value": numeric_value,
                        "fiscal_year": period.get("fiscal_year"),
                        "fiscal_period": period.get("fiscal_period"),
                    }
                )

        return series_by_metric

    def _compare_metric_series(
        self,
        series_by_metric: dict[str, list[dict[str, Any]]],
        comparison_method: str,
    ) -> dict[str, Any]:
        """
        Compare metric time series using the selected method.
        """

        comparisons: dict[str, Any] = {}

        for metric_name, rows in series_by_metric.items():
            if comparison_method == "linear_trend":
                comparisons[metric_name] = {
                    "linear_trend": self._calculate_linear_trend(
                        rows=rows,
                        value_key="value",
                        date_key="date",
                    ),
                    "first_to_last_change": (
                        self._calculate_first_to_last_change(
                            rows=rows,
                            value_key="value",
                            date_key="date",
                        )
                    ),
                }

            elif comparison_method == "period_over_period":
                comparisons[metric_name] = (
                    self._calculate_period_over_period_changes(
                        rows=rows,
                        value_key="value",
                        date_key="date",
                    )
                )

            elif comparison_method == "yoy":
                comparisons[metric_name] = self._calculate_year_over_year_change(
                    rows=rows,
                )

            elif comparison_method == "quarter_over_quarter":
                comparisons[metric_name] = (
                    self._calculate_quarter_over_quarter_change(
                        rows=rows,
                    )
                )

        return comparisons

    def _calculate_growth_metrics(
        self,
        raw_metric_series: dict[str, list[dict[str, Any]]],
        calculated_metric_series: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """
        Calculate first-to-last growth for important statement and ratio metrics.
        """

        raw_growth_metrics = (
            "revenue",
            "gross_profit",
            "operating_income",
            "net_income",
            "assets",
            "liabilities",
            "equity",
            "cash",
            "debt",
            "operating_cash_flow",
            "free_cash_flow",
            "ebit",
        )

        calculated_growth_metrics = (
            "gross_margin",
            "operating_margin",
            "net_margin",
            "return_on_assets",
            "return_on_equity",
            "current_ratio",
            "debt_to_equity",
            "debt_to_assets",
            "free_cash_flow_margin",
        )

        raw_growth = {}

        for metric_name in raw_growth_metrics:
            raw_growth[metric_name] = self._calculate_first_to_last_change(
                rows=raw_metric_series.get(metric_name, []),
                value_key="value",
                date_key="date",
            )

        calculated_growth = {}

        for metric_name in calculated_growth_metrics:
            calculated_growth[metric_name] = self._calculate_first_to_last_change(
                rows=calculated_metric_series.get(metric_name, []),
                value_key="value",
                date_key="date",
            )

        return {
            "raw_financial_statement_growth": raw_growth,
            "calculated_financial_metric_growth": calculated_growth,
        }

    def _calculate_year_over_year_change(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compare the latest available period with the same fiscal period in the
        previous fiscal year.
        """

        ordered_rows = self._sort_by_date(
            rows=rows,
            date_key="date",
        )

        valid_rows = [
            row
            for row in ordered_rows
            if row.get("fiscal_year") is not None
            and row.get("fiscal_period") is not None
        ]

        if len(valid_rows) < 2:
            return self._empty_comparison_result()

        current_row = valid_rows[-1]
        current_year = self._safe_int(current_row.get("fiscal_year"))
        current_period = current_row.get("fiscal_period")

        if current_year is None:
            return self._empty_comparison_result()

        previous_row = None

        for row in reversed(valid_rows[:-1]):
            row_year = self._safe_int(row.get("fiscal_year"))
            row_period = row.get("fiscal_period")

            if row_year == current_year - 1 and row_period == current_period:
                previous_row = row
                break

        if previous_row is None:
            return self._empty_comparison_result(
                current_row=current_row,
            )

        return self._build_comparison_result(
            previous_row=previous_row,
            current_row=current_row,
            comparison_type="yoy",
        )

    def _calculate_quarter_over_quarter_change(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compare the latest available quarter with the immediately previous
        quarter-like observation.
        """

        ordered_rows = self._sort_by_date(
            rows=rows,
            date_key="date",
        )

        quarter_rows = [
            row
            for row in ordered_rows
            if row.get("fiscal_period") in {"Q1", "Q2", "Q3", "Q4"}
        ]

        if len(quarter_rows) < 2:
            return self._empty_comparison_result()

        previous_row = quarter_rows[-2]
        current_row = quarter_rows[-1]

        return self._build_comparison_result(
            previous_row=previous_row,
            current_row=current_row,
            comparison_type="quarter_over_quarter",
        )

    def _build_comparison_result(
        self,
        previous_row: dict[str, Any],
        current_row: dict[str, Any],
        comparison_type: str,
    ) -> dict[str, Any]:
        """
        Build a standardized comparison result.
        """

        previous_value = self._safe_float(previous_row.get("value"))
        current_value = self._safe_float(current_row.get("value"))

        return {
            "comparison_type": comparison_type,
            "date": current_row.get("date"),
            "previous_date": previous_row.get("date"),
            "fiscal_year": current_row.get("fiscal_year"),
            "previous_fiscal_year": previous_row.get("fiscal_year"),
            "fiscal_period": current_row.get("fiscal_period"),
            "previous_fiscal_period": previous_row.get("fiscal_period"),
            "value": current_value,
            "previous_value": previous_value,
            "absolute_change": self._calculate_absolute_change(
                previous_value=previous_value,
                current_value=current_value,
            ),
            "percentage_change": self._calculate_period_change(
                previous_value=previous_value,
                current_value=current_value,
            ),
        }

    def _empty_comparison_result(
        self,
        current_row: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Return a stable empty comparison shape.
        """

        current_row = current_row or {}

        return {
            "comparison_type": None,
            "date": current_row.get("date"),
            "previous_date": None,
            "fiscal_year": current_row.get("fiscal_year"),
            "previous_fiscal_year": None,
            "fiscal_period": current_row.get("fiscal_period"),
            "previous_fiscal_period": None,
            "value": self._safe_float(current_row.get("value")),
            "previous_value": None,
            "absolute_change": None,
            "percentage_change": None,
        }

    def _get_period_metadata(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Extract reporting-period metadata from a group of rows.
        """

        if not rows:
            return {
                "end_date": None,
                "fiscal_year": None,
                "fiscal_period": None,
                "form": None,
            }

        first_row = rows[0]

        forms = sorted(
            {
                row.get("form")
                for row in rows
                if row.get("form") is not None
            }
        )

        return {
            "end_date": first_row.get("date"),
            "fiscal_year": first_row.get("fiscal_year"),
            "fiscal_period": first_row.get("fiscal_period"),
            "form": forms[0] if forms else first_row.get("form"),
        }

    def _flatten_metric_categories(
        self,
        calculated_metrics: dict[str, dict[str, Optional[float]]],
    ) -> dict[str, Optional[float]]:
        """
        Flatten categorized metrics into one dictionary.
        """

        flat_metrics: dict[str, Optional[float]] = {}

        for category_metrics in calculated_metrics.values():
            for metric_name, value in category_metrics.items():
                flat_metrics[metric_name] = value

        return flat_metrics

    def _get_first_available_value(
        self,
        row: dict[str, Any],
        keys: tuple[str, ...],
    ) -> Any:
        """
        Return the first non-missing value among candidate keys.
        """

        for key in keys:
            value = row.get(key)

            if value is not None:
                return value

        return None

    def _sum_available(
        self,
        values: list[Any],
    ) -> Optional[float]:
        """
        Sum available values only when at least one value is present.
        """

        numeric_values = [
            self._safe_float(value)
            for value in values
        ]

        numeric_values = [
            value
            for value in numeric_values
            if value is not None
        ]

        if not numeric_values:
            return None

        return sum(numeric_values)

    def _absolute_value(
        self,
        value: Any,
    ) -> Optional[float]:
        """
        Return absolute numeric value when available.
        """

        numeric_value = self._safe_float(value)

        if numeric_value is None:
            return None

        return abs(numeric_value)

    def _calculate_working_capital(
        self,
        current_assets: Optional[float],
        current_liabilities: Optional[float],
    ) -> Optional[float]:
        """
        Calculate working capital when the provider does not supply it.
        """

        current_assets = self._safe_float(current_assets)
        current_liabilities = self._safe_float(current_liabilities)

        if current_assets is None or current_liabilities is None:
            return None

        return current_assets - current_liabilities

    def _calculate_capex_outflow(
        self,
        capital_expenditures: Optional[float],
    ) -> Optional[float]:
        """
        Normalize capital expenditures as a positive cash outflow.

        SEC tags for payments to acquire property, plant, and equipment are
        often positive outflow amounts. Some providers may represent capex as
        negative cash flow. This method standardizes the magnitude.
        """

        capital_expenditures = self._safe_float(capital_expenditures)

        if capital_expenditures is None:
            return None

        return abs(capital_expenditures)

    def _calculate_free_cash_flow(
        self,
        operating_cash_flow: Optional[float],
        capital_expenditures_outflow: Optional[float],
    ) -> Optional[float]:
        """
        Calculate free cash flow when the provider does not supply it.
        """

        operating_cash_flow = self._safe_float(operating_cash_flow)
        capital_expenditures_outflow = self._safe_float(
            capital_expenditures_outflow,
        )

        if operating_cash_flow is None or capital_expenditures_outflow is None:
            return None

        return operating_cash_flow - capital_expenditures_outflow

    def _calculate_net_debt(
        self,
        debt: Optional[float],
        cash: Optional[float],
    ) -> Optional[float]:
        """
        Calculate net debt.
        """

        debt = self._safe_float(debt)
        cash = self._safe_float(cash)

        if debt is None or cash is None:
            return None

        return debt - cash

    def _calculate_total_capital(
        self,
        debt: Optional[float],
        equity: Optional[float],
    ) -> Optional[float]:
        """
        Calculate total capital as debt plus equity.
        """

        debt = self._safe_float(debt)
        equity = self._safe_float(equity)

        if debt is None or equity is None:
            return None

        return debt + equity

    def _calculate_cost_of_goods_sold(
        self,
        revenue: Optional[float],
        gross_profit: Optional[float],
    ) -> Optional[float]:
        """
        Approximate cost of goods sold when revenue and gross profit are
        available.
        """

        revenue = self._safe_float(revenue)
        gross_profit = self._safe_float(gross_profit)

        if revenue is None or gross_profit is None:
            return None

        return revenue - gross_profit
    
    def _deduplicate_normalized_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Deduplicate normalized financial statement rows.

        Provider data, especially SEC company facts, may include the same statement
        fact multiple times because later filings repeat prior-period comparative
        facts.

        We deduplicate by:
        - metric_name
        - actual statement end date

        This avoids false same-date period-over-period changes and prevents trend
        frequency from being incorrectly classified as daily.
        """

        best_rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}

        for row in rows:
            metric_name = row.get("metric_name")
            row_date = row.get("date")

            if metric_name is None or row_date is None:
                continue

            key = (
                str(metric_name),
                str(row_date),
            )

            existing_row = best_rows_by_key.get(key)

            if existing_row is None:
                best_rows_by_key[key] = row
                continue

            if self._is_better_financial_row(
                candidate_row=row,
                existing_row=existing_row,
            ):
                best_rows_by_key[key] = row

        deduplicated_rows = list(best_rows_by_key.values())

        return self._sort_by_date(
            rows=deduplicated_rows,
            date_key="date",
        )


    def _is_better_financial_row(
        self,
        candidate_row: dict[str, Any],
        existing_row: dict[str, Any],
    ) -> bool:
        """
        Decide which duplicated provider row to keep.

        Preference rules:
        1. Prefer rows with a non-null value.
        2. Prefer rows whose fiscal_year is plausible for the statement end date.
        3. Prefer FY over quarter when the same metric/date appears with both.
        4. Prefer later filed date.
        """

        candidate_value = self._safe_float(candidate_row.get("value"))
        existing_value = self._safe_float(existing_row.get("value"))

        if candidate_value is not None and existing_value is None:
            return True

        if candidate_value is None and existing_value is not None:
            return False

        candidate_plausible = self._has_plausible_fiscal_year(candidate_row)
        existing_plausible = self._has_plausible_fiscal_year(existing_row)

        if candidate_plausible and not existing_plausible:
            return True

        if not candidate_plausible and existing_plausible:
            return False

        candidate_period_score = self._financial_period_preference_score(
            candidate_row,
        )
        existing_period_score = self._financial_period_preference_score(
            existing_row,
        )

        if candidate_period_score > existing_period_score:
            return True

        if candidate_period_score < existing_period_score:
            return False

        candidate_filed = candidate_row.get("filed") or ""
        existing_filed = existing_row.get("filed") or ""

        return candidate_filed > existing_filed


    def _has_plausible_fiscal_year(
        self,
        row: dict[str, Any],
    ) -> bool:
        """
        Check whether fiscal_year is plausible relative to the actual statement
        end date.

        This is intentionally loose because companies may have non-calendar fiscal
        years. For example, a December 2024 quarter can be fiscal year 2025.

        But a 2024 statement date being labeled fiscal year 2026 is usually a
        repeated comparative fact from a later filing context, not the true period.
        """

        row_date = self._parse_date(row.get("date"))
        fiscal_year = self._safe_int(row.get("fiscal_year"))

        if row_date is None or fiscal_year is None:
            return True

        return abs(fiscal_year - row_date.year) <= 1


    def _financial_period_preference_score(
        self,
        row: dict[str, Any],
    ) -> int:
        """
        Score period labels when duplicated rows exist for the same metric/date.

        FY is preferred because annual facts are usually cleaner for default
        financial statement metrics. Quarterly rows remain available when there is
        no annual duplicate for that metric/date.
        """

        fiscal_period = row.get("fiscal_period")
        form = row.get("form")

        score = 0

        if fiscal_period == "FY":
            score += 20

        if form == "10-K":
            score += 10

        if fiscal_period in {"Q1", "Q2", "Q3", "Q4"}:
            score += 5

        if form == "10-Q":
            score += 3

        return score