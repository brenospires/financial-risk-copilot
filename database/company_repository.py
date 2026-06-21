from pathlib import Path

from config.settings import DATABASE_PATH
from data_models.company import Company
from database.base_repository import BaseRepository


class CompanyRepository(BaseRepository):
    def __init__(self, db_path: str | Path = DATABASE_PATH) -> None:
        super().__init__(db_path)

    def create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    market TEXT NOT NULL,
                    name TEXT NOT NULL,
                    country TEXT,
                    sector TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (provider_id) REFERENCES data_providers(id)
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_identity
                ON companies (
                    provider_id,
                    LOWER(market),
                    UPPER(ticker)
                )
                """
            )

    def upsert(self, company: Company) -> Company:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM companies
                WHERE provider_id = ?
                  AND market = ? COLLATE NOCASE
                  AND ticker = ? COLLATE NOCASE
                """,
                (company.provider_id, company.market, company.ticker),
            ).fetchone()

            if existing:
                company_id = existing["id"]
                connection.execute(
                    """
                    UPDATE companies
                    SET provider_id = ?,
                        ticker = ?,
                        market = ?,
                        name = ?,
                        country = ?,
                        sector = ?,
                        active = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        company.provider_id,
                        company.ticker,
                        company.market,
                        company.name,
                        company.country,
                        company.sector,
                        company.active,
                        company_id,
                    ),
                )
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO companies (
                        provider_id,
                        ticker,
                        market,
                        name,
                        country,
                        sector,
                        active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        company.provider_id,
                        company.ticker,
                        company.market,
                        company.name,
                        company.country,
                        company.sector,
                        company.active,
                    ),
                )
                company_id = cursor.lastrowid

            row = connection.execute(
                """
                SELECT
                    id,
                    provider_id,
                    ticker,
                    market,
                    name,
                    country,
                    sector,
                    active
                FROM companies
                WHERE id = ?
                """,
                (company_id,),
            ).fetchone()

        return self._to_model(row)

    def get_by_id(self, company_id: int) -> Company | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    provider_id,
                    ticker,
                    market,
                    name,
                    country,
                    sector,
                    active
                FROM companies
                WHERE id = ?
                """,
                (company_id,),
            ).fetchone()

        return self._to_model(row) if row else None

    @staticmethod
    def _to_model(row: object) -> Company:
        return Company(
            id=row["id"],
            provider_id=row["provider_id"],
            ticker=row["ticker"],
            market=row["market"],
            name=row["name"],
            country=row["country"],
            sector=row["sector"],
            active=bool(row["active"]),
        )
