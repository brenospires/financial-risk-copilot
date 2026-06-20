import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from databases.initialize import initialize_database


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
                "company_sources",
                "data_providers",
                "financial_statements",
            }.issubset(table_names)
        )


if __name__ == "__main__":
    unittest.main()
