"""Financial-statement trend adjustments."""

import pandas as pd

from config.trend_analysis import (
    ALIGNMENT_TOLERANCE_DAYS_BY_FREQUENCY,
    MAX_STALE_BALANCE_SHEET_PERIODS,
    PERIOD_MONTHS_BY_FREQUENCY,
)
from data_models.financial_statement import FinancialStatement
from data_models.financial_statement_measure import (
    FINANCIAL_STATEMENT_MEASURE_INFO,
    FinancialStatementMeasure,
    FinancialStatementMeasureType,
)
from data_models.time_series_frequency import TimeSeriesFrequency
from utils.time_series import pivot_time_series


class FinancialStatementTrends:
    """Adjust financial-statement measures using their historical trends."""

    def adjust_financial_statements_by_trend(
        self,
        statements: list[FinancialStatement],
    ) -> dict[FinancialStatementMeasure, dict[str, float | None]]:
        """Return original and trend-adjusted values for every measure."""

        raise NotImplementedError

    def _pivot_financial_statements(
        self,
        statements: list[FinancialStatement],
    ) -> pd.DataFrame:
        """Return observed measures by reporting date in chronological order."""

        self._validate_statements(statements)
        records = [
            statement.model_dump(mode="json")
            for statement in statements
        ]

        return pivot_time_series(
            records,
            values="value",
            columns="measure",
            timestamp="end_date",
            group_columns=(
                "unit",
                "ticker",
                "market",
                "frequency",
                "provider_id",
            ),
        )

    def _prepare_balance_sheet_measure(
        self,
        statements: pd.DataFrame,
        measure: FinancialStatementMeasure,
    ) -> tuple[pd.Series, float | None]:
        """Return observed history and the latest value within the stale limit."""

        measure_type = FINANCIAL_STATEMENT_MEASURE_INFO[measure]["measure_type"]
        if measure_type is not FinancialStatementMeasureType.BALANCE_SHEET:
            raise ValueError(f"{measure.value} is not a balance-sheet measure")

        if measure.value not in statements:
            return pd.Series(dtype="Float64"), None

        dates = pd.DatetimeIndex(
            statements.index.get_level_values("end_date")
        )
        history = statements[measure.value].copy()
        history.index = dates
        history = history.dropna().sort_index()
        if history.empty:
            return history, None

        frequency = TimeSeriesFrequency(
            statements.index.get_level_values("frequency")[0]
        )
        stale_months = (
            PERIOD_MONTHS_BY_FREQUENCY[frequency.value]
            * MAX_STALE_BALANCE_SHEET_PERIODS
        )
        oldest_allowed_date = (
            dates.max()
            - pd.DateOffset(months=stale_months)
            - pd.Timedelta(
                days=ALIGNMENT_TOLERANCE_DAYS_BY_FREQUENCY[frequency.value]
            )
        )
        if history.index[-1] < oldest_allowed_date:
            return history, None

        return history, float(history.iloc[-1])

    def _validate_statements(
        self,
        statements: list[FinancialStatement],
    ) -> None:
        """Validate that statements describe one financial-reporting context."""

        if not statements:
            raise ValueError("Financial statements are required")

        contexts = {
            "unit": {statement.unit.casefold() for statement in statements},
            "ticker": {statement.ticker for statement in statements},
            "market": {statement.market.casefold() for statement in statements},
            "provider": {statement.provider_id for statement in statements},
            "frequency": {statement.frequency for statement in statements},
        }
        for name, values in contexts.items():
            if len(values) > 1:
                raise ValueError(f"Financial statements must use one {name}")
