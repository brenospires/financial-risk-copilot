
import sqlite3
import pandas as pd
from pathlib import Path

class FREDRepository:
    """
    Simple SQLite repository for FRED data.

    This follows the same lightweight pattern used in SECRepository.
    """

    def __init__(self, db_path: str = "data/financial_risk_copilot.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fred_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    series_id TEXT,
                    indicator_name TEXT,
                    date TEXT,
                    value REAL
                )
            """)

            conn.commit()

    def save_indicator(
        self,
        series_id: str,
        indicator_name: str,
        df: pd.DataFrame,
    ):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM fred_observations WHERE series_id = ?",
                (series_id,)
            )

            for _, row in df.iterrows():
                cursor.execute("""
                    INSERT INTO fred_observations (
                        series_id,
                        indicator_name,
                        date,
                        value
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    series_id,
                    indicator_name,
                    str(row["date"]),
                    None if pd.isna(row["value"]) else float(row["value"]),
                ))

            conn.commit()

    def get_indicator(self, series_id: str):
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM fred_observations
                WHERE series_id = ?
                ORDER BY date
            """, (series_id,))

            return [dict(row) for row in cursor.fetchall()]