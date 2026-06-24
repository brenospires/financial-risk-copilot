import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.trend_analysis import (
    MAX_TREND_ADJUSTMENT,
    MIN_TREND_ADJUSTMENT,
)
from tools.financial_statement_trends import FinancialStatementTrends


class TestFinancialStatementTrends(unittest.TestCase):
    @staticmethod
    def frame(
        assets: list[float | None],
        revenue: list[float | None] | None = None,
    ) -> pd.DataFrame:
        data = {
            "end_date": pd.date_range(
                "2000-12-31",
                periods=len(assets),
                freq="YE",
            ),
            "ticker": ["AMZN"] * len(assets),
            "assets": pd.array(assets, dtype="Float64"),
        }

        if revenue is not None:
            data["revenue"] = pd.array(revenue, dtype="Float64")

        return pd.DataFrame(data)

    def test_returns_unchanged_current_row_with_three_records(self) -> None:
        statements = self.frame([80.0, 90.0, 100.0])

        adjusted = FinancialStatementTrends().adjust_financial_statements_by_trend(
            statements
        )

        self.assertEqual(len(adjusted), 1)
        self.assertEqual(adjusted.iloc[0]["ticker"], "AMZN")
        self.assertEqual(adjusted.iloc[0]["assets"], 100.0)
        self.assertEqual(
            adjusted.iloc[0]["end_date"],
            statements.iloc[-1]["end_date"],
        )

    def test_calculates_score_from_smoothed_historical_changes(self) -> None:
        values = [100.0, 110.0, 99.0, 118.8, 130.0]
        statements = self.frame(values, revenue=values)

        adjusted = FinancialStatementTrends().adjust_financial_statements_by_trend(
            statements
        )

        expected_adjustment = MIN_TREND_ADJUSTMENT + (1 / 3) * (
            MAX_TREND_ADJUSTMENT - MIN_TREND_ADJUSTMENT
        )
        self.assertAlmostEqual(
            adjusted.iloc[0]["assets"],
            130.0 * (1 + expected_adjustment),
        )
        self.assertAlmostEqual(
            adjusted.iloc[0]["revenue"],
            130.0 * (1 - expected_adjustment),
        )

    def test_forward_fills_only_historical_records(self) -> None:
        statements = self.frame([100.0, None, 110.0, 121.0, 130.0])

        adjusted = FinancialStatementTrends().adjust_financial_statements_by_trend(
            statements
        )

        expected_adjustment = MIN_TREND_ADJUSTMENT + (1 / 3) * (
            MAX_TREND_ADJUSTMENT - MIN_TREND_ADJUSTMENT
        )
        self.assertAlmostEqual(
            adjusted.iloc[0]["assets"],
            130.0 * (1 + expected_adjustment),
        )

    def test_flow_measure_reverses_balance_sheet_adjustment(self) -> None:
        values = [100.0, 110.0, 99.0, 118.8, 130.0]
        statements = self.frame(values, revenue=values)

        adjusted = FinancialStatementTrends().adjust_financial_statements_by_trend(
            statements
        )

        asset_change = adjusted.iloc[0]["assets"] - 130.0
        revenue_change = adjusted.iloc[0]["revenue"] - 130.0
        self.assertAlmostEqual(asset_change, -revenue_change)

    def test_preserves_missing_current_value(self) -> None:
        statements = self.frame([70.0, 80.0, 90.0, 100.0, None])

        adjusted = FinancialStatementTrends().adjust_financial_statements_by_trend(
            statements
        )

        self.assertTrue(pd.isna(adjusted.iloc[0]["assets"]))

    def test_orders_records_before_selecting_current_row(self) -> None:
        statements = self.frame([80.0, 90.0, 100.0])
        unordered = statements.iloc[[2, 0, 1]]

        adjusted = FinancialStatementTrends().adjust_financial_statements_by_trend(
            unordered
        )

        self.assertEqual(
            adjusted.iloc[0]["end_date"],
            statements.iloc[-1]["end_date"],
        )
        self.assertEqual(adjusted.iloc[0]["assets"], 100.0)

    def test_does_not_mutate_input(self) -> None:
        statements = self.frame([100.0, 110.0, 99.0, 118.8, 130.0])
        original = statements.copy()

        FinancialStatementTrends().adjust_financial_statements_by_trend(
            statements
        )

        pd.testing.assert_frame_equal(statements, original)

    def test_rejects_empty_dataframe(self) -> None:
        with self.assertRaisesRegex(ValueError, "DataFrame is empty"):
            FinancialStatementTrends().adjust_financial_statements_by_trend(
                pd.DataFrame()
            )

    def test_rejects_dataframe_without_reporting_date(self) -> None:
        statements = pd.DataFrame(
            {"assets": [100.0]},
        )

        with self.assertRaisesRegex(ValueError, "end_date column"):
            FinancialStatementTrends().adjust_financial_statements_by_trend(
                statements
            )


if __name__ == "__main__":
    unittest.main()
