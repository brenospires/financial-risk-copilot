"""Company financial-statement snapshot and trend metric calculations."""

import pandas as pd

from config.settings import INVESTMENT_PROFILE
from config.trend_analysis import (
    ALIGNMENT_TOLERANCE_DAYS_BY_FREQUENCY,
    EMA_ALPHA_BY_CATEGORY,
    METRIC_EMA_CATEGORY,
    MINIMUM_TREND_PERIODS,
    PERIOD_MONTHS_BY_FREQUENCY,
    TIMESERIES_LENGTH_THRESHOLD,
    TREND_CLIPPING_RANGE,
    get_trend_sensitivity,
)
from data_models.financial_statement import FinancialStatement
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.time_series_frequency import TimeSeriesFrequency
from utils.numeric import safe_divide
from utils.time_series import (
    calculate_exponential_trend,
    calculate_linear_trend,
    pivot_time_series,
    regularize_time_series,
)


class CompanyMetrics:
    """
    Calculate company metrics from canonical financial statements.

    The public snapshot method always receives ``list[FinancialStatement]``.
    It converts those long-form observations into one wide row per reporting
    end date, preserves every supported raw measure, and appends every
    calculated metric as a nullable column.

    Missing observations are expected. Calculations never substitute zero for
    missing data, and zero denominators produce ``pd.NA``. Provider retrieval,
    persistence, risk scoring, peer comparison, and written analysis remain
    outside this class. ``company_id`` may be absent because some providers may
    not resolve a persisted company record for every market.
    """

    GROUP_COLUMNS = (
        "provider_id",
        "ticker",
        "market",
        "unit",
        "frequency",
    )

    RAW_MEASURE_COLUMNS = tuple(
        measure.value
        for measure in FinancialStatementMeasure
    )

    METRIC_COLUMNS = (
        "cash_ratio",
        "net_margin",
        "quick_ratio",
        "equity_ratio",
        "gross_margin",
        "current_ratio",
        "ebitda_margin",
        "debt_to_assets",
        "debt_to_equity",
        "operating_margin",
        "return_on_assets",
        "return_on_equity",
        "interest_coverage",
        "net_debt_to_ebitda",
        "liabilities_to_assets",
        "free_cash_flow_margin",
        "free_cash_flow_to_debt",
        "working_capital_to_assets",
        "operating_cash_flow_margin",
        "retained_earnings_to_assets",
        "operating_cash_flow_to_net_income",
    )

    METRIC_RISK_DIRECTION = {
        "higher_better": {
            "cash_ratio",
            "net_margin",
            "quick_ratio",
            "equity_ratio",
            "gross_margin",
            "current_ratio",
            "ebitda_margin",
            "return_on_assets",
            "return_on_equity",
            "interest_coverage",
            "free_cash_flow_margin",
            "free_cash_flow_to_debt",
            "operating_cash_flow_margin",
            "working_capital_to_assets",
            "retained_earnings_to_assets",
        },
        "lower_better": {
            "debt_to_assets",
            "debt_to_equity",
            "liabilities_to_assets",
            "net_debt_to_ebitda",
        },
        "contextual": {
            "operating_cash_flow_to_net_income",
        },
    }

    POSITIVE_DENOMINATOR_BY_METRIC = {
        "cash_ratio": "current_liabilities",
        "net_margin": "revenue",
        "quick_ratio": "current_liabilities",
        "gross_margin": "revenue",
        "current_ratio": "current_liabilities",
        "ebitda_margin": "revenue",
        "debt_to_equity": "equity",
        "operating_margin": "revenue",
        "return_on_equity": "equity",
        "net_debt_to_ebitda": "ebitda",
        "free_cash_flow_margin": "revenue",
        "free_cash_flow_to_debt": "debt",
        "operating_cash_flow_margin": "revenue",
        "operating_cash_flow_to_net_income": "net_income",
    }

    def calculate_snapshots(
        self,
        statements: list[FinancialStatement],
    ) -> pd.DataFrame:
        """
        Calculate one wide financial metric row per reporting period.

        The input must contain at least one statement and describe one provider,
        ticker, market, unit, and reporting frequency. Fiscal labels are not
        part of row identity because comparative SEC facts may carry a later
        filing's fiscal context. Missing measures remain nullable cells.
        Duplicate canonical observations are rejected by the shared time-series
        pivot instead of being aggregated silently.
        """

        self._validate_statements(statements)

        records = [
            statement.model_dump(mode="json")
            for statement in statements
        ]
        result = pivot_time_series(
            records,
            values="value",
            columns="measure",
            timestamp="end_date",
            group_columns=self.GROUP_COLUMNS,
            expected_columns=self.RAW_MEASURE_COLUMNS,
        )

        result["cash_ratio"] = self._calculate_cash_ratio(
            result["cash"],
            result["current_liabilities"],
        )
        result["net_margin"] = self._calculate_net_margin(
            result["net_income"],
            result["revenue"],
        )
        result["quick_ratio"] = self._calculate_quick_ratio(
            result["current_assets"],
            result["inventory"],
            result["current_liabilities"],
        )
        result["equity_ratio"] = self._calculate_equity_ratio(
            result["equity"],
            result["assets"],
        )
        result["gross_margin"] = self._calculate_gross_margin(
            result["gross_profit"],
            result["revenue"],
        )
        result["current_ratio"] = self._calculate_current_ratio(
            result["current_assets"],
            result["current_liabilities"],
        )
        result["ebitda_margin"] = self._calculate_ebitda_margin(
            result["ebitda"],
            result["revenue"],
        )
        result["debt_to_assets"] = self._calculate_debt_to_assets(
            result["debt"],
            result["assets"],
        )
        result["debt_to_equity"] = self._calculate_debt_to_equity(
            result["debt"],
            result["equity"],
        )
        result["operating_margin"] = self._calculate_operating_margin(
            result["operating_income"],
            result["revenue"],
        )
        result["return_on_assets"] = self._calculate_return_on_assets(
            result["net_income"],
            result["assets"],
        )
        result["return_on_equity"] = self._calculate_return_on_equity(
            result["net_income"],
            result["equity"],
        )
        result["interest_coverage"] = self._calculate_interest_coverage(
            result["ebit"],
            result["interest_expense"],
        )
        result["net_debt_to_ebitda"] = self._calculate_net_debt_to_ebitda(
            result["debt"],
            result["cash"],
            result["ebitda"],
        )
        result["liabilities_to_assets"] = (
            self._calculate_liabilities_to_assets(
                result["liabilities"],
                result["assets"],
            )
        )
        result["free_cash_flow_margin"] = (
            self._calculate_free_cash_flow_margin(
                result["free_cash_flow"],
                result["revenue"],
            )
        )
        result["free_cash_flow_to_debt"] = (
            self._calculate_free_cash_flow_to_debt(
                result["free_cash_flow"],
                result["debt"],
            )
        )
        result["working_capital_to_assets"] = (
            self._calculate_working_capital_to_assets(
                result["working_capital"],
                result["assets"],
            )
        )
        result["operating_cash_flow_margin"] = (
            self._calculate_operating_cash_flow_margin(
                result["operating_cash_flow"],
                result["revenue"],
            )
        )
        result["retained_earnings_to_assets"] = (
            self._calculate_retained_earnings_to_assets(
                result["retained_earnings"],
                result["assets"],
            )
        )
        result["operating_cash_flow_to_net_income"] = (
            self._calculate_operating_cash_flow_to_net_income(
                result["operating_cash_flow"],
                result["net_income"],
            )
        )

        return self._sort_snapshots_by_date(result)

    def adjust_metrics_for_trend(
        self,
        snapshots: pd.DataFrame,
    ) -> dict[str, float | None]:
        """
        Return the latest metric values adjusted by their historical trajectories.

        Each metric must exist in the final chronological snapshot. Series with
        fewer than three real observations return that value unchanged. Shorter
        series use exponential smoothing, while series longer than the configured
        threshold use timestamp-aware linear regression. Missing final metrics
        remain ``None`` and conditional ratios are unavailable when their final
        denominator is non-positive.
        """

        if snapshots.empty:
            raise ValueError("Snapshots DataFrame is empty")

        frequency = self._get_snapshot_frequency(snapshots)
        missing_columns = sorted(set(self.METRIC_COLUMNS) - set(snapshots.columns))
        if missing_columns:
            missing_names = ", ".join(missing_columns)
            raise ValueError(f"Missing snapshot metric columns: {missing_names}")

        ordered = self._sort_snapshots_by_date(snapshots)
        sensitivity = get_trend_sensitivity(INVESTMENT_PROFILE)
        adjusted_metrics: dict[str, float | None] = {}
        for metric_name in self.METRIC_COLUMNS:
            metric_series = self._as_datetime_series(
                ordered[metric_name],
                ordered,
            )
            latest_index = metric_series.index[-1]
            latest_observation = metric_series.iloc[-1]
            if pd.isna(latest_observation):
                adjusted_metrics[metric_name] = None
                continue

            latest_value = float(latest_observation)
            if not self._is_interpretable_metric(
                metric_name,
                latest_index,
                ordered,
            ):
                adjusted_metrics[metric_name] = None
                continue

            regularized = regularize_time_series(
                metric_series,
                months_per_period=PERIOD_MONTHS_BY_FREQUENCY[frequency.value],
                tolerance_days=(
                    ALIGNMENT_TOLERANCE_DAYS_BY_FREQUENCY[frequency.value]
                ),
            )
            observed_count = int(regularized["is_observed"].sum())
            trend_series = regularized["value"].dropna()
            trend = self._calculate_metric_pace(
                metric_name,
                trend_series,
                observed_count,
                frequency,
            )
            if trend is None:
                adjusted_metrics[metric_name] = latest_value
                continue

            scale = abs(latest_value)
            adjusted_metrics[metric_name] = self._adjust_metric_value(
                metric_name=metric_name,
                current_value=latest_value,
                normalized_pace=trend,
                scale=scale,
                sensitivity=sensitivity,
            )

        return adjusted_metrics

    def _calculate_metric_pace(
        self,
        metric_name: str,
        series: pd.Series,
        observed_count: int,
        frequency: TimeSeriesFrequency,
    ) -> float | None:
        """Calculate one normalized metric pace per reporting period."""

        if observed_count < MINIMUM_TREND_PERIODS:
            return None

        if observed_count <= TIMESERIES_LENGTH_THRESHOLD:
            category = METRIC_EMA_CATEGORY.get(
                metric_name,
                "medium",
            )
            alpha = EMA_ALPHA_BY_CATEGORY[category]
            comparison_period = (
                "qoq"
                if frequency is TimeSeriesFrequency.QUARTERLY
                else "yoy"
            )
            return calculate_exponential_trend(
                series,
                alpha=alpha,
                period=comparison_period,
            )

        return calculate_linear_trend(series)

    def _adjust_metric_value(
        self,
        metric_name: str,
        current_value: float,
        normalized_pace: float,
        scale: float,
        sensitivity: float,
    ) -> float:
        """Adjust a metric while preserving its financially interpreted movement."""

        direction = self._get_metric_risk_direction(metric_name)
        if direction == "contextual":
            return current_value

        minimum_pace, maximum_pace = TREND_CLIPPING_RANGE
        clipped_pace = min(
            maximum_pace,
            max(minimum_pace, normalized_pace),
        )
        financial_pace = (
            clipped_pace
            if direction == "higher_better"
            else -clipped_pace
        )
        if financial_pace >= 0:
            adjustment_sign = 1.0 if direction == "higher_better" else -1.0
        else:
            adjustment_sign = -1.0 if direction == "higher_better" else 1.0

        adjustment = (
            scale
            * abs(financial_pace)
            * adjustment_sign
            * sensitivity
        )
        return float(current_value + adjustment)

    def _get_metric_risk_direction(self, metric_name: str) -> str:
        """Return the configured financial interpretation for one metric."""

        for direction, metric_names in self.METRIC_RISK_DIRECTION.items():
            if metric_name in metric_names:
                return direction

        raise ValueError(f"Missing risk direction for metric: {metric_name}")

    def _is_interpretable_metric(
        self,
        metric_name: str,
        latest_index: pd.Timestamp,
        snapshots: pd.DataFrame,
    ) -> bool:
        """Return whether the latest metric has a meaningful denominator."""

        denominator_name = self.POSITIVE_DENOMINATOR_BY_METRIC.get(metric_name)
        if denominator_name is None:
            return True

        denominator_series = self._as_datetime_series(
            snapshots[denominator_name],
            snapshots,
        )
        denominator = denominator_series.get(latest_index)
        return bool(pd.notna(denominator) and denominator > 0)

    def _as_datetime_series(
        self,
        series: pd.Series,
        snapshots: pd.DataFrame,
    ) -> pd.Series:
        """Return a metric series indexed only by its reporting timestamp."""

        result = series.copy()
        result.index = self._get_snapshot_dates(snapshots)
        return result.sort_index()

    def _sort_snapshots_by_date(
        self,
        snapshots: pd.DataFrame,
    ) -> pd.DataFrame:
        """Return snapshots ordered explicitly by reporting timestamp."""

        timestamps = self._get_snapshot_dates(snapshots)
        positions = sorted(
            range(len(snapshots)),
            key=timestamps.__getitem__,
        )

        return snapshots.iloc[positions]

    def _get_snapshot_dates(
        self,
        snapshots: pd.DataFrame,
    ) -> pd.DatetimeIndex:
        """Validate and return normalized reporting timestamps."""

        if isinstance(snapshots.index, pd.MultiIndex):
            if "end_date" not in snapshots.index.names:
                raise ValueError("Snapshot index must include end_date")

            if "frequency" in snapshots.index.names:
                frequencies = set(
                    snapshots.index.get_level_values("frequency")
                )
                if len(frequencies) != 1:
                    raise ValueError("Snapshots must use one frequency")

            timestamp_values = snapshots.index.get_level_values("end_date")
        elif isinstance(snapshots.index, pd.DatetimeIndex):
            timestamp_values = snapshots.index
        else:
            raise ValueError("Snapshots must use a datetime index")

        timestamps = pd.to_datetime(
            timestamp_values,
            errors="raise",
            utc=True,
        ).tz_localize(None)

        if timestamps.has_duplicates:
            raise ValueError("Snapshot reporting timestamps must be unique")

        return timestamps

    def _get_snapshot_frequency(
        self,
        snapshots: pd.DataFrame,
    ) -> TimeSeriesFrequency:
        """Validate and return the single snapshot reporting frequency."""

        if not isinstance(snapshots.index, pd.MultiIndex):
            raise ValueError("Snapshot index must include frequency")

        if "frequency" not in snapshots.index.names:
            raise ValueError("Snapshot index must include frequency")

        frequencies = set(
            snapshots.index.get_level_values("frequency")
        )
        if len(frequencies) != 1:
            raise ValueError("Snapshots must use one frequency")

        return TimeSeriesFrequency(next(iter(frequencies)))

    def _validate_statements(
        self,
        statements: list[FinancialStatement],
    ) -> None:
        """Validate the company and reporting context of statement inputs."""

        if not statements:
            raise ValueError("Financial statements are required")

        providers = {statement.provider_id for statement in statements}
        frequencies = {statement.frequency for statement in statements}
        tickers = {statement.ticker for statement in statements}
        markets = {statement.market.casefold() for statement in statements}
        units = {statement.unit.casefold() for statement in statements}

        contexts = (
            (providers, "provider"),
            (tickers, "ticker"),
            (markets, "market"),
            (units, "unit"),
            (frequencies, "frequency"),
        )

        for values, name in contexts:
            if len(values) > 1:
                raise ValueError(
                    f"Financial statements must use one {name}"
                )

    def _calculate_cash_ratio(
        self,
        cash: pd.Series,
        current_liabilities: pd.Series,
    ) -> pd.Series:
        """Calculate cash divided by current liabilities."""

        return safe_divide(cash, current_liabilities)

    def _calculate_net_margin(
        self,
        net_income: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate net income divided by revenue."""

        return safe_divide(net_income, revenue)

    def _calculate_quick_ratio(
        self,
        current_assets: pd.Series,
        inventory: pd.Series,
        current_liabilities: pd.Series,
    ) -> pd.Series:
        """Calculate inventory-adjusted assets over current liabilities."""

        return safe_divide(
            current_assets - inventory,
            current_liabilities,
        )

    def _calculate_equity_ratio(
        self,
        equity: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate equity divided by total assets."""

        return safe_divide(equity, assets)

    def _calculate_gross_margin(
        self,
        gross_profit: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate gross profit divided by revenue."""

        return safe_divide(gross_profit, revenue)

    def _calculate_current_ratio(
        self,
        current_assets: pd.Series,
        current_liabilities: pd.Series,
    ) -> pd.Series:
        """Calculate current assets divided by current liabilities."""

        return safe_divide(current_assets, current_liabilities)

    def _calculate_ebitda_margin(
        self,
        ebitda: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate EBITDA divided by revenue."""

        return safe_divide(ebitda, revenue)

    def _calculate_debt_to_assets(
        self,
        debt: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate total debt divided by total assets."""

        return safe_divide(debt, assets)

    def _calculate_debt_to_equity(
        self,
        debt: pd.Series,
        equity: pd.Series,
    ) -> pd.Series:
        """Calculate total debt divided by equity."""

        return safe_divide(debt, equity)

    def _calculate_operating_margin(
        self,
        operating_income: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate operating income divided by revenue."""

        return safe_divide(operating_income, revenue)

    def _calculate_return_on_assets(
        self,
        net_income: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate net income divided by total assets."""

        return safe_divide(net_income, assets)

    def _calculate_return_on_equity(
        self,
        net_income: pd.Series,
        equity: pd.Series,
    ) -> pd.Series:
        """Calculate net income divided by equity."""

        return safe_divide(net_income, equity)

    def _calculate_interest_coverage(
        self,
        ebit: pd.Series,
        interest_expense: pd.Series,
    ) -> pd.Series:
        """Calculate EBIT divided by the absolute interest expense."""

        return safe_divide(ebit, interest_expense.abs())

    def _calculate_net_debt_to_ebitda(
        self,
        debt: pd.Series,
        cash: pd.Series,
        ebitda: pd.Series,
    ) -> pd.Series:
        """Calculate debt net of cash divided by EBITDA."""

        return safe_divide(debt - cash, ebitda)

    def _calculate_liabilities_to_assets(
        self,
        liabilities: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate total liabilities divided by total assets."""

        return safe_divide(liabilities, assets)

    def _calculate_free_cash_flow_margin(
        self,
        free_cash_flow: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate free cash flow divided by revenue."""

        return safe_divide(free_cash_flow, revenue)

    def _calculate_free_cash_flow_to_debt(
        self,
        free_cash_flow: pd.Series,
        debt: pd.Series,
    ) -> pd.Series:
        """Calculate free cash flow divided by total debt."""

        return safe_divide(free_cash_flow, debt)

    def _calculate_working_capital_to_assets(
        self,
        working_capital: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate working capital divided by total assets."""

        return safe_divide(working_capital, assets)

    def _calculate_operating_cash_flow_margin(
        self,
        operating_cash_flow: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate operating cash flow divided by revenue."""

        return safe_divide(operating_cash_flow, revenue)

    def _calculate_retained_earnings_to_assets(
        self,
        retained_earnings: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate retained earnings divided by total assets."""

        return safe_divide(retained_earnings, assets)

    def _calculate_operating_cash_flow_to_net_income(
        self,
        operating_cash_flow: pd.Series,
        net_income: pd.Series,
    ) -> pd.Series:
        """Calculate operating cash flow divided by net income."""

        return safe_divide(operating_cash_flow, net_income)
