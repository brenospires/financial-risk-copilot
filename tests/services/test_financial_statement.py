import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.financial_statement import FinancialStatement
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency
from database.financial_statement_repository import FinancialStatementRepository
from database.initialize import initialize_database
from services.financial_statement import FinancialStatementService
from tools.data_domains_retrieval.financial_statement import (
    FinancialStatementDataProvider,
)


class FakeFinancialStatementProvider(FinancialStatementDataProvider):
    def __init__(self, statements: list[FinancialStatement]) -> None:
        self.calls = 0
        self.statements = statements

    def fetch_financial_statements(
        self,
        ticker: str,
        market: str,
        frequency: TimeSeriesFrequency,
        start_date: date,
        end_date: date | None = None,
    ) -> list[FinancialStatement]:
        """Return configured statements and count external fetches."""

        self.calls += 1
        return self.statements


class TestFinancialStatementService(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(self.db_path)
        self.repository = FinancialStatementRepository(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def statement(self, year: int) -> FinancialStatement:
        return FinancialStatement(
            unit="USD",
            market="NASDAQ",
            ticker="AAPL",
            value=float(year),
            company_id=None,
            provider_id=1,
            start_date=None,
            fiscal_year=year,
            fiscal_period="FY",
            end_date=date(year, 12, 31),
            measure=FinancialStatementMeasure.ASSETS,
            frequency=TimeSeriesFrequency.ANNUAL,
            observation_type=ObservationType.SNAPSHOT,
        )

    def service(
        self,
        statements: list[FinancialStatement],
    ) -> tuple[FinancialStatementService, FakeFinancialStatementProvider]:
        provider = FakeFinancialStatementProvider(statements)
        service = FinancialStatementService(
            provider=provider,
            repository=self.repository,
        )

        return service, provider

    def test_fetches_upserts_and_requeries_when_database_is_empty(self) -> None:
        expected = self.statement(2024)
        service, provider = self.service([expected])

        statements = service.get_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(statements), 1)
        self.assertEqual(statements[0].value, expected.value)
        self.assertIsNotNone(statements[0].id)

    def test_uses_database_when_requested_period_is_covered(self) -> None:
        expected = self.repository.upsert(self.statement(2024))
        service, provider = self.service([])

        statements = service.get_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        self.assertEqual(statements, [expected])
        self.assertEqual(provider.calls, 0)

    def test_fetches_when_database_has_an_internal_period_hole(self) -> None:
        self.repository.upsert(self.statement(2022))
        self.repository.upsert(self.statement(2024))
        service, provider = self.service([self.statement(2023)])

        statements = service.get_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        self.assertEqual(provider.calls, 1)
        self.assertEqual(
            [statement.fiscal_year for statement in statements],
            [2022, 2023, 2024],
        )

    def test_refresh_fetches_even_when_database_is_covered(self) -> None:
        self.repository.upsert(self.statement(2024))
        refreshed = self.statement(2024).model_copy(update={"value": 999.0})
        service, provider = self.service([refreshed])

        statements = service.get_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            refresh=True,
        )

        self.assertEqual(provider.calls, 1)
        self.assertEqual(statements[0].value, 999.0)

    def test_provider_exception_bubbles_up_when_fetch_fails(self) -> None:
        self.repository.upsert(self.statement(2024))

        class ErrorProvider(FinancialStatementDataProvider):
            def fetch_financial_statements(
                self,
                ticker: str,
                market: str,
                frequency: TimeSeriesFrequency,
                start_date: date,
                end_date: date | None = None,
            ) -> list[FinancialStatement]:
                raise RuntimeError("external provider failure")

        service = FinancialStatementService(
            provider=ErrorProvider(),
            repository=self.repository,
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "external provider failure",
        ):
            service.get_financial_statements(
                ticker="AAPL",
                market="NASDAQ",
                frequency=TimeSeriesFrequency.ANNUAL,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                refresh=True,
            )


if __name__ == "__main__":
    unittest.main()
