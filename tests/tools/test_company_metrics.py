import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.company_metrics import CompanyMetrics


class TestCompanyMetricsContract(unittest.TestCase):
    def setUp(self) -> None:
        self.metrics = CompanyMetrics()

    def current_snapshot(self, **changes: object) -> pd.DataFrame:
        values: dict[str, object] = {
            "cash": 100.0,
            "debt": 300.0,
            "ebit": 120.0,
            "assets": 1000.0,
            "equity": 400.0,
            "ebitda": 200.0,
            "revenue": 800.0,
            "inventory": 50.0,
            "net_income": 80.0,
            "liabilities": 600.0,
            "gross_profit": 320.0,
            "current_assets": 400.0,
            "free_cash_flow": 120.0,
            "operating_income": 160.0,
            "working_capital": 200.0,
            "interest_expense": -20.0,
            "retained_earnings": 100.0,
            "current_liabilities": 200.0,
            "operating_cash_flow": 160.0,
        }
        values.update(changes)

        return pd.DataFrame([values])

    def test_rejects_empty_current_snapshot(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "expects a snapshot of financial metrics records",
        ):
            self.metrics.calculate_metrics(pd.DataFrame())

    def test_rejects_multiple_current_snapshot_rows(self) -> None:
        dt_current = pd.concat(
            [
                self.current_snapshot(),
                self.current_snapshot(),
            ],
            ignore_index=True,
        )

        with self.assertRaisesRegex(
            ValueError,
            "expects a snapshot of financial metrics records",
        ):
            self.metrics.calculate_metrics(dt_current)

    def test_calculates_complete_current_snapshot_metrics(self) -> None:
        metrics = self.metrics.calculate_metrics(self.current_snapshot())
        expected_metrics = {
            "cash_ratio": 0.5,
            "net_margin": 0.1,
            "quick_ratio": 1.75,
            "equity_ratio": 0.4,
            "gross_margin": 0.4,
            "current_ratio": 2.0,
            "ebitda_margin": 0.25,
            "debt_to_assets": 0.3,
            "debt_to_equity": 0.75,
            "operating_margin": 0.2,
            "return_on_assets": 0.08,
            "return_on_equity": 0.2,
            "interest_coverage": 6.0,
            "net_debt_to_ebitda": 1.0,
            "liabilities_to_assets": 0.6,
            "free_cash_flow_margin": 0.15,
            "free_cash_flow_to_debt": 0.4,
            "working_capital_to_assets": 0.2,
            "operating_cash_flow_margin": 0.2,
            "retained_earnings_to_assets": 0.1,
            "operating_cash_flow_to_net_income": 2.0,
        }

        self.assertEqual(list(metrics), list(CompanyMetrics.METRIC_COLUMNS))
        for metric_name, expected_value in expected_metrics.items():
            with self.subTest(metric=metric_name):
                self.assertAlmostEqual(metrics[metric_name], expected_value)

    def test_missing_inputs_return_none_for_affected_metrics(self) -> None:
        metrics = self.metrics.calculate_metrics(
            self.current_snapshot(
                cash=pd.NA,
                inventory=pd.NA,
                retained_earnings=pd.NA,
            )
        )

        self.assertIsNone(metrics["cash_ratio"])
        self.assertIsNone(metrics["quick_ratio"])
        self.assertIsNone(metrics["net_debt_to_ebitda"])
        self.assertIsNone(metrics["retained_earnings_to_assets"])
        self.assertAlmostEqual(metrics["current_ratio"], 2.0)

    def test_missing_columns_return_none_for_affected_metrics(self) -> None:
        dt_current = self.current_snapshot().drop(
            columns=[
                "cash",
                "inventory",
                "retained_earnings",
            ]
        )

        metrics = self.metrics.calculate_metrics(dt_current)

        self.assertIsNone(metrics["cash_ratio"])
        self.assertIsNone(metrics["quick_ratio"])
        self.assertIsNone(metrics["net_debt_to_ebitda"])
        self.assertIsNone(metrics["retained_earnings_to_assets"])
        self.assertAlmostEqual(metrics["current_ratio"], 2.0)

    def test_non_numeric_inputs_return_none_for_affected_metrics(self) -> None:
        metrics = self.metrics.calculate_metrics(
            self.current_snapshot(
                cash="not numeric",
                current_assets="not numeric",
                retained_earnings="not numeric",
            )
        )

        self.assertIsNone(metrics["cash_ratio"])
        self.assertIsNone(metrics["quick_ratio"])
        self.assertIsNone(metrics["current_ratio"])
        self.assertIsNone(metrics["retained_earnings_to_assets"])
        self.assertAlmostEqual(metrics["net_margin"], 0.1)

    def test_zero_denominators_return_none(self) -> None:
        metrics = self.metrics.calculate_metrics(
            self.current_snapshot(
                assets=0.0,
                debt=0.0,
                equity=0.0,
                ebitda=0.0,
                revenue=0.0,
                net_income=0.0,
                interest_expense=0.0,
                current_liabilities=0.0,
            )
        )

        self.assertTrue(
            all(
                value is None
                for value in metrics.values()
            )
        )

    def test_interest_coverage_uses_absolute_interest_expense(self) -> None:
        positive_interest_metrics = self.metrics.calculate_metrics(
            self.current_snapshot(interest_expense=20.0)
        )
        negative_interest_metrics = self.metrics.calculate_metrics(
            self.current_snapshot(interest_expense=-20.0)
        )

        self.assertAlmostEqual(
            positive_interest_metrics["interest_coverage"],
            6.0,
        )
        self.assertAlmostEqual(
            negative_interest_metrics["interest_coverage"],
            6.0,
        )


if __name__ == "__main__":
    unittest.main()
