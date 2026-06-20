from pathlib import Path

from config.settings import DATABASE_PATH
from data_models.provider import DataProvider
from databases.base_repository import BaseRepository


class DataProviderRepository(BaseRepository):
    def __init__(self, db_path: str | Path = DATABASE_PATH) -> None:
        super().__init__(db_path)

    def create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS data_providers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def upsert(self, provider: DataProvider) -> DataProvider:
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO data_providers (name, active)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    active = excluded.active,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, name, active
                """,
                (provider.name, provider.active),
            ).fetchone()

        return self._to_model(row)

    def get_by_id(self, provider_id: int) -> DataProvider | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, name, active
                FROM data_providers
                WHERE id = ?
                """,
                (provider_id,),
            ).fetchone()

        return self._to_model(row) if row else None

    def get_by_name(self, name: str) -> DataProvider | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, name, active
                FROM data_providers
                WHERE name = ? COLLATE NOCASE
                """,
                (name.strip(),),
            ).fetchone()

        return self._to_model(row) if row else None

    @staticmethod
    def _to_model(row: object) -> DataProvider:
        return DataProvider(
            id=row["id"],
            name=row["name"],
            active=bool(row["active"]),
        )
