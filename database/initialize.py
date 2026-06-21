from pathlib import Path

from config.settings import DATABASE_PATH
from config.system_defaults import DEFAULT_DATA_PROVIDERS
from database.company_repository import CompanyRepository
from database.financial_statement_repository import FinancialStatementRepository
from database.data_provider_repository import DataProviderRepository


def initialize_database(db_path: str | Path = DATABASE_PATH) -> None:
    repositories = (
        DataProviderRepository(db_path),
        CompanyRepository(db_path),
        FinancialStatementRepository(db_path),
    )

    for repository in repositories:
        repository.create_table()

    provider_repository = DataProviderRepository(db_path)

    for provider in DEFAULT_DATA_PROVIDERS:
        provider_repository.upsert(provider)
