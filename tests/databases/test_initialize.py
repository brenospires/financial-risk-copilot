import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.system_defaults import FRED_PROVIDER, SEC_PROVIDER
from database.data_provider_repository import DataProviderRepository
from database.initialize import initialize_database


class TestInitializeDatabase(unittest.TestCase):
    def test_creates_all_data_model_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            db_path = Path(temporary_directory) / "test.db"

            initialize_database(db_path)

            with sqlite3.connect(db_path) as connection:
                rows = connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()

        table_names = {row[0] for row in rows}
        self.assertTrue(
            {
                "companies",
                "data_providers",
                "financial_statements",
            }.issubset(table_names)
        )

    def test_persists_canonical_provider_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            db_path = Path(temporary_directory) / "test.db"
            initialize_database(db_path)
            repository = DataProviderRepository(db_path)

            sec = repository.get_by_id(SEC_PROVIDER.id)
            fred = repository.get_by_id(FRED_PROVIDER.id)

        self.assertEqual(sec, SEC_PROVIDER)
        self.assertEqual(fred, FRED_PROVIDER)


if __name__ == "__main__":
    unittest.main()
