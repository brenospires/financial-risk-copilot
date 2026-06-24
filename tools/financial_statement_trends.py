"""Financial-statement trend adjustments."""

import pandas as pd

from config.trend_analysis import (
    MAX_TREND_ADJUSTMENT,
    MIN_TREND_ADJUSTMENT,
    NO_TREND_ADJUSTMENT_MAX_PERIODS,
)
from data_models.financial_statement_measure import (
    FINANCIAL_STATEMENT_MEASURE_INFO,
    FinancialStatementMeasure,
    FinancialStatementMeasureType,
)


class FinancialStatementTrends:
    def adjust_financial_statements_by_trend(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        if df.empty:
            raise ValueError("Financial statements DataFrame is empty")
        if "end_date" not in df.columns:
            raise ValueError("Financial statements require an end_date column")

        df = df.sort_values(by=["end_date"])
        df_trend = df.iloc[:-1].copy()
        df_current = df.iloc[[-1]].copy()

        if len(df) <= NO_TREND_ADJUSTMENT_MAX_PERIODS:
            return df_current

        df_trends = df_trend.ffill()

        for column in df_trend.columns:
            try:
                measure = FinancialStatementMeasure(column)
            except ValueError:
                continue

            trend = df_trends[column].pct_change(fill_method=None).dropna()
            if trend.empty:
                continue

            trend_signal = trend.ewm(alpha=0.35).mean().iloc[-1]
            score = (trend < trend_signal).mean()
            adjustment = MIN_TREND_ADJUSTMENT + score * (
                MAX_TREND_ADJUSTMENT - MIN_TREND_ADJUSTMENT
            )

            measure_type = FINANCIAL_STATEMENT_MEASURE_INFO[measure]["measure_type"]
            if measure_type is FinancialStatementMeasureType.FLOW:
                adjustment = -adjustment

            df_current[column] *= 1 + adjustment

        return df_current
