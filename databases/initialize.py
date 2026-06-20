from pathlib import Path

from config.settings import DATABASE_PATH
from databases.company_repository import CompanyRepository
from databases.company_source_repository import CompanySourceRepository
from databases.financial_statement_repository import FinancialStatementRepository
from databases.provider_repository import DataProviderRepository


def initialize_database(db_path: str | Path = DATABASE_PATH) -> None:
    repositories = (
        DataProviderRepository(db_path),
        CompanyRepository(db_path),
        CompanySourceRepository(db_path),
        FinancialStatementRepository(db_path),
    )

    for repository in repositories:
        repository.create_table()
