from enum import Enum


class FinancialItem(str, Enum):
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
    SHARES_OUTSTANDING = "shares_outstanding"
