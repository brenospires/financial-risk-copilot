from datetime import date
from pathlib import Path

from config.settings import DATABASE_PATH
from data_models.financial_statement import FinancialStatement
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency
from database.base_repository import BaseRepository


class FinancialStatementRepository(BaseRepository):
    def __init__(self, db_path: str | Path = DATABASE_PATH) -> None:
        super().__init__(db_path)

    def create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS financial_statements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_id INTEGER NOT NULL,
                    company_id INTEGER,
                    ticker TEXT NOT NULL,
                    market TEXT NOT NULL,
                    measure TEXT NOT NULL,
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
                    FOREIGN KEY (provider_id) REFERENCES data_providers(id),
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_financial_statements_identity
                ON financial_statements (
                    provider_id,
                    UPPER(ticker),
                    LOWER(market),
                    measure,
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
                WHERE provider_id = ?
                  AND ticker = ? COLLATE NOCASE
                  AND market = ? COLLATE NOCASE
                  AND measure = ?
                  AND frequency = ?
                  AND observation_type = ?
                  AND COALESCE(start_date, '') = COALESCE(?, '')
                  AND end_date = ?
                  AND unit = ?
                """,
                (
                    statement.provider_id,
                    statement.ticker,
                    statement.market,
                    statement.measure.value,
                    statement.frequency.value,
                    statement.observation_type.value,
                    start_date,
                    end_date,
                    statement.unit,
                ),
            ).fetchone()

            values = (
                statement.provider_id,
                statement.company_id,
                statement.ticker,
                statement.market,
                statement.measure.value,
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
                    SET provider_id = ?,
                        company_id = ?,
                        ticker = ?,
                        market = ?,
                        measure = ?,
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
                        provider_id,
                        company_id,
                        ticker,
                        market,
                        measure,
                        value,
                        unit,
                        observation_type,
                        frequency,
                        start_date,
                        end_date,
                        fiscal_year,
                        fiscal_period
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ticker: str,
        market: str,
        frequency: TimeSeriesFrequency,
        start_date: date | None = None,
        end_date: date | None = None,
        measures: list[FinancialStatementMeasure] | None = None,
    ) -> list[FinancialStatement]:
        """
        Retrieve statements for a snapshot or time-series request.

        When only start_date is provided, it represents the exact snapshot
        date. When both dates are provided, they define an inclusive time-series
        range. Requests without start_date are invalid.
        """

        if start_date is None:
            raise ValueError("start_date is required")

        if (
            start_date is not None
            and end_date is not None
            and start_date > end_date
        ):
            raise ValueError("start_date cannot be after end_date")

        query = """
            SELECT
                id,
                provider_id,
                company_id,
                ticker,
                market,
                measure,
                value,
                unit,
                observation_type,
                frequency,
                start_date,
                end_date,
                fiscal_year,
                fiscal_period
            FROM financial_statements
            WHERE ticker = ? COLLATE NOCASE
              AND market = ? COLLATE NOCASE
              AND frequency = ?
        """
        parameters: list[object] = [
            ticker,
            market,
            frequency.value,
        ]

        if end_date is None:
            query += " AND end_date = ?"
            parameters.append(start_date.isoformat())

        if end_date is not None:
            query += " AND end_date >= ?"
            parameters.append(start_date.isoformat())
            query += " AND end_date <= ?"
            parameters.append(end_date.isoformat())

        if measures:
            placeholders = ", ".join("?" for _ in measures)
            query += f" AND measure IN ({placeholders})"
            parameters.extend(measure.value for measure in measures)

        query += " ORDER BY end_date, measure"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [self._to_model(row) for row in rows]

    @staticmethod
    def _select_by_id(connection: object, statement_id: int) -> object:
        return connection.execute(
            """
            SELECT
                id,
                provider_id,
                company_id,
                ticker,
                market,
                measure,
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
            provider_id=row["provider_id"],
            company_id=row["company_id"],
            ticker=row["ticker"],
            market=row["market"],
            measure=row["measure"],
            value=row["value"],
            unit=row["unit"],
            observation_type=row["observation_type"],
            frequency=row["frequency"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            fiscal_year=row["fiscal_year"],
            fiscal_period=row["fiscal_period"],
        )
