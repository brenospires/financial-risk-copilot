import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.financial_statement import FinancialStatement
from data_models.financial_statement_measure import (
    FINANCIAL_STATEMENT_MEASURE_INFO,
    FinancialStatementMeasure,
    FinancialStatementMeasureType,
)
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency
from tools.financial_statement_trends import FinancialStatementTrends


class TestFinancialStatementTrendClassifications(unittest.TestCase):
    def test_metadata_covers_every_measure(self) -> None:
        self.assertEqual(
            set(FINANCIAL_STATEMENT_MEASURE_INFO),
            set(FinancialStatementMeasure),
        )

    def test_metadata_values_are_valid(self) -> None:
        valid_directions = {
            "contextual",
            "lower_better",
            "higher_better",
        }

        for measure, info in FINANCIAL_STATEMENT_MEASURE_INFO.items():
            with self.subTest(measure=measure):
                self.assertEqual(
                    set(info),
                    {"measure_type", "risk_direction"},
                )
                self.assertIn(
                    info["measure_type"],
                    set(FinancialStatementMeasureType),
                )
                self.assertIn(info["risk_direction"], valid_directions)

    def test_representative_financial_semantics(self) -> None:
        self.assertEqual(
            FINANCIAL_STATEMENT_MEASURE_INFO[
                FinancialStatementMeasure.ASSETS
            ],
            {
                "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
                "risk_direction": "contextual",
            },
        )
        self.assertEqual(
            FINANCIAL_STATEMENT_MEASURE_INFO[
                FinancialStatementMeasure.DEBT
            ]["risk_direction"],
            "lower_better",
        )
        self.assertEqual(
            FINANCIAL_STATEMENT_MEASURE_INFO[
                FinancialStatementMeasure.REVENUE
            ],
            {
                "measure_type": FinancialStatementMeasureType.FLOW,
                "risk_direction": "higher_better",
            },
        )


class TestFinancialStatementTrendMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.trends = FinancialStatementTrends()

    def statement(self, **changes: object) -> FinancialStatement:
        values: dict[str, object] = {
            "unit": "USD",
            "value": 100.0,
            "market": "NASDAQ",
            "ticker": "AMZN",
            "company_id": None,
            "provider_id": 1,
            "start_date": None,
            "fiscal_year": 2024,
            "fiscal_period": "FY",
            "end_date": date(2024, 12, 31),
            "measure": FinancialStatementMeasure.ASSETS,
            "frequency": TimeSeriesFrequency.ANNUAL,
            "observation_type": ObservationType.SNAPSHOT,
        }
        values.update(changes)

        return FinancialStatement.model_validate(values)

    def test_pivots_only_observed_measures(self) -> None:
        statements = [
            self.statement(),
            self.statement(
                measure=FinancialStatementMeasure.REVENUE,
                start_date=date(2024, 1, 1),
                observation_type=ObservationType.PERIOD,
            ),
        ]

        result = self.trends._pivot_financial_statements(statements)

        self.assertEqual(
            set(result.columns),
            {"assets", "revenue"},
        )

    def test_orders_reporting_dates(self) -> None:
        statements = [
            self.statement(),
            self.statement(
                fiscal_year=2023,
                end_date=date(2023, 12, 31),
            ),
        ]

        result = self.trends._pivot_financial_statements(statements)

        self.assertEqual(
            list(result.index.get_level_values("end_date")),
            list(pd.to_datetime(["2023-12-31", "2024-12-31"])),
        )

    def test_rejects_empty_statement_list(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Financial statements are required",
        ):
            self.trends._pivot_financial_statements([])

    def test_rejects_mixed_statement_contexts(self) -> None:
        statements = [
            self.statement(),
            self.statement(market="NYSE"),
        ]

        with self.assertRaisesRegex(ValueError, "one market"):
            self.trends._pivot_financial_statements(statements)

    def test_prepares_current_balance_sheet_measure(self) -> None:
        statements = [
            self.statement(
                value=80.0,
                fiscal_year=2023,
                end_date=date(2023, 12, 31),
            ),
            self.statement(),
        ]
        matrix = self.trends._pivot_financial_statements(statements)

        history, latest = self.trends._prepare_balance_sheet_measure(
            matrix,
            FinancialStatementMeasure.ASSETS,
        )

        self.assertEqual(list(history), [80.0, 100.0])
        self.assertEqual(latest, 100.0)

    def test_accepts_balance_sheet_measure_one_period_stale(self) -> None:
        statements = [
            self.statement(
                fiscal_period="Q2",
                end_date=date(2024, 6, 30),
                frequency=TimeSeriesFrequency.QUARTERLY,
            ),
            self.statement(
                fiscal_period="Q3",
                end_date=date(2024, 9, 30),
                measure=FinancialStatementMeasure.CASH,
                frequency=TimeSeriesFrequency.QUARTERLY,
            ),
        ]
        matrix = self.trends._pivot_financial_statements(statements)

        _, latest = self.trends._prepare_balance_sheet_measure(
            matrix,
            FinancialStatementMeasure.ASSETS,
        )

        self.assertEqual(latest, 100.0)

    def test_rejects_balance_sheet_measure_over_one_period_stale(self) -> None:
        statements = [
            self.statement(
                fiscal_period="Q1",
                end_date=date(2024, 3, 31),
                frequency=TimeSeriesFrequency.QUARTERLY,
            ),
            self.statement(
                fiscal_period="Q3",
                end_date=date(2024, 9, 30),
                measure=FinancialStatementMeasure.CASH,
                frequency=TimeSeriesFrequency.QUARTERLY,
            ),
        ]
        matrix = self.trends._pivot_financial_statements(statements)

        history, latest = self.trends._prepare_balance_sheet_measure(
            matrix,
            FinancialStatementMeasure.ASSETS,
        )

        self.assertEqual(list(history), [100.0])
        self.assertIsNone(latest)

    def test_preserves_absent_balance_sheet_measure_as_null(self) -> None:
        matrix = self.trends._pivot_financial_statements(
            [self.statement()]
        )

        history, latest = self.trends._prepare_balance_sheet_measure(
            matrix,
            FinancialStatementMeasure.CASH,
        )

        self.assertTrue(history.empty)
        self.assertIsNone(latest)


if __name__ == "__main__":
    unittest.main()
