import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.company import Company
from database.company_repository import CompanyRepository
from database.initialize import initialize_database
from database.data_provider_repository import DataProviderRepository


class TestCompanyRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(self.db_path)
        self.provider = DataProviderRepository(self.db_path).get_by_id(1)
        self.assertIsNotNone(self.provider)
        self.repository = CompanyRepository(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_upsert_updates_existing_company(self) -> None:
        created = self.repository.upsert(
            Company(
                provider_id=self.provider.id,
                ticker="AAPL",
                market="US",
                name="Apple Inc.",
                country="US",
                sector="Technology",
            )
        )
        updated = self.repository.upsert(
            Company(
                provider_id=self.provider.id,
                ticker="aapl",
                market="US",
                name="Apple Incorporated",
                country="US",
                sector="Technology",
            )
        )

        self.assertEqual(created.id, updated.id)
        self.assertEqual(updated.name, "Apple Incorporated")
        self.assertEqual(self.repository.get_by_id(updated.id), updated)


if __name__ == "__main__":
    unittest.main()
