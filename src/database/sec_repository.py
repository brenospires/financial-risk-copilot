import sqlite3
from typing import Any, Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.settings import DATABASE_PATH

class SECRepository:
    """
    SQLite repository for normalized SEC data.

    This repository only handles persistence.
    It does not call the SEC API.
    It does not normalize SEC facts.
    It does not calculate financial ratios or risk scores.
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
        Create the required SEC tables if they do not exist.
        """

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    ticker TEXT PRIMARY KEY,
                    cik TEXT,
                    company_name TEXT,
                    sic TEXT,
                    sic_description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sec_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT,
                    cik TEXT,
                    metric_name TEXT,
                    sec_metric_name TEXT,
                    value REAL,
                    fiscal_year INTEGER,
                    fiscal_period TEXT,
                    end_date TEXT,
                    form TEXT,
                    filed TEXT,
                    unit TEXT,
                    frame TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            conn.commit()

    def _ensure_schema_compatibility(self) -> None:
        """
        Add missing columns if the database was created by an older version
        of the project.

        This keeps local development easier because you do not need to delete
        the SQLite file every time the schema evolves.
        """

        self._add_column_if_missing("companies", "company_name", "TEXT")
        self._add_column_if_missing("companies", "sic", "TEXT")
        self._add_column_if_missing("companies", "sic_description", "TEXT")
        self._add_column_if_missing(
            "companies",
            "created_at",
            "TEXT DEFAULT CURRENT_TIMESTAMP",
        )
        self._add_column_if_missing(
            "companies",
            "updated_at",
            "TEXT DEFAULT CURRENT_TIMESTAMP",
        )

        self._add_column_if_missing("sec_metrics", "cik", "TEXT")
        self._add_column_if_missing("sec_metrics", "unit", "TEXT")
        self._add_column_if_missing("sec_metrics", "frame", "TEXT")
        self._add_column_if_missing(
            "sec_metrics",
            "created_at",
            "TEXT DEFAULT CURRENT_TIMESTAMP",
        )
        self._add_column_if_missing(
            "sec_metrics",
            "updated_at",
            "TEXT DEFAULT CURRENT_TIMESTAMP",
        )

        self._migrate_company_name_if_needed()

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

    def _migrate_company_name_if_needed(self) -> None:
        """
        Copy old companies.name values into companies.company_name when the
        database was created with the previous schema.
        """

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(companies)")
            existing_columns = {
                row["name"]
                for row in cursor.fetchall()
            }

            if "name" not in existing_columns:
                return

            cursor.execute(
                """
                UPDATE companies
                SET company_name = name
                WHERE company_name IS NULL
                  AND name IS NOT NULL
                """
            )

            conn.commit()

    def save_company(self, company: dict[str, Any]) -> None:
        """
        Insert or update company metadata.

        Expected input:
        {
            "ticker": "AAPL",
            "cik": "0000320193",
            "company_name": "Apple Inc.",
            "sic": "3571",
            "sic_description": "Electronic Computers",
            "updated_at": "..."
        }

        created_at is preserved on update.
        updated_at is refreshed on update.
        """

        ticker = str(company["ticker"]).upper().strip()

        with self._connect() as conn:
            cursor = conn.cursor()

            existing = cursor.execute(
                """
                SELECT ticker
                FROM companies
                WHERE ticker = ?
                """,
                (ticker,),
            ).fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE companies
                    SET
                        cik = ?,
                        company_name = ?,
                        sic = ?,
                        sic_description = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE ticker = ?
                    """,
                    (
                        company.get("cik"),
                        company.get("company_name"),
                        company.get("sic"),
                        company.get("sic_description"),
                        ticker,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO companies (
                        ticker,
                        cik,
                        company_name,
                        sic,
                        sic_description,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (
                        ticker,
                        company.get("cik"),
                        company.get("company_name"),
                        company.get("sic"),
                        company.get("sic_description"),
                    ),
                )

            conn.commit()

    def get_company(self, ticker: str) -> Optional[dict[str, Any]]:
        """
        Return company metadata for one ticker.
        """

        ticker = ticker.upper().strip()

        with self._connect() as conn:
            cursor = conn.cursor()

            row = cursor.execute(
                """
                SELECT
                    ticker,
                    cik,
                    company_name,
                    sic,
                    sic_description,
                    created_at,
                    updated_at
                FROM companies
                WHERE ticker = ?
                """,
                (ticker,),
            ).fetchone()

            if row is None:
                return None

            return dict(row)

    def save_metrics(self, metrics: list[dict[str, Any]]) -> None:
        """
        Insert or update normalized SEC metric rows.

        Expected input:
        [
            {
                "ticker": "AAPL",
                "cik": "0000320193",
                "metric_name": "revenue",
                "sec_metric_name": "RevenueFromContractWithCustomerExcludingAssessedTax",
                "value": 391035000000,
                "fiscal_year": 2024,
                "fiscal_period": "FY",
                "end_date": "2024-09-28",
                "form": "10-K",
                "filed": "2024-11-01",
                "unit": "USD",
                "frame": "CY2024"
            }
        ]

        created_at is preserved on update.
        updated_at is refreshed on update.
        """

        if not metrics:
            return

        with self._connect() as conn:
            cursor = conn.cursor()

            for metric in metrics:
                ticker = str(metric["ticker"]).upper().strip()

                existing = cursor.execute(
                    """
                    SELECT id
                    FROM sec_metrics
                    WHERE ticker = ?
                      AND metric_name = ?
                      AND COALESCE(fiscal_year, -1) = COALESCE(?, -1)
                      AND COALESCE(fiscal_period, '') = COALESCE(?, '')
                      AND COALESCE(end_date, '') = COALESCE(?, '')
                    LIMIT 1
                    """,
                    (
                        ticker,
                        metric.get("metric_name"),
                        metric.get("fiscal_year"),
                        metric.get("fiscal_period"),
                        metric.get("end_date"),
                    ),
                ).fetchone()

                if existing:
                    cursor.execute(
                        """
                        UPDATE sec_metrics
                        SET
                            cik = ?,
                            sec_metric_name = ?,
                            value = ?,
                            form = ?,
                            filed = ?,
                            unit = ?,
                            frame = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (
                            metric.get("cik"),
                            metric.get("sec_metric_name"),
                            metric.get("value"),
                            metric.get("form"),
                            metric.get("filed"),
                            metric.get("unit"),
                            metric.get("frame"),
                            existing["id"],
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO sec_metrics (
                            ticker,
                            cik,
                            metric_name,
                            sec_metric_name,
                            value,
                            fiscal_year,
                            fiscal_period,
                            end_date,
                            form,
                            filed,
                            unit,
                            frame,
                            created_at,
                            updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (
                            ticker,
                            metric.get("cik"),
                            metric.get("metric_name"),
                            metric.get("sec_metric_name"),
                            metric.get("value"),
                            metric.get("fiscal_year"),
                            metric.get("fiscal_period"),
                            metric.get("end_date"),
                            metric.get("form"),
                            metric.get("filed"),
                            metric.get("unit"),
                            metric.get("frame"),
                        ),
                    )

            conn.commit()

    def get_metrics(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Return normalized SEC metrics for one ticker.

        If start_date and/or end_date are provided, filter by end_date.
        """

        ticker = ticker.upper().strip()

        query = """
            SELECT
                id,
                ticker,
                cik,
                metric_name,
                sec_metric_name,
                value,
                fiscal_year,
                fiscal_period,
                end_date,
                form,
                filed,
                unit,
                frame,
                created_at,
                updated_at
            FROM sec_metrics
            WHERE ticker = ?
        """

        params: list[Any] = [ticker]

        if start_date is not None:
            query += " AND end_date >= ?"
            params.append(start_date)

        if end_date is not None:
            query += " AND end_date <= ?"
            params.append(end_date)

        query += """
            ORDER BY
                end_date,
                fiscal_year,
                fiscal_period,
                metric_name
        """

        with self._connect() as conn:
            cursor = conn.cursor()

            rows = cursor.execute(query, params).fetchall()

            return [dict(row) for row in rows]