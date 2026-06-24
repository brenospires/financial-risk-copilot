"""Company financial metric calculations for the current snapshot."""

import pandas as pd

from utils.dataframe import get_single_row_value
from utils.numeric import (
    divide_or_none,
    absolute_or_none,
    subtract_or_none,
)


class CompanyMetrics:
    """
    Calculate company metrics from one current financial-statement snapshot.

    The public method expects a one-row DataFrame containing the most recent
    adjusted financial measures. Missing, null, non-numeric, or zero-denominator
    inputs produce ``None`` instead of fabricated metric values.
    """

    METRIC_COLUMNS = (
        "cash_ratio",
        "net_margin",
        "quick_ratio",
        "equity_ratio",
        "gross_margin",
        "current_ratio",
        "ebitda_margin",
        "debt_to_assets",
        "debt_to_equity",
        "operating_margin",
        "return_on_assets",
        "return_on_equity",
        "interest_coverage",
        "net_debt_to_ebitda",
        "liabilities_to_assets",
        "free_cash_flow_margin",
        "free_cash_flow_to_debt",
        "working_capital_to_assets",
        "operating_cash_flow_margin",
        "retained_earnings_to_assets",
        "operating_cash_flow_to_net_income",
    )

    def calculate_metrics(
        self,
        dt_current: pd.DataFrame,
    ) -> dict[str, float | None]:
        """Calculate financial metrics for one current snapshot row."""

        if len(dt_current) != 1:
            raise ValueError(
                "Calculate metrics expects a snapshot of financial metrics records"
        )

        cash_ratio = self._calculate_cash_ratio(
            get_single_row_value(dt_current, "cash"),
            get_single_row_value(dt_current, "current_liabilities"),
        )
        net_margin = self._calculate_net_margin(
            get_single_row_value(dt_current, "net_income"),
            get_single_row_value(dt_current, "revenue"),
        )
        quick_ratio = self._calculate_quick_ratio(
            get_single_row_value(dt_current, "current_assets"),
            get_single_row_value(dt_current, "inventory"),
            get_single_row_value(dt_current, "current_liabilities"),
        )
        equity_ratio = self._calculate_equity_ratio(
            get_single_row_value(dt_current, "equity"),
            get_single_row_value(dt_current, "assets"),
        )
        gross_margin = self._calculate_gross_margin(
            get_single_row_value(dt_current, "gross_profit"),
            get_single_row_value(dt_current, "revenue"),
        )
        current_ratio = self._calculate_current_ratio(
            get_single_row_value(dt_current, "current_assets"),
            get_single_row_value(dt_current, "current_liabilities"),
        )
        ebitda_margin = self._calculate_ebitda_margin(
            get_single_row_value(dt_current, "ebitda"),
            get_single_row_value(dt_current, "revenue"),
        )
        debt_to_assets = self._calculate_debt_to_assets(
            get_single_row_value(dt_current, "debt"),
            get_single_row_value(dt_current, "assets"),
        )
        debt_to_equity = self._calculate_debt_to_equity(
            get_single_row_value(dt_current, "debt"),
            get_single_row_value(dt_current, "equity"),
        )
        operating_margin = self._calculate_operating_margin(
            get_single_row_value(dt_current, "operating_income"),
            get_single_row_value(dt_current, "revenue"),
        )
        return_on_assets = self._calculate_return_on_assets(
            get_single_row_value(dt_current, "net_income"),
            get_single_row_value(dt_current, "assets"),
        )
        return_on_equity = self._calculate_return_on_equity(
            get_single_row_value(dt_current, "net_income"),
            get_single_row_value(dt_current, "equity"),
        )
        interest_coverage = self._calculate_interest_coverage(
            get_single_row_value(dt_current, "ebit"),
            get_single_row_value(dt_current, "interest_expense"),
        )
        net_debt_to_ebitda = self._calculate_net_debt_to_ebitda(
            get_single_row_value(dt_current, "debt"),
            get_single_row_value(dt_current, "cash"),
            get_single_row_value(dt_current, "ebitda"),
        )
        liabilities_to_assets = self._calculate_liabilities_to_assets(
            get_single_row_value(dt_current, "liabilities"),
            get_single_row_value(dt_current, "assets"),
        )
        free_cash_flow_margin = self._calculate_free_cash_flow_margin(
            get_single_row_value(dt_current, "free_cash_flow"),
            get_single_row_value(dt_current, "revenue"),
        )
        free_cash_flow_to_debt = self._calculate_free_cash_flow_to_debt(
            get_single_row_value(dt_current, "free_cash_flow"),
            get_single_row_value(dt_current, "debt"),
        )
        working_capital_to_assets = self._calculate_working_capital_to_assets(
            get_single_row_value(dt_current, "working_capital"),
            get_single_row_value(dt_current, "assets"),
        )
        operating_cash_flow_margin = (
            self._calculate_operating_cash_flow_margin(
                get_single_row_value(dt_current, "operating_cash_flow"),
                get_single_row_value(dt_current, "revenue"),
            )
        )
        retained_earnings_to_assets = (
            self._calculate_retained_earnings_to_assets(
                get_single_row_value(dt_current, "retained_earnings"),
                get_single_row_value(dt_current, "assets"),
            )
        )
        operating_cash_flow_to_net_income = (
            self._calculate_operating_cash_flow_to_net_income(
                get_single_row_value(dt_current, "operating_cash_flow"),
                get_single_row_value(dt_current, "net_income"),
            )
        )

        metrics = {
            "cash_ratio": cash_ratio,
            "net_margin": net_margin,
            "quick_ratio": quick_ratio,
            "equity_ratio": equity_ratio,
            "gross_margin": gross_margin,
            "current_ratio": current_ratio,
            "ebitda_margin": ebitda_margin,
            "debt_to_assets": debt_to_assets,
            "debt_to_equity": debt_to_equity,
            "operating_margin": operating_margin,
            "return_on_assets": return_on_assets,
            "return_on_equity": return_on_equity,
            "interest_coverage": interest_coverage,
            "net_debt_to_ebitda": net_debt_to_ebitda,
            "liabilities_to_assets": liabilities_to_assets,
            "free_cash_flow_margin": free_cash_flow_margin,
            "free_cash_flow_to_debt": free_cash_flow_to_debt,
            "working_capital_to_assets": working_capital_to_assets,
            "operating_cash_flow_margin": operating_cash_flow_margin,
            "retained_earnings_to_assets": retained_earnings_to_assets,
            "operating_cash_flow_to_net_income": (
                operating_cash_flow_to_net_income
            ),
        }

        return metrics

    def _calculate_cash_ratio(
        self,
        cash: object,
        current_liabilities: object,
    ) -> float | None:
        """Calculate cash divided by current liabilities."""

        return divide_or_none(cash, current_liabilities)

    def _calculate_net_margin(
        self,
        net_income: object,
        revenue: object,
    ) -> float | None:
        """Calculate net income divided by revenue."""

        return divide_or_none(net_income, revenue)

    def _calculate_quick_ratio(
        self,
        current_assets: object,
        inventory: object,
        current_liabilities: object,
    ) -> float | None:
        """Calculate inventory-adjusted assets over current liabilities."""

        quick_assets = subtract_or_none(current_assets, inventory)

        return divide_or_none(quick_assets, current_liabilities)

    def _calculate_equity_ratio(
        self,
        equity: object,
        assets: object,
    ) -> float | None:
        """Calculate equity divided by total assets."""

        return divide_or_none(equity, assets)

    def _calculate_gross_margin(
        self,
        gross_profit: object,
        revenue: object,
    ) -> float | None:
        """Calculate gross profit divided by revenue."""

        return divide_or_none(gross_profit, revenue)

    def _calculate_current_ratio(
        self,
        current_assets: object,
        current_liabilities: object,
    ) -> float | None:
        """Calculate current assets divided by current liabilities."""

        return divide_or_none(current_assets, current_liabilities)

    def _calculate_ebitda_margin(
        self,
        ebitda: object,
        revenue: object,
    ) -> float | None:
        """Calculate EBITDA divided by revenue."""

        return divide_or_none(ebitda, revenue)

    def _calculate_debt_to_assets(
        self,
        debt: object,
        assets: object,
    ) -> float | None:
        """Calculate total debt divided by total assets."""

        return divide_or_none(debt, assets)

    def _calculate_debt_to_equity(
        self,
        debt: object,
        equity: object,
    ) -> float | None:
        """Calculate total debt divided by equity."""

        return divide_or_none(debt, equity)

    def _calculate_operating_margin(
        self,
        operating_income: object,
        revenue: object,
    ) -> float | None:
        """Calculate operating income divided by revenue."""

        return divide_or_none(operating_income, revenue)

    def _calculate_return_on_assets(
        self,
        net_income: object,
        assets: object,
    ) -> float | None:
        """Calculate net income divided by total assets."""

        return divide_or_none(net_income, assets)

    def _calculate_return_on_equity(
        self,
        net_income: object,
        equity: object,
    ) -> float | None:
        """Calculate net income divided by equity."""

        return divide_or_none(net_income, equity)

    def _calculate_interest_coverage(
        self,
        ebit: object,
        interest_expense: object,
    ) -> float | None:
        """Calculate EBIT divided by the absolute interest expense."""

        return divide_or_none(ebit, absolute_or_none(interest_expense))

    def _calculate_net_debt_to_ebitda(
        self,
        debt: object,
        cash: object,
        ebitda: object,
    ) -> float | None:
        """Calculate debt net of cash divided by EBITDA."""

        net_debt = subtract_or_none(debt, cash)

        return divide_or_none(net_debt, ebitda)

    def _calculate_liabilities_to_assets(
        self,
        liabilities: object,
        assets: object,
    ) -> float | None:
        """Calculate total liabilities divided by total assets."""

        return divide_or_none(liabilities, assets)

    def _calculate_free_cash_flow_margin(
        self,
        free_cash_flow: object,
        revenue: object,
    ) -> float | None:
        """Calculate free cash flow divided by revenue."""

        return divide_or_none(free_cash_flow, revenue)

    def _calculate_free_cash_flow_to_debt(
        self,
        free_cash_flow: object,
        debt: object,
    ) -> float | None:
        """Calculate free cash flow divided by total debt."""

        return divide_or_none(free_cash_flow, debt)

    def _calculate_working_capital_to_assets(
        self,
        working_capital: object,
        assets: object,
    ) -> float | None:
        """Calculate working capital divided by total assets."""

        return divide_or_none(working_capital, assets)

    def _calculate_operating_cash_flow_margin(
        self,
        operating_cash_flow: object,
        revenue: object,
    ) -> float | None:
        """Calculate operating cash flow divided by revenue."""

        return divide_or_none(operating_cash_flow, revenue)

    def _calculate_retained_earnings_to_assets(
        self,
        retained_earnings: object,
        assets: object,
    ) -> float | None:
        """Calculate retained earnings divided by total assets."""

        return divide_or_none(retained_earnings, assets)

    def _calculate_operating_cash_flow_to_net_income(
        self,
        operating_cash_flow: object,
        net_income: object,
    ) -> float | None:
        """Calculate operating cash flow divided by net income."""

        return divide_or_none(operating_cash_flow, net_income)
