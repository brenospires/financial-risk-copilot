from pathlib import Path

from config.settings import DATABASE_PATH
from database.company_repository import CompanyRepository
from database.company_source_repository import CompanySourceRepository
from database.financial_statement_repository import FinancialStatementRepository
from database.provider_repository import DataProviderRepository


def initialize_database(db_path: str | Path = DATABASE_PATH) -> None:
    repositories = (
        DataProviderRepository(db_path),
        CompanyRepository(db_path),
        CompanySourceRepository(db_path),
        FinancialStatementRepository(db_path),
    )

    for repository in repositories:
        repository.create_table()
