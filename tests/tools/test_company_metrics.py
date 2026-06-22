import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.financial_statement import FinancialStatement
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency
from tools.company_metrics import CompanyMetrics


class TestCompanyMetricsContract(unittest.TestCase):
    def setUp(self) -> None:
        self.metrics = CompanyMetrics()

    def statement(self, **changes: object) -> FinancialStatement:
        values: dict[str, object] = {
            "unit": "USD",
            "value": 100.0,
            "market": "NASDAQ",
            "ticker": "AAPL",
            "company_id": 1,
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

    def complete_statements(
        self,
        year: int = 2024,
        scale: float = 1.0,
    ) -> list[FinancialStatement]:
        values = {
            FinancialStatementMeasure.CASH: 100.0 * scale,
            FinancialStatementMeasure.DEBT: 300.0 * scale,
            FinancialStatementMeasure.EBIT: 120.0 * scale,
            FinancialStatementMeasure.ASSETS: 1000.0 * scale,
            FinancialStatementMeasure.EQUITY: 400.0 * scale,
            FinancialStatementMeasure.EBITDA: 200.0 * scale,
            FinancialStatementMeasure.REVENUE: 800.0 * scale,
            FinancialStatementMeasure.INVENTORY: 50.0 * scale,
            FinancialStatementMeasure.NET_INCOME: 80.0 * scale,
            FinancialStatementMeasure.LIABILITIES: 600.0 * scale,
            FinancialStatementMeasure.GROSS_PROFIT: 320.0 * scale,
            FinancialStatementMeasure.CURRENT_ASSETS: 400.0 * scale,
            FinancialStatementMeasure.FREE_CASH_FLOW: 120.0 * scale,
            FinancialStatementMeasure.OPERATING_INCOME: 160.0 * scale,
            FinancialStatementMeasure.WORKING_CAPITAL: 200.0 * scale,
            FinancialStatementMeasure.INTEREST_EXPENSE: -20.0 * scale,
            FinancialStatementMeasure.RETAINED_EARNINGS: 100.0 * scale,
            FinancialStatementMeasure.CURRENT_LIABILITIES: 200.0 * scale,
            FinancialStatementMeasure.OPERATING_CASH_FLOW: 160.0 * scale,
        }
        period_measures = {
            FinancialStatementMeasure.EBIT,
            FinancialStatementMeasure.EBITDA,
            FinancialStatementMeasure.REVENUE,
            FinancialStatementMeasure.NET_INCOME,
            FinancialStatementMeasure.GROSS_PROFIT,
            FinancialStatementMeasure.FREE_CASH_FLOW,
            FinancialStatementMeasure.OPERATING_INCOME,
            FinancialStatementMeasure.INTEREST_EXPENSE,
            FinancialStatementMeasure.OPERATING_CASH_FLOW,
        }

        return [
            self.statement(
                value=value,
                measure=measure,
                fiscal_year=year,
                end_date=date(year, 12, 31),
                start_date=(
                    date(year, 1, 1)
                    if measure in period_measures
                    else None
                ),
                observation_type=(
                    ObservationType.PERIOD
                    if measure in period_measures
                    else ObservationType.SNAPSHOT
                ),
            )
            for measure, value in values.items()
        ]

    def complete_history(self, year_count: int) -> list[FinancialStatement]:
        end_year = 2024
        start_year = end_year - year_count + 1

        return [
            statement
            for scale, year in enumerate(
                range(end_year, start_year - 1, -1),
                start=1,
            )
            for statement in self.complete_statements(
                year=year,
                scale=float(scale),
            )
        ]

    def test_rejects_empty_statement_list(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Financial statements are required",
        ):
            self.metrics.calculate_snapshots([])

    def test_accepts_multiple_periods_for_one_context(self) -> None:
        statements = [
            self.statement(
                fiscal_year=2023,
                end_date=date(2023, 12, 31),
            ),
            self.statement(),
        ]

        snapshots = self.metrics.calculate_snapshots(statements)

        self.assertEqual(len(snapshots), 2)

    def test_accepts_statements_without_company_id(self) -> None:
        snapshots = self.metrics.calculate_snapshots(
            [self.statement(company_id=None)]
        )

        self.assertEqual(len(snapshots), 1)

    def test_calculates_complete_snapshot_as_wide_dataframe(self) -> None:
        snapshots = self.metrics.calculate_snapshots(
            self.complete_statements()
        )
        snapshot = snapshots.iloc[0]

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(
            list(snapshots.columns),
            [
                *CompanyMetrics.RAW_MEASURE_COLUMNS,
                *CompanyMetrics.METRIC_COLUMNS,
            ],
        )
        expected_metrics = {
            "net_margin": 0.1,
            "cash_ratio": 0.5,
            "quick_ratio": 1.75,
            "gross_margin": 0.4,
            "equity_ratio": 0.4,
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

        for metric_name, expected_value in expected_metrics.items():
            with self.subTest(metric=metric_name):
                self.assertAlmostEqual(snapshot[metric_name], expected_value)

    def test_preserves_metric_columns_when_inputs_are_missing(self) -> None:
        snapshots = self.metrics.calculate_snapshots([self.statement()])
        missing_metrics = snapshots.loc[:, CompanyMetrics.METRIC_COLUMNS]

        self.assertTrue(
            missing_metrics.apply(pd.isna).all(axis=None)
        )

    def test_calculates_one_five_and_ten_year_histories(self) -> None:
        for year_count in (1, 5, 10):
            with self.subTest(year_count=year_count):
                snapshots = self.metrics.calculate_snapshots(
                    self.complete_history(year_count)
                )
                end_dates = list(
                    snapshots.index.get_level_values("end_date")
                )

                self.assertEqual(len(snapshots), year_count)
                self.assertEqual(end_dates, sorted(end_dates))
                self.assertTrue(
                    snapshots.loc[:, CompanyMetrics.METRIC_COLUMNS]
                    .notna()
                    .all(axis=None)
                )
                self.assertTrue(
                    snapshots["current_ratio"].eq(2.0).all()
                )
                self.assertTrue(
                    snapshots["net_debt_to_ebitda"].eq(1.0).all()
                )

    def test_one_year_history_is_one_snapshot_row(self) -> None:
        statements = self.complete_history(1)

        snapshots = self.metrics.calculate_snapshots(statements)

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(
            {statement.observation_type for statement in statements},
            {ObservationType.SNAPSHOT, ObservationType.PERIOD},
        )

    def test_conflicting_fiscal_labels_share_one_reporting_date(self) -> None:
        statements = [
            statement.model_copy(
                update={"fiscal_year": statement.fiscal_year + 1}
                if statement.observation_type is ObservationType.PERIOD
                else {},
            )
            for statement in self.complete_statements()
        ]

        snapshots = self.metrics.calculate_snapshots(statements)

        self.assertEqual(len(snapshots), 1)
        self.assertAlmostEqual(snapshots.iloc[0]["current_ratio"], 2.0)
        self.assertAlmostEqual(snapshots.iloc[0]["net_margin"], 0.1)

    def test_zero_denominators_preserve_nullable_metric_columns(self) -> None:
        denominator_measures = {
            FinancialStatementMeasure.DEBT,
            FinancialStatementMeasure.ASSETS,
            FinancialStatementMeasure.EQUITY,
            FinancialStatementMeasure.EBITDA,
            FinancialStatementMeasure.REVENUE,
            FinancialStatementMeasure.NET_INCOME,
            FinancialStatementMeasure.INTEREST_EXPENSE,
            FinancialStatementMeasure.CURRENT_LIABILITIES,
        }
        statements = [
            statement.model_copy(
                update={"value": 0.0}
                if statement.measure in denominator_measures
                else {},
            )
            for statement in self.complete_statements()
        ]

        snapshots = self.metrics.calculate_snapshots(statements)
        calculated_metrics = snapshots.loc[
            :,
            CompanyMetrics.METRIC_COLUMNS,
        ]

        self.assertTrue(calculated_metrics.isna().all(axis=None))

    def test_calculates_interest_coverage_with_positive_interest_expense(self) -> None:
        statements = self.complete_statements()
        statements = [
            statement.model_copy(
                update={"value": 20.0}
                if statement.measure is FinancialStatementMeasure.INTEREST_EXPENSE
                else {},
            )
            for statement in statements
        ]

        snapshots = self.metrics.calculate_snapshots(statements)
        snapshot = snapshots.iloc[0]

        self.assertAlmostEqual(snapshot["interest_coverage"], 6.0)

    def test_preserves_column_shape_for_sparse_statement_history(self) -> None:
        statements = self.complete_history(3)
        sparse_year = 2023
        statements = [
            statement
            for statement in statements
            if not (
                statement.fiscal_year == sparse_year
                and statement.measure is FinancialStatementMeasure.INVENTORY
            )
        ]

        snapshots = self.metrics.calculate_snapshots(statements)

        self.assertEqual(len(snapshots), 3)
        self.assertEqual(
            list(snapshots.columns),
            [*CompanyMetrics.RAW_MEASURE_COLUMNS, *CompanyMetrics.METRIC_COLUMNS],
        )
        self.assertTrue(
            pd.isna(
                snapshots.xs(
                    pd.Timestamp(sparse_year, 12, 31),
                    level="end_date",
                )["inventory"],
            ).all()
        )
        self.assertTrue(
            snapshots.loc[:, CompanyMetrics.METRIC_COLUMNS]
            .notna()
            .any(axis=None)
        )

    def test_rejects_duplicate_canonical_statements(self) -> None:
        statements = self.complete_statements()
        statements.append(statements[0].model_copy())

        with self.assertRaisesRegex(
            ValueError,
            "Duplicate canonical",
        ):
            self.metrics.calculate_snapshots(statements)

    def test_rejects_mixed_statement_contexts(self) -> None:
        context_changes = (
            ({"provider_id": 2}, "provider"),
            ({"ticker": "MSFT"}, "ticker"),
            ({"market": "NYSE"}, "market"),
            ({"unit": "EUR"}, "unit"),
            ({"frequency": TimeSeriesFrequency.QUARTERLY}, "frequency"),
        )

        for changes, context_name in context_changes:
            with self.subTest(context=context_name):
                statements = [self.statement(), self.statement(**changes)]

                with self.assertRaisesRegex(
                    ValueError,
                    f"one {context_name}",
                ):
                    self.metrics.calculate_snapshots(statements)


if __name__ == "__main__":
    unittest.main()
