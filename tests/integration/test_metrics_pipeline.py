import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.settings import SEC_USER_AGENT
from config.system_defaults import SEC_PROVIDER
from data_models.time_series_frequency import TimeSeriesFrequency
from database.financial_statement_repository import FinancialStatementRepository
from database.initialize import initialize_database
from services.financial_statement import FinancialStatementService
from tools.company_metrics import CompanyMetrics
from tools.data_providers.sec import SECProvider


@unittest.skipUnless(
    SEC_USER_AGENT,
    "SEC_USER_AGENT is required for live SEC integration tests",
)
class TestMetricsPipelineIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_downloads_five_years_and_calculates_metrics(self) -> None:
        today = date.today()
        end_year = today.year - 1 if today.month >= 3 else today.year - 2
        start_year = end_year - 4
        start_date = date(start_year, 1, 1)
        end_date = date(end_year, 12, 31)

        repository = FinancialStatementRepository(self.db_path)
        provider = SECProvider(provider=SEC_PROVIDER)
        service = FinancialStatementService(
            provider=provider,
            repository=repository,
        )
        statements = service.get_financial_statements(
            ticker="AMZN",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=start_date,
            end_date=end_date,
            refresh=True,
        )
        snapshots = CompanyMetrics().calculate_snapshots(statements)
        observed_years = {
            timestamp.year
            for timestamp in snapshots.index.get_level_values("end_date")
        }
        expected_years = set(range(start_year, end_year + 1))

        self.assertTrue(statements)
        self.assertTrue(all(statement.id is not None for statement in statements))
        self.assertTrue(all(statement.company_id is None for statement in statements))
        self.assertEqual(len(snapshots), 5)
        self.assertEqual(observed_years, expected_years)
        self.assertFalse(snapshots.index.has_duplicates)
        self.assertEqual(
            list(snapshots.columns),
            [
                *CompanyMetrics.RAW_MEASURE_COLUMNS,
                *CompanyMetrics.METRIC_COLUMNS,
            ],
        )
        self.assertTrue(snapshots["assets"].notna().all())
        self.assertTrue(snapshots["revenue"].notna().all())
        self.assertTrue(snapshots["current_ratio"].notna().all())
        self.assertTrue(snapshots["debt_to_assets"].notna().all())
        self.assertTrue(snapshots["operating_margin"].notna().all())


if __name__ == "__main__":
    unittest.main()
