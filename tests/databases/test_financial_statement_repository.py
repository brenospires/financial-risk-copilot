import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.company import Company
from data_models.company_source import CompanySource
from data_models.financial_item import FinancialItem
from data_models.financial_statement import FinancialStatement
from data_models.observation_type import ObservationType
from data_models.provider import DataProvider
from data_models.time_series_frequency import TimeSeriesFrequency
from database.company_repository import CompanyRepository
from database.company_source_repository import CompanySourceRepository
from database.financial_statement_repository import FinancialStatementRepository
from database.initialize import initialize_database
from database.provider_repository import DataProviderRepository


class TestFinancialStatementRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(self.db_path)

        company = CompanyRepository(self.db_path).upsert(
            Company(name="Apple Inc.", country="US")
        )
        provider = DataProviderRepository(self.db_path).upsert(
            DataProvider(name="SEC")
        )
        self.source = CompanySourceRepository(self.db_path).upsert(
            CompanySource(
                company_id=company.id,
                provider_id=provider.id,
                provider_company_id="0000320193",
                ticker="AAPL",
                market="US",
            )
        )
        self.repository = FinancialStatementRepository(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def statement(self, **changes: object) -> FinancialStatement:
        values: dict[str, object] = {
            "company_source_id": self.source.id,
            "item": FinancialItem.REVENUE,
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

    def test_filters_by_frequency_period_and_items(self) -> None:
        expected = self.repository.upsert(self.statement())
        self.repository.upsert(
            self.statement(
                item=FinancialItem.NET_INCOME,
                end_date=date(2023, 12, 31),
                start_date=date(2023, 1, 1),
                fiscal_year=2023,
            )
        )

        records = self.repository.get_for_period(
            company_source_id=self.source.id,
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            items=[FinancialItem.REVENUE],
        )

        self.assertEqual(records, [expected])


if __name__ == "__main__":
    unittest.main()
