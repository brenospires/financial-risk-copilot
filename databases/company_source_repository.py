from pathlib import Path

from config.settings import DATABASE_PATH
from data_models.company_source import CompanySource
from databases.base_repository import BaseRepository


class CompanySourceRepository(BaseRepository):
    def __init__(self, db_path: str | Path = DATABASE_PATH) -> None:
        super().__init__(db_path)

    def create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS company_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    provider_id INTEGER NOT NULL,
                    provider_company_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    market TEXT NOT NULL,
                    exchange TEXT,
                    currency TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(id),
                    FOREIGN KEY (provider_id) REFERENCES data_providers(id)
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_company_sources_identity
                ON company_sources (
                    provider_id,
                    LOWER(market),
                    UPPER(ticker)
                )
                """
            )

    def upsert(self, source: CompanySource) -> CompanySource:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM company_sources
                WHERE provider_id = ?
                  AND market = ? COLLATE NOCASE
                  AND ticker = ? COLLATE NOCASE
                """,
                (source.provider_id, source.market, source.ticker),
            ).fetchone()

            values = (
                source.company_id,
                source.provider_id,
                source.provider_company_id,
                source.ticker,
                source.market,
                source.exchange,
                source.currency,
                source.active,
            )

            if existing:
                source_id = existing["id"]
                connection.execute(
                    """
                    UPDATE company_sources
                    SET company_id = ?,
                        provider_id = ?,
                        provider_company_id = ?,
                        ticker = ?,
                        market = ?,
                        exchange = ?,
                        currency = ?,
                        active = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (*values, source_id),
                )
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO company_sources (
                        company_id,
                        provider_id,
                        provider_company_id,
                        ticker,
                        market,
                        exchange,
                        currency,
                        active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
                source_id = cursor.lastrowid

            row = connection.execute(
                """
                SELECT
                    id,
                    company_id,
                    provider_id,
                    provider_company_id,
                    ticker,
                    market,
                    exchange,
                    currency,
                    active
                FROM company_sources
                WHERE id = ?
                """,
                (source_id,),
            ).fetchone()

        return self._to_model(row)

    def get_by_id(self, source_id: int) -> CompanySource | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    company_id,
                    provider_id,
                    provider_company_id,
                    ticker,
                    market,
                    exchange,
                    currency,
                    active
                FROM company_sources
                WHERE id = ?
                """,
                (source_id,),
            ).fetchone()

        return self._to_model(row) if row else None

    @staticmethod
    def _to_model(row: object) -> CompanySource:
        return CompanySource(
            id=row["id"],
            company_id=row["company_id"],
            provider_id=row["provider_id"],
            provider_company_id=row["provider_company_id"],
            ticker=row["ticker"],
            market=row["market"],
            exchange=row["exchange"],
            currency=row["currency"],
            active=bool(row["active"]),
        )
