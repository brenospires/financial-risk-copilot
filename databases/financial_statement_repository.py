from datetime import date
from pathlib import Path

from config.settings import DATABASE_PATH
from data_models.financial_item import FinancialItem
from data_models.financial_statement import FinancialStatement
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency
from databases.base_repository import BaseRepository


class FinancialStatementRepository(BaseRepository):
    def __init__(self, db_path: str | Path = DATABASE_PATH) -> None:
        super().__init__(db_path)

    def create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS financial_statements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_source_id INTEGER NOT NULL,
                    item TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    observation_type TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT NOT NULL,
                    fiscal_year INTEGER NOT NULL,
                    fiscal_period TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_source_id) REFERENCES company_sources(id)
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_financial_statements_identity
                ON financial_statements (
                    company_source_id,
                    item,
                    frequency,
                    observation_type,
                    COALESCE(start_date, ''),
                    end_date,
                    unit
                )
                """
            )

    def upsert(self, statement: FinancialStatement) -> FinancialStatement:
        start_date = self._serialize_date(statement.start_date)
        end_date = statement.end_date.isoformat()

        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM financial_statements
                WHERE company_source_id = ?
                  AND item = ?
                  AND frequency = ?
                  AND observation_type = ?
                  AND COALESCE(start_date, '') = COALESCE(?, '')
                  AND end_date = ?
                  AND unit = ?
                """,
                (
                    statement.company_source_id,
                    statement.item.value,
                    statement.frequency.value,
                    statement.observation_type.value,
                    start_date,
                    end_date,
                    statement.unit,
                ),
            ).fetchone()

            values = (
                statement.company_source_id,
                statement.item.value,
                statement.value,
                statement.unit,
                statement.observation_type.value,
                statement.frequency.value,
                start_date,
                end_date,
                statement.fiscal_year,
                statement.fiscal_period,
            )

            if existing:
                statement_id = existing["id"]
                connection.execute(
                    """
                    UPDATE financial_statements
                    SET company_source_id = ?,
                        item = ?,
                        value = ?,
                        unit = ?,
                        observation_type = ?,
                        frequency = ?,
                        start_date = ?,
                        end_date = ?,
                        fiscal_year = ?,
                        fiscal_period = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (*values, statement_id),
                )
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO financial_statements (
                        company_source_id,
                        item,
                        value,
                        unit,
                        observation_type,
                        frequency,
                        start_date,
                        end_date,
                        fiscal_year,
                        fiscal_period
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
                statement_id = cursor.lastrowid

            row = self._select_by_id(connection, statement_id)

        return self._to_model(row)

    def get_by_id(self, statement_id: int) -> FinancialStatement | None:
        with self._connect() as connection:
            row = self._select_by_id(connection, statement_id)

        return self._to_model(row) if row else None

    def get_for_period(
        self,
        company_source_id: int,
        frequency: TimeSeriesFrequency,
        start_date: date | None = None,
        end_date: date | None = None,
        items: list[FinancialItem] | None = None,
    ) -> list[FinancialStatement]:
        query = """
            SELECT
                id,
                company_source_id,
                item,
                value,
                unit,
                observation_type,
                frequency,
                start_date,
                end_date,
                fiscal_year,
                fiscal_period
            FROM financial_statements
            WHERE company_source_id = ?
              AND frequency = ?
        """
        parameters: list[object] = [company_source_id, frequency.value]

        if start_date is not None:
            query += " AND end_date >= ?"
            parameters.append(start_date.isoformat())

        if end_date is not None:
            query += " AND end_date <= ?"
            parameters.append(end_date.isoformat())

        if items:
            placeholders = ", ".join("?" for _ in items)
            query += f" AND item IN ({placeholders})"
            parameters.extend(item.value for item in items)

        query += " ORDER BY end_date, item"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [self._to_model(row) for row in rows]

    @staticmethod
    def _select_by_id(connection: object, statement_id: int) -> object:
        return connection.execute(
            """
            SELECT
                id,
                company_source_id,
                item,
                value,
                unit,
                observation_type,
                frequency,
                start_date,
                end_date,
                fiscal_year,
                fiscal_period
            FROM financial_statements
            WHERE id = ?
            """,
            (statement_id,),
        ).fetchone()

    @staticmethod
    def _serialize_date(value: date | None) -> str | None:
        return value.isoformat() if value else None

    @staticmethod
    def _to_model(row: object) -> FinancialStatement:
        return FinancialStatement(
            id=row["id"],
            company_source_id=row["company_source_id"],
            item=row["item"],
            value=row["value"],
            unit=row["unit"],
            observation_type=row["observation_type"],
            frequency=row["frequency"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            fiscal_year=row["fiscal_year"],
            fiscal_period=row["fiscal_period"],
        )
