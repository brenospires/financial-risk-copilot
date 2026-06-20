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
                    name TEXT NOT NULL,
                    country TEXT,
                    industry TEXT,
                    sector TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_identity
                ON companies (LOWER(name), COALESCE(country, ''))
                """
            )

    def upsert(self, company: Company) -> Company:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM companies
                WHERE name = ? COLLATE NOCASE
                  AND COALESCE(country, '') = COALESCE(?, '')
                """,
                (company.name, company.country),
            ).fetchone()

            if existing:
                company_id = existing["id"]
                connection.execute(
                    """
                    UPDATE companies
                    SET name = ?,
                        country = ?,
                        industry = ?,
                        sector = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        company.name,
                        company.country,
                        company.industry,
                        company.sector,
                        company_id,
                    ),
                )
            else:
                cursor = connection.execute(
                    """
                    INSERT INTO companies (name, country, industry, sector)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        company.name,
                        company.country,
                        company.industry,
                        company.sector,
                    ),
                )
                company_id = cursor.lastrowid

            row = connection.execute(
                """
                SELECT id, name, country, industry, sector
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
                SELECT id, name, country, industry, sector
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
            name=row["name"],
            country=row["country"],
            industry=row["industry"],
            sector=row["sector"],
        )
