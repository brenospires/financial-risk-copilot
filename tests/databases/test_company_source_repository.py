import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.company import Company
from data_models.company_source import CompanySource
from data_models.provider import DataProvider
from database.company_repository import CompanyRepository
from database.company_source_repository import CompanySourceRepository
from database.initialize import initialize_database
from database.provider_repository import DataProviderRepository


class TestCompanySourceRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(self.db_path)

        self.company = CompanyRepository(self.db_path).upsert(
            Company(name="Apple Inc.", country="US")
        )
        self.provider = DataProviderRepository(self.db_path).upsert(
            DataProvider(name="SEC")
        )
        self.repository = CompanySourceRepository(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def source(self, **changes: object) -> CompanySource:
        values: dict[str, object] = {
            "company_id": self.company.id,
            "provider_id": self.provider.id,
            "provider_company_id": "0000320193",
            "ticker": "AAPL",
            "market": "US",
            "exchange": "NASDAQ",
            "currency": "USD",
        }
        values.update(changes)
        return CompanySource.model_validate(values)

    def test_upsert_updates_existing_source(self) -> None:
        created = self.repository.upsert(self.source())
        updated = self.repository.upsert(self.source(exchange="NYSE"))

        self.assertEqual(created.id, updated.id)
        self.assertEqual(updated.exchange, "NYSE")

    def test_rejects_missing_foreign_key(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.repository.upsert(self.source(company_id=999))


if __name__ == "__main__":
    unittest.main()
