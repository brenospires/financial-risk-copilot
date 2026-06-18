import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, Optional

class SECRepository:
    """
    Simple SQLite repository for SEC data.

    This is intentionally lightweight.
    The goal is persistence for the portfolio project, not production-grade storage.
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
                CREATE TABLE IF NOT EXISTS companies (
                    ticker TEXT PRIMARY KEY,
                    cik TEXT,
                    name TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sec_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT,
                    metric_name TEXT,
                    sec_metric_name TEXT,
                    value REAL,
                    fiscal_year INTEGER,
                    fiscal_period TEXT,
                    end_date TEXT,
                    form TEXT,
                    filed TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sec_filings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT,
                    accession_number TEXT,
                    filing_date TEXT,
                    report_date TEXT,
                    form TEXT,
                    primary_document TEXT,
                    primary_doc_description TEXT,
                    filing_text TEXT
                )
            """)

            conn.commit()

    def save_company(self, ticker: str, cik: str, name: str):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO companies (
                    ticker, cik, name
                )
                VALUES (?, ?, ?)
            """, (ticker, cik, name))

            conn.commit()

    def save_metrics(self, ticker: str, metrics: Dict[str, Optional[Dict[str, Any]]]):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM sec_metrics WHERE ticker = ?",
                (ticker,)
            )

            for metric_name, metric_data in metrics.items():
                if metric_data is None:
                    continue

                cursor.execute("""
                    INSERT INTO sec_metrics (
                        ticker,
                        metric_name,
                        sec_metric_name,
                        value,
                        fiscal_year,
                        fiscal_period,
                        end_date,
                        form,
                        filed
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker,
                    metric_name,
                    metric_data.get("sec_metric_name"),
                    metric_data.get("value"),
                    metric_data.get("fiscal_year"),
                    metric_data.get("fiscal_period"),
                    metric_data.get("end_date"),
                    metric_data.get("form"),
                    metric_data.get("filed"),
                ))

            conn.commit()

    def save_filing(self, ticker: str, filing: Dict[str, Any], filing_text: str):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO sec_filings (
                    ticker,
                    accession_number,
                    filing_date,
                    report_date,
                    form,
                    primary_document,
                    primary_doc_description,
                    filing_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                filing.get("accession_number"),
                filing.get("filing_date"),
                filing.get("report_date"),
                filing.get("form"),
                filing.get("primary_document"),
                filing.get("primary_doc_description"),
                filing_text,
            ))

            conn.commit()

    def get_metrics(self, ticker: str):
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM sec_metrics
                WHERE ticker = ?
            """, (ticker,))

            return [dict(row) for row in cursor.fetchall()]