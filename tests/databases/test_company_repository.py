import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.company import Company
from database.company_repository import CompanyRepository
from database.initialize import initialize_database


class TestCompanyRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(self.db_path)
        self.repository = CompanyRepository(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_upsert_updates_existing_company(self) -> None:
        created = self.repository.upsert(
            Company(name="Apple Inc.", country="US", sector="Technology")
        )
        updated = self.repository.upsert(
            Company(
                name="apple inc.",
                country="US",
                industry="Consumer Electronics",
                sector="Technology",
            )
        )

        self.assertEqual(created.id, updated.id)
        self.assertEqual(updated.industry, "Consumer Electronics")
        self.assertEqual(self.repository.get_by_id(updated.id), updated)


if __name__ == "__main__":
    unittest.main()
