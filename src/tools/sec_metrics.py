from typing import Any, Dict, List, Optional


MetricValue = Dict[str, Any]


class SECMetricExtractor:
    """
    Extracts useful financial metrics from SEC company facts.

    The SEC company facts object is large and inconsistent across companies.
    This class searches for common US-GAAP metric names and returns the most
    recent annual values.
    """

    METRIC_CANDIDATES = {

        # Income Statement
        "revenue": [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet",
        ],

        "net_income": ["NetIncomeLoss"],
        "operating_income": ["OperatingIncomeLoss"],
        "gross_profit": ["GrossProfit"],

        "interest_expense": [
            "InterestExpenseNonOperating",
            "InterestExpense",
        ],

        # Balance Sheet
        "assets": ["Assets"],
        "current_assets": ["AssetsCurrent"],
        "liabilities": ["Liabilities"],
        "current_liabilities": ["LiabilitiesCurrent"],

        "equity": [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ],

        "cash": [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ],

        "inventory": ["InventoryNet"],
        "accounts_receivable": ["AccountsReceivableNetCurrent"],
        "accounts_payable": ["AccountsPayableCurrent"],
        "retained_earnings": ["RetainedEarningsAccumulatedDeficit"],
        "working_capital": ["WorkingCapital"],

        # Debt
        "debt": [
            "LongTermDebt",
            "LongTermDebtCurrent",
            "ShortTermBorrowings",
            "ShortTermDebt",
            "LongTermDebtAndFinanceLeaseObligations",
            "LongTermDebtAndFinanceLeaseObligationsCurrent",
            "ShortTermBorrowingsAndFinanceLeaseObligations",
        ],

        "long_term_debt": [
            "LongTermDebt",
            "LongTermDebtAndFinanceLeaseObligations",
        ],

        # Cash Flow Statement
        "operating_cash_flow": [
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        ],

        "capital_expenditures": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
        ],

        "free_cash_flow": ["FreeCashFlow"],

        # Altman Z Score
        "ebit": [
            "OperatingIncomeLoss",
        ],

        # Shares
        "shares_outstanding": [
            "CommonStockSharesOutstanding",
            "EntityCommonStockSharesOutstanding",
        ],
    }

    def __init__(self, facts: Dict[str, Any]):
        self.facts = facts
        self.us_gaap = facts.get("facts", {}).get("us-gaap", {})

    def _get_fact_units(self, metric_name: str) -> Optional[Dict[str, List[MetricValue]]]:
        metric = self.us_gaap.get(metric_name)

        if not metric:
            return None

        return metric.get("units")

    def _get_usd_values(self, metric_name: str) -> List[MetricValue]:
        units = self._get_fact_units(metric_name)

        if not units:
            return []

        if "USD" in units:
            return units["USD"]

        if "shares" in units:
            return units["shares"]

        return []

    def _filter_annual_values(self, values: List[MetricValue]) -> List[MetricValue]:
        annual_values = []

        for item in values:
            form = item.get("form")
            fiscal_year = item.get("fy")
            fiscal_period = item.get("fp")
            value = item.get("val")
            end_date = item.get("end")

            if (
                form == "10-K"
                and fiscal_year is not None
                and fiscal_period == "FY"
                and value is not None
                and end_date is not None
            ):
                annual_values.append(item)

        return annual_values

    def _get_latest_annual_value(self, metric_name: str) -> Optional[MetricValue]:
        values = self._get_usd_values(metric_name)
        annual_values = self._filter_annual_values(values)

        if not annual_values:
            return None

        annual_values = sorted(
            annual_values,
            key=lambda x: x.get("end", ""),
            reverse=True,
        )

        return annual_values[0]

    def get_metric(self, metric_key: str) -> Optional[MetricValue]:
        candidates = self.METRIC_CANDIDATES.get(metric_key, [])

        for candidate in candidates:
            latest_value = self._get_latest_annual_value(candidate)

            if latest_value:
                return {
                    "metric": metric_key,
                    "sec_metric_name": candidate,
                    "value": latest_value.get("val"),
                    "fiscal_year": latest_value.get("fy"),
                    "fiscal_period": latest_value.get("fp"),
                    "end_date": latest_value.get("end"),
                    "form": latest_value.get("form"),
                    "filed": latest_value.get("filed"),
                }

        return None

    def extract_all_metrics(self) -> Dict[str, Optional[MetricValue]]:
        extracted_metrics = {}

        for metric_key in self.METRIC_CANDIDATES.keys():
            extracted_metrics[metric_key] = self.get_metric(metric_key)

        return extracted_metrics