from data_models.data_domain import DataDomain
from data_models.data_provider import DataProvider
from database.base_repository import BaseRepository


class DataProviderRepository(BaseRepository):
    def create_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS data_providers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE,
                    data_domains TEXT NOT NULL,
                    supported_frequencies TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (name)
                )
                """
            )

    def upsert(self, provider: DataProvider) -> DataProvider:
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO data_providers (
                    id,
                    name,
                    data_domains,
                    supported_frequencies,
                    active
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    data_domains = excluded.data_domains,
                    supported_frequencies = excluded.supported_frequencies,
                    active = excluded.active,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING
                    id,
                    name,
                    data_domains,
                    supported_frequencies,
                    active
                """,
                (
                    provider.id,
                    provider.name,
                    ",".join(
                        sorted(domain.value for domain in provider.data_domains)
                    ),
                    (
                        ",".join(
                            sorted(
                                frequency.value
                                for frequency in provider.supported_frequencies
                            )
                        )
                        if provider.supported_frequencies is not None
                        else None
                    ),
                    provider.active,
                ),
            ).fetchone()

        return self._to_model(row)

    def get_by_id(self, provider_id: int) -> DataProvider | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    name,
                    data_domains,
                    supported_frequencies,
                    active
                FROM data_providers
                WHERE id = ?
                """,
                (provider_id,),
            ).fetchone()

        return self._to_model(row) if row else None

    def get_by_name_and_domain(
        self,
        name: str,
        data_domain: DataDomain,
    ) -> DataProvider | None:
        provider = self.get_by_name(name)

        if provider is None or data_domain not in provider.data_domains:
            return None

        return provider

    def get_by_name(self, name: str) -> DataProvider | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    name,
                    data_domains,
                    supported_frequencies,
                    active
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
            data_domains=set(row["data_domains"].split(",")),
            supported_frequencies=(
                set(row["supported_frequencies"].split(","))
                if row["supported_frequencies"] is not None
                else None
            ),
            active=bool(row["active"]),
        )
