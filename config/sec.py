"""Static SEC provider configuration."""

from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency

BASE_SEC_URL = "https://www.sec.gov"
BASE_DATA_URL = "https://data.sec.gov"

ANNUAL_FORMS = frozenset({"10-K"})
SUPPORTED_FREQUENCIES = frozenset({TimeSeriesFrequency.ANNUAL})

MINIMUM_ANNUAL_DURATION_DAYS = 300
MAXIMUM_ANNUAL_DURATION_DAYS = 400

SNAPSHOT_MEASURES = frozenset(
    {
        FinancialStatementMeasure.ASSETS,
        FinancialStatementMeasure.CURRENT_ASSETS,
        FinancialStatementMeasure.CASH,
        FinancialStatementMeasure.INVENTORY,
        FinancialStatementMeasure.ACCOUNTS_RECEIVABLE,
        FinancialStatementMeasure.LIABILITIES,
        FinancialStatementMeasure.CURRENT_LIABILITIES,
        FinancialStatementMeasure.DEBT,
        FinancialStatementMeasure.LONG_TERM_DEBT,
        FinancialStatementMeasure.ACCOUNTS_PAYABLE,
        FinancialStatementMeasure.EQUITY,
        FinancialStatementMeasure.RETAINED_EARNINGS,
        FinancialStatementMeasure.WORKING_CAPITAL,
    }
)

PERIOD_MEASURES = frozenset(
    {
        FinancialStatementMeasure.REVENUE,
        FinancialStatementMeasure.GROSS_PROFIT,
        FinancialStatementMeasure.OPERATING_INCOME,
        FinancialStatementMeasure.NET_INCOME,
        FinancialStatementMeasure.EBIT,
        FinancialStatementMeasure.EBITDA,
        FinancialStatementMeasure.INTEREST_EXPENSE,
        FinancialStatementMeasure.OPERATING_CASH_FLOW,
        FinancialStatementMeasure.CAPITAL_EXPENDITURES,
        FinancialStatementMeasure.FREE_CASH_FLOW,
    }
)

MEASURE_CANDIDATES: dict[FinancialStatementMeasure, tuple[str, ...]] = {
    FinancialStatementMeasure.ASSETS: ("Assets",),
    FinancialStatementMeasure.CURRENT_ASSETS: ("AssetsCurrent",),
    FinancialStatementMeasure.CASH: (
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ),
    FinancialStatementMeasure.INVENTORY: ("InventoryNet",),
    FinancialStatementMeasure.ACCOUNTS_RECEIVABLE: (
        "AccountsReceivableNetCurrent",
    ),
    FinancialStatementMeasure.LIABILITIES: ("Liabilities",),
    FinancialStatementMeasure.CURRENT_LIABILITIES: ("LiabilitiesCurrent",),
    FinancialStatementMeasure.DEBT: (
        "LongTermDebtAndFinanceLeaseObligations",
    ),
    FinancialStatementMeasure.LONG_TERM_DEBT: (
        "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
        "LongTermDebtNoncurrent",
        "LongTermDebt",
    ),
    FinancialStatementMeasure.ACCOUNTS_PAYABLE: ("AccountsPayableCurrent",),
    FinancialStatementMeasure.EQUITY: (
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ),
    FinancialStatementMeasure.RETAINED_EARNINGS: (
        "RetainedEarningsAccumulatedDeficit",
    ),
    FinancialStatementMeasure.WORKING_CAPITAL: ("WorkingCapital",),
    FinancialStatementMeasure.REVENUE: (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    FinancialStatementMeasure.GROSS_PROFIT: ("GrossProfit",),
    FinancialStatementMeasure.OPERATING_INCOME: ("OperatingIncomeLoss",),
    FinancialStatementMeasure.NET_INCOME: ("NetIncomeLoss",),
    FinancialStatementMeasure.EBIT: (),
    FinancialStatementMeasure.EBITDA: (),
    FinancialStatementMeasure.INTEREST_EXPENSE: (
        "InterestExpenseNonOperating",
        "InterestExpense",
    ),
    FinancialStatementMeasure.OPERATING_CASH_FLOW: (
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ),
    FinancialStatementMeasure.CAPITAL_EXPENDITURES: (
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ),
    FinancialStatementMeasure.FREE_CASH_FLOW: (),
}

AUXILIARY_CANDIDATES: dict[str, tuple[str, ...]] = {
    "current_debt": (
        "ShortTermBorrowings",
        "ShortTermDebt",
        "LongTermDebtCurrent",
        "LongTermDebtAndFinanceLeaseObligationsCurrent",
    ),
    "noncurrent_debt": (
        "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
        "LongTermDebtNoncurrent",
    ),
    "pretax_income": (
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
    ),
    "depreciation_and_amortization": (
        "DepreciationDepletionAndAmortization",
        "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
        "DepreciationAndAmortization",
    ),
}

AUXILIARY_OBSERVATION_TYPES = {
    "current_debt": ObservationType.SNAPSHOT,
    "noncurrent_debt": ObservationType.SNAPSHOT,
    "pretax_income": ObservationType.PERIOD,
    "depreciation_and_amortization": ObservationType.PERIOD,
}
