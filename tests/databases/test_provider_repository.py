import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.provider import DataProvider
from database.initialize import initialize_database
from database.provider_repository import DataProviderRepository


class TestDataProviderRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / "test.db"
        initialize_database(self.db_path)
        self.repository = DataProviderRepository(self.db_path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_upsert_updates_existing_provider(self) -> None:
        created = self.repository.upsert(DataProvider(name="SEC"))
        updated = self.repository.upsert(DataProvider(name="sec", active=False))

        self.assertEqual(created.id, updated.id)
        self.assertFalse(updated.active)
        self.assertEqual(self.repository.get_by_name("SEC"), updated)


if __name__ == "__main__":
    unittest.main()
