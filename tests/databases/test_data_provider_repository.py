import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.system_defaults import SEC_PROVIDER
from data_models.data_domain import DataDomain
from data_models.data_provider import DataProvider
from data_models.time_series_frequency import TimeSeriesFrequency
from database.initialize import initialize_database
from database.data_provider_repository import DataProviderRepository


class TestDataProviderRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(self.db_path)
        self.repository = DataProviderRepository(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_upsert_updates_existing_provider(self) -> None:
        created = self.repository.upsert(
            SEC_PROVIDER
        )
        updated = self.repository.upsert(
            DataProvider(
                id=1,
                name="sec",
                data_domains={
                    DataDomain.COMPANY,
                    DataDomain.FINANCIAL_STATEMENT,
                },
                supported_frequencies={TimeSeriesFrequency.ANNUAL},
                active=False,
            )
        )

        self.assertEqual(created.id, updated.id)
        self.assertEqual(
            updated.supported_frequencies,
            {TimeSeriesFrequency.ANNUAL},
        )
        self.assertFalse(updated.active)
        self.assertEqual(
            self.repository.get_by_name_and_domain(
                "SEC",
                DataDomain.FINANCIAL_STATEMENT,
            ),
            updated,
        )

    def test_same_provider_supports_multiple_domains(self) -> None:
        provider = self.repository.get_by_id(1)

        self.assertIsNotNone(provider)
        self.assertEqual(provider.id, 1)
        self.assertEqual(
            provider.data_domains,
            {
                DataDomain.COMPANY,
                DataDomain.FINANCIAL_STATEMENT,
            },
        )


if __name__ == "__main__":
    unittest.main()
