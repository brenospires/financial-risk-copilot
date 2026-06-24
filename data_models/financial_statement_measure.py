from enum import Enum


class FinancialStatementMeasure(str, Enum):
    ASSETS = "assets"
    CURRENT_ASSETS = "current_assets"
    CASH = "cash"
    INVENTORY = "inventory"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"

    LIABILITIES = "liabilities"
    CURRENT_LIABILITIES = "current_liabilities"
    DEBT = "debt"
    LONG_TERM_DEBT = "long_term_debt"
    ACCOUNTS_PAYABLE = "accounts_payable"

    EQUITY = "equity"
    RETAINED_EARNINGS = "retained_earnings"
    WORKING_CAPITAL = "working_capital"

    REVENUE = "revenue"
    GROSS_PROFIT = "gross_profit"
    OPERATING_INCOME = "operating_income"
    NET_INCOME = "net_income"
    EBIT = "ebit"
    EBITDA = "ebitda"
    INTEREST_EXPENSE = "interest_expense"

    OPERATING_CASH_FLOW = "operating_cash_flow"
    CAPITAL_EXPENDITURES = "capital_expenditures"
    FREE_CASH_FLOW = "free_cash_flow"


class FinancialStatementMeasureType(str, Enum):
    FLOW = "flow"
    OTHER = "other"
    BALANCE_SHEET = "balance_sheet"


FINANCIAL_STATEMENT_MEASURE_INFO = {
    FinancialStatementMeasure.ASSETS: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "contextual",
    },
    FinancialStatementMeasure.CURRENT_ASSETS: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.CASH: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.INVENTORY: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "contextual",
    },
    FinancialStatementMeasure.ACCOUNTS_RECEIVABLE: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "contextual",
    },
    FinancialStatementMeasure.LIABILITIES: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "lower_better",
    },
    FinancialStatementMeasure.CURRENT_LIABILITIES: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "lower_better",
    },
    FinancialStatementMeasure.DEBT: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "lower_better",
    },
    FinancialStatementMeasure.LONG_TERM_DEBT: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "lower_better",
    },
    FinancialStatementMeasure.ACCOUNTS_PAYABLE: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "contextual",
    },
    FinancialStatementMeasure.EQUITY: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.RETAINED_EARNINGS: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.WORKING_CAPITAL: {
        "measure_type": FinancialStatementMeasureType.BALANCE_SHEET,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.REVENUE: {
        "measure_type": FinancialStatementMeasureType.FLOW,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.GROSS_PROFIT: {
        "measure_type": FinancialStatementMeasureType.FLOW,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.OPERATING_INCOME: {
        "measure_type": FinancialStatementMeasureType.FLOW,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.NET_INCOME: {
        "measure_type": FinancialStatementMeasureType.FLOW,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.EBIT: {
        "measure_type": FinancialStatementMeasureType.FLOW,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.EBITDA: {
        "measure_type": FinancialStatementMeasureType.FLOW,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.INTEREST_EXPENSE: {
        "measure_type": FinancialStatementMeasureType.FLOW,
        "risk_direction": "lower_better",
    },
    FinancialStatementMeasure.OPERATING_CASH_FLOW: {
        "measure_type": FinancialStatementMeasureType.FLOW,
        "risk_direction": "higher_better",
    },
    FinancialStatementMeasure.CAPITAL_EXPENDITURES: {
        "measure_type": FinancialStatementMeasureType.FLOW,
        "risk_direction": "contextual",
    },
    FinancialStatementMeasure.FREE_CASH_FLOW: {
        "measure_type": FinancialStatementMeasureType.FLOW,
        "risk_direction": "higher_better",
    },
}
