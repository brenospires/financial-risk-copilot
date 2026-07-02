import sys
import sqlite3
from pathlib import Path
from typing import Any, Optional

sys.path.append(str(Path(__file__).resolve().parents[2]))
from config.settings import DATABASE_PATH

class FREDRepository:
    """
    SQLite repository for normalized FRED data.

    This repository only handles persistence.
    It does not call the FRED API.
    It does not calculate macro summaries or risk interpretation.
    """

    def __init__(self) -> None:
        self.db_path = DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_tables()
        self._ensure_schema_compatibility()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self) -> None:
        """
        Create the required FRED tables if they do not exist.
        """

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fred_indicators (
                    series_id TEXT PRIMARY KEY,
                    indicator_name TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fred_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    series_id TEXT,
                    indicator_name TEXT,
                    date TEXT,
                    value REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(series_id, date)
                )
                """
            )

            conn.commit()

    def _ensure_schema_compatibility(self) -> None:
        """
        Add missing columns if the database was created by an older version
        of the project.
        """

        self._add_column_if_missing(
            table_name="fred_observations",
            column_name="created_at",
            column_type="TEXT DEFAULT CURRENT_TIMESTAMP",
        )

        self._add_column_if_missing(
            table_name="fred_observations",
            column_name="updated_at",
            column_type="TEXT DEFAULT CURRENT_TIMESTAMP",
        )

    def _add_column_if_missing(
        self,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> None:
        """
        Add a column to an existing table if it does not already exist.
        """

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {
                row["name"]
                for row in cursor.fetchall()
            }

            if column_name in existing_columns:
                return

            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )

            conn.commit()

    def save_indicator_metadata(
        self,
        series_id: str,
        indicator_name: str,
    ) -> None:
        """
        Insert or update FRED indicator metadata.

        created_at is preserved on update.
        updated_at is refreshed on update.
        """

        series_id = series_id.upper().strip()

        with self._connect() as conn:
            cursor = conn.cursor()

            existing = cursor.execute(
                """
                SELECT series_id
                FROM fred_indicators
                WHERE series_id = ?
                """,
                (series_id,),
            ).fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE fred_indicators
                    SET
                        indicator_name = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE series_id = ?
                    """,
                    (
                        indicator_name,
                        series_id,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO fred_indicators (
                        series_id,
                        indicator_name,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (
                        series_id,
                        indicator_name,
                    ),
                )

            conn.commit()

    def get_indicator_metadata(
        self,
        series_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Return metadata for one FRED indicator.
        """

        series_id = series_id.upper().strip()

        with self._connect() as conn:
            cursor = conn.cursor()

            row = cursor.execute(
                """
                SELECT
                    series_id,
                    indicator_name,
                    created_at,
                    updated_at
                FROM fred_indicators
                WHERE series_id = ?
                """,
                (series_id,),
            ).fetchone()

            if row is None:
                return None

            return dict(row)

    def save_observations(
        self,
        observations: list[dict[str, Any]],
    ) -> None:
        """
        Insert or update normalized FRED observations.

        Expected input:
        [
            {
                "series_id": "GDP",
                "indicator_name": "Gross Domestic Product",
                "date": "2024-01-01",
                "value": 28624.069
            }
        ]

        created_at is preserved on update.
        updated_at is refreshed on update.
        """

        if not observations:
            return

        with self._connect() as conn:
            cursor = conn.cursor()

            for observation in observations:
                series_id = str(observation["series_id"]).upper().strip()
                date = str(observation["date"])

                existing = cursor.execute(
                    """
                    SELECT id
                    FROM fred_observations
                    WHERE series_id = ?
                      AND date = ?
                    LIMIT 1
                    """,
                    (
                        series_id,
                        date,
                    ),
                ).fetchone()

                if existing:
                    cursor.execute(
                        """
                        UPDATE fred_observations
                        SET
                            indicator_name = ?,
                            value = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (
                            observation.get("indicator_name"),
                            observation.get("value"),
                            existing["id"],
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO fred_observations (
                            series_id,
                            indicator_name,
                            date,
                            value,
                            created_at,
                            updated_at
                        )
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (
                            series_id,
                            observation.get("indicator_name"),
                            date,
                            observation.get("value"),
                        ),
                    )

            conn.commit()

    def get_observations(
        self,
        series_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Return FRED observations for one series.

        If start_date and/or end_date are provided, filter by date.
        """

        series_id = series_id.upper().strip()

        query = """
            SELECT
                id,
                series_id,
                indicator_name,
                date,
                value,
                created_at,
                updated_at
            FROM fred_observations
            WHERE series_id = ?
        """

        params: list[Any] = [series_id]

        if start_date is not None:
            query += " AND date >= ?"
            params.append(start_date)

        if end_date is not None:
            query += " AND date <= ?"
            params.append(end_date)

        query += """
            ORDER BY date
        """

        with self._connect() as conn:
            cursor = conn.cursor()

            rows = cursor.execute(query, params).fetchall()

            return [dict(row) for row in rows]

    def get_coverage(
        self,
        series_id: str,
    ) -> dict[str, Any]:
        """
        Return stored observation coverage for one FRED series.
        """

        series_id = series_id.upper().strip()

        with self._connect() as conn:
            cursor = conn.cursor()

            row = cursor.execute(
                """
                SELECT
                    MIN(date) AS first_observation_date,
                    MAX(date) AS latest_observation_date,
                    COUNT(*) AS observation_count
                FROM fred_observations
                WHERE series_id = ?
                """,
                (series_id,),
            ).fetchone()

            return {
                "series_id": series_id,
                "first_observation_date": row["first_observation_date"],
                "latest_observation_date": row["latest_observation_date"],
                "observation_count": row["observation_count"],
            }