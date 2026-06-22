"""Company financial-statement snapshot and trend metric calculations."""

import pandas as pd

from data_models.financial_statement import FinancialStatement
from data_models.financial_statement_measure import FinancialStatementMeasure
from utils.numeric import safe_divide
from utils.time_series import pivot_time_series


class CompanyMetrics:
    """
    Calculate company metrics from canonical financial statements.

    The public snapshot method always receives ``list[FinancialStatement]``.
    It converts those long-form observations into one wide row per reporting
    end date, preserves every supported raw measure, and appends every
    calculated metric as a nullable column.

    Missing observations are expected. Calculations never substitute zero for
    missing data, and zero denominators produce ``pd.NA``. Provider retrieval,
    persistence, risk scoring, peer comparison, and written analysis remain
    outside this class. ``company_id`` may be absent because some providers may
    not resolve a persisted company record for every market.
    """

    GROUP_COLUMNS = (
        "provider_id",
        "ticker",
        "market",
        "unit",
        "frequency",
    )

    RAW_MEASURE_COLUMNS = tuple(
        measure.value
        for measure in FinancialStatementMeasure
    )

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

    def calculate_snapshots(
        self,
        statements: list[FinancialStatement],
    ) -> pd.DataFrame:
        """
        Calculate one wide financial metric row per reporting period.

        The input must contain at least one statement and describe one provider,
        ticker, market, unit, and reporting frequency. Fiscal labels are not
        part of row identity because comparative SEC facts may carry a later
        filing's fiscal context. Missing measures remain nullable cells.
        Duplicate canonical observations are rejected by the shared time-series
        pivot instead of being aggregated silently.
        """

        self._validate_statements(statements)

        records = [
            statement.model_dump(mode="json")
            for statement in statements
        ]
        result = pivot_time_series(
            records,
            values="value",
            columns="measure",
            timestamp="end_date",
            group_columns=self.GROUP_COLUMNS,
            expected_columns=self.RAW_MEASURE_COLUMNS,
        )

        result["cash_ratio"] = self._calculate_cash_ratio(
            result["cash"],
            result["current_liabilities"],
        )
        result["net_margin"] = self._calculate_net_margin(
            result["net_income"],
            result["revenue"],
        )
        result["quick_ratio"] = self._calculate_quick_ratio(
            result["current_assets"],
            result["inventory"],
            result["current_liabilities"],
        )
        result["equity_ratio"] = self._calculate_equity_ratio(
            result["equity"],
            result["assets"],
        )
        result["gross_margin"] = self._calculate_gross_margin(
            result["gross_profit"],
            result["revenue"],
        )
        result["current_ratio"] = self._calculate_current_ratio(
            result["current_assets"],
            result["current_liabilities"],
        )
        result["ebitda_margin"] = self._calculate_ebitda_margin(
            result["ebitda"],
            result["revenue"],
        )
        result["debt_to_assets"] = self._calculate_debt_to_assets(
            result["debt"],
            result["assets"],
        )
        result["debt_to_equity"] = self._calculate_debt_to_equity(
            result["debt"],
            result["equity"],
        )
        result["operating_margin"] = self._calculate_operating_margin(
            result["operating_income"],
            result["revenue"],
        )
        result["return_on_assets"] = self._calculate_return_on_assets(
            result["net_income"],
            result["assets"],
        )
        result["return_on_equity"] = self._calculate_return_on_equity(
            result["net_income"],
            result["equity"],
        )
        result["interest_coverage"] = self._calculate_interest_coverage(
            result["ebit"],
            result["interest_expense"],
        )
        result["net_debt_to_ebitda"] = self._calculate_net_debt_to_ebitda(
            result["debt"],
            result["cash"],
            result["ebitda"],
        )
        result["liabilities_to_assets"] = (
            self._calculate_liabilities_to_assets(
                result["liabilities"],
                result["assets"],
            )
        )
        result["free_cash_flow_margin"] = (
            self._calculate_free_cash_flow_margin(
                result["free_cash_flow"],
                result["revenue"],
            )
        )
        result["free_cash_flow_to_debt"] = (
            self._calculate_free_cash_flow_to_debt(
                result["free_cash_flow"],
                result["debt"],
            )
        )
        result["working_capital_to_assets"] = (
            self._calculate_working_capital_to_assets(
                result["working_capital"],
                result["assets"],
            )
        )
        result["operating_cash_flow_margin"] = (
            self._calculate_operating_cash_flow_margin(
                result["operating_cash_flow"],
                result["revenue"],
            )
        )
        result["retained_earnings_to_assets"] = (
            self._calculate_retained_earnings_to_assets(
                result["retained_earnings"],
                result["assets"],
            )
        )
        result["operating_cash_flow_to_net_income"] = (
            self._calculate_operating_cash_flow_to_net_income(
                result["operating_cash_flow"],
                result["net_income"],
            )
        )

        return result

    def calculate_trend(
        self,
        snapshots: pd.DataFrame,
    ) -> pd.DataFrame:
        """Calculate financial trends after the trend contract is approved."""

        pass

    def _validate_statements(
        self,
        statements: list[FinancialStatement],
    ) -> None:
        """Validate the company and reporting context of statement inputs."""

        if not statements:
            raise ValueError("Financial statements are required")

        providers = {statement.provider_id for statement in statements}
        frequencies = {statement.frequency for statement in statements}
        tickers = {statement.ticker for statement in statements}
        markets = {statement.market.casefold() for statement in statements}
        units = {statement.unit.casefold() for statement in statements}

        contexts = (
            (providers, "provider"),
            (tickers, "ticker"),
            (markets, "market"),
            (units, "unit"),
            (frequencies, "frequency"),
        )

        for values, name in contexts:
            if len(values) > 1:
                raise ValueError(
                    f"Financial statements must use one {name}"
                )

    def _calculate_cash_ratio(
        self,
        cash: pd.Series,
        current_liabilities: pd.Series,
    ) -> pd.Series:
        """Calculate cash divided by current liabilities."""

        return safe_divide(cash, current_liabilities)

    def _calculate_net_margin(
        self,
        net_income: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate net income divided by revenue."""

        return safe_divide(net_income, revenue)

    def _calculate_quick_ratio(
        self,
        current_assets: pd.Series,
        inventory: pd.Series,
        current_liabilities: pd.Series,
    ) -> pd.Series:
        """Calculate inventory-adjusted assets over current liabilities."""

        return safe_divide(
            current_assets - inventory,
            current_liabilities,
        )

    def _calculate_equity_ratio(
        self,
        equity: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate equity divided by total assets."""

        return safe_divide(equity, assets)

    def _calculate_gross_margin(
        self,
        gross_profit: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate gross profit divided by revenue."""

        return safe_divide(gross_profit, revenue)

    def _calculate_current_ratio(
        self,
        current_assets: pd.Series,
        current_liabilities: pd.Series,
    ) -> pd.Series:
        """Calculate current assets divided by current liabilities."""

        return safe_divide(current_assets, current_liabilities)

    def _calculate_ebitda_margin(
        self,
        ebitda: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate EBITDA divided by revenue."""

        return safe_divide(ebitda, revenue)

    def _calculate_debt_to_assets(
        self,
        debt: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate total debt divided by total assets."""

        return safe_divide(debt, assets)

    def _calculate_debt_to_equity(
        self,
        debt: pd.Series,
        equity: pd.Series,
    ) -> pd.Series:
        """Calculate total debt divided by equity."""

        return safe_divide(debt, equity)

    def _calculate_operating_margin(
        self,
        operating_income: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate operating income divided by revenue."""

        return safe_divide(operating_income, revenue)

    def _calculate_return_on_assets(
        self,
        net_income: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate net income divided by total assets."""

        return safe_divide(net_income, assets)

    def _calculate_return_on_equity(
        self,
        net_income: pd.Series,
        equity: pd.Series,
    ) -> pd.Series:
        """Calculate net income divided by equity."""

        return safe_divide(net_income, equity)

    def _calculate_interest_coverage(
        self,
        ebit: pd.Series,
        interest_expense: pd.Series,
    ) -> pd.Series:
        """Calculate EBIT divided by the absolute interest expense."""

        return safe_divide(ebit, interest_expense.abs())

    def _calculate_net_debt_to_ebitda(
        self,
        debt: pd.Series,
        cash: pd.Series,
        ebitda: pd.Series,
    ) -> pd.Series:
        """Calculate debt net of cash divided by EBITDA."""

        return safe_divide(debt - cash, ebitda)

    def _calculate_liabilities_to_assets(
        self,
        liabilities: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate total liabilities divided by total assets."""

        return safe_divide(liabilities, assets)

    def _calculate_free_cash_flow_margin(
        self,
        free_cash_flow: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate free cash flow divided by revenue."""

        return safe_divide(free_cash_flow, revenue)

    def _calculate_free_cash_flow_to_debt(
        self,
        free_cash_flow: pd.Series,
        debt: pd.Series,
    ) -> pd.Series:
        """Calculate free cash flow divided by total debt."""

        return safe_divide(free_cash_flow, debt)

    def _calculate_working_capital_to_assets(
        self,
        working_capital: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate working capital divided by total assets."""

        return safe_divide(working_capital, assets)

    def _calculate_operating_cash_flow_margin(
        self,
        operating_cash_flow: pd.Series,
        revenue: pd.Series,
    ) -> pd.Series:
        """Calculate operating cash flow divided by revenue."""

        return safe_divide(operating_cash_flow, revenue)

    def _calculate_retained_earnings_to_assets(
        self,
        retained_earnings: pd.Series,
        assets: pd.Series,
    ) -> pd.Series:
        """Calculate retained earnings divided by total assets."""

        return safe_divide(retained_earnings, assets)

    def _calculate_operating_cash_flow_to_net_income(
        self,
        operating_cash_flow: pd.Series,
        net_income: pd.Series,
    ) -> pd.Series:
        """Calculate operating cash flow divided by net income."""

        return safe_divide(operating_cash_flow, net_income)
