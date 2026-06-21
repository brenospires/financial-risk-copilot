import sys
import unittest
from datetime import date
from pathlib import Path

from pydantic import ValidationError

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.financial_statement import FinancialStatement
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency


class TestFinancialStatement(unittest.TestCase):
    def statement(self, **changes: object) -> FinancialStatement:
        values: dict[str, object] = {
            "provider_id": 1,
            "company_id": 1,
            "ticker": "aapl",
            "market": "US",
            "measure": FinancialStatementMeasure.REVENUE,
            "value": 100.0,
            "unit": "USD",
            "observation_type": ObservationType.PERIOD,
            "frequency": TimeSeriesFrequency.ANNUAL,
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
            "fiscal_year": 2024,
            "fiscal_period": "FY",
        }
        values.update(changes)
        return FinancialStatement.model_validate(values)

    def test_accepts_period_observation(self) -> None:
        statement = self.statement()

        self.assertEqual(
            statement.measure,
            FinancialStatementMeasure.REVENUE,
        )
        self.assertEqual(statement.ticker, "AAPL")
        self.assertEqual(statement.frequency, TimeSeriesFrequency.ANNUAL)

    def test_accepts_observation_without_company(self) -> None:
        statement = self.statement(company_id=None)

        self.assertIsNone(statement.company_id)

    def test_accepts_snapshot_without_start_date(self) -> None:
        statement = self.statement(
            measure=FinancialStatementMeasure.ASSETS,
            observation_type=ObservationType.SNAPSHOT,
            start_date=None,
        )

        self.assertIsNone(statement.start_date)

    def test_requires_start_date_for_period(self) -> None:
        with self.assertRaises(ValidationError):
            self.statement(start_date=None)

    def test_rejects_start_date_after_end_date(self) -> None:
        with self.assertRaises(ValidationError):
            self.statement(start_date=date(2025, 1, 1))

    def test_rejects_start_date_for_snapshot(self) -> None:
        with self.assertRaises(ValidationError):
            self.statement(
                measure=FinancialStatementMeasure.ASSETS,
                observation_type=ObservationType.SNAPSHOT,
            )


if __name__ == "__main__":
    unittest.main()
