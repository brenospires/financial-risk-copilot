from enum import Enum


class DataDomain(str, Enum):
    COMPANY = "company"
    FINANCIAL_STATEMENT = "financial_statement"
    MACROECONOMICS = "macroeconomics"
