import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.company import Company
from data_models.financial_statement import FinancialStatement
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency
from database.company_repository import CompanyRepository
from database.financial_statement_repository import FinancialStatementRepository
from database.initialize import initialize_database
from database.data_provider_repository import DataProviderRepository


class TestFinancialStatementRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(self.db_path)

        self.provider = DataProviderRepository(self.db_path).get_by_id(1)
        self.assertIsNotNone(self.provider)
        self.company = CompanyRepository(self.db_path).upsert(
            Company(
                provider_id=self.provider.id,
                ticker="AAPL",
                market="US",
                name="Apple Inc.",
                country="US",
            )
        )
        self.repository = FinancialStatementRepository(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def statement(self, **changes: object) -> FinancialStatement:
        values: dict[str, object] = {
            "provider_id": self.provider.id,
            "company_id": self.company.id,
            "ticker": "AAPL",
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

    def test_persists_observation_without_company(self) -> None:
        statement = self.repository.upsert(self.statement(company_id=None))

        self.assertIsNone(statement.company_id)

    def test_upsert_updates_same_economic_observation(self) -> None:
        created = self.repository.upsert(self.statement())
        updated = self.repository.upsert(
            self.statement(value=125.0, fiscal_year=2025, fiscal_period="Q1")
        )

        self.assertEqual(created.id, updated.id)
        self.assertEqual(updated.value, 125.0)
        self.assertEqual(updated.fiscal_period, "Q1")

    def test_keeps_frequencies_separate(self) -> None:
        annual = self.repository.upsert(self.statement())
        quarterly = self.repository.upsert(
            self.statement(
                frequency=TimeSeriesFrequency.QUARTERLY,
                start_date=date(2024, 10, 1),
                fiscal_period="Q4",
            )
        )

        self.assertNotEqual(annual.id, quarterly.id)

    def test_filters_time_series_by_frequency_period_and_measures(self) -> None:
        expected = self.repository.upsert(self.statement())
        self.repository.upsert(
            self.statement(
                measure=FinancialStatementMeasure.NET_INCOME,
                end_date=date(2023, 12, 31),
                start_date=date(2023, 1, 1),
                fiscal_year=2023,
            )
        )

        records = self.repository.get_for_period(
            ticker="AAPL",
            market="US",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            measures=[FinancialStatementMeasure.REVENUE],
        )

        self.assertEqual(records, [expected])

    def test_retrieves_snapshot_for_exact_date(self) -> None:
        expected = self.repository.upsert(self.statement())
        self.repository.upsert(
            self.statement(
                end_date=date(2023, 12, 31),
                start_date=date(2023, 1, 1),
                fiscal_year=2023,
            )
        )

        records = self.repository.get_for_period(
            ticker="AAPL",
            market="US",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 12, 31),
        )

        self.assertEqual(records, [expected])

    def test_rejects_end_date_without_start_date(self) -> None:
        with self.assertRaises(ValueError):
            self.repository.get_for_period(
                ticker="AAPL",
                market="US",
                frequency=TimeSeriesFrequency.ANNUAL,
                end_date=date(2024, 12, 31),
            )

    def test_rejects_request_without_dates(self) -> None:
        with self.assertRaises(ValueError):
            self.repository.get_for_period(
                ticker="AAPL",
                market="US",
                frequency=TimeSeriesFrequency.ANNUAL,
            )

    def test_rejects_start_date_after_end_date(self) -> None:
        with self.assertRaises(ValueError):
            self.repository.get_for_period(
                ticker="AAPL",
                market="US",
                frequency=TimeSeriesFrequency.ANNUAL,
                start_date=date(2025, 1, 1),
                end_date=date(2024, 12, 31),
            )


if __name__ == "__main__":
    unittest.main()
