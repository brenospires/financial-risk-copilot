from typing import Dict, Any, Optional


class FinancialRatios:
    """
    Computes basic financial ratios from SEC metrics.

    Expected input:
    List of dictionaries returned by SECRepository.get_metrics(ticker)
    """

    def __init__(self, metrics: list[Dict[str, Any]]):
        self.metrics = metrics
        self.metric_map = self._build_metric_map()

    def _build_metric_map(self) -> Dict[str, Optional[float]]:
        metric_map = {}

        for row in self.metrics:
            metric_name = row.get("metric_name")
            value = row.get("value")

            if metric_name:
                metric_map[metric_name] = value

        return metric_map

    def _get(self, metric_name: str) -> Optional[float]:
        return self.metric_map.get(metric_name)

    def _safe_divide(
        self,
        numerator: Optional[float],
        denominator: Optional[float],
    ) -> Optional[float]:

        if numerator is None or denominator is None:
            return None

        if denominator == 0:
            return None

        return numerator / denominator

    def calculate(self) -> Dict[str, Optional[float]]:
        assets = self._get("assets")
        liabilities = self._get("liabilities")
        equity = self._get("equity")
        revenue = self._get("revenue")
        net_income = self._get("net_income")
        current_assets = self._get("current_assets")
        current_liabilities = self._get("current_liabilities")
        cash = self._get("cash")
        debt = self._get("debt")
        operating_income = self._get("operating_income")
        interest_expense = self._get("interest_expense")

        ratios = {
            "current_ratio": self._safe_divide(
                current_assets,
                current_liabilities,
            ),
            "debt_to_equity": self._safe_divide(
                debt,
                equity,
            ),
            "debt_to_assets": self._safe_divide(
                debt,
                assets,
            ),
            "equity_ratio": self._safe_divide(
                equity,
                assets,
            ),
            "net_margin": self._safe_divide(
                net_income,
                revenue,
            ),
            "return_on_assets": self._safe_divide(
                net_income,
                assets,
            ),
            "return_on_equity": self._safe_divide(
                net_income,
                equity,
            ),
            "operating_margin": self._safe_divide(
                operating_income,
                revenue,
            ),
            "interest_coverage": self._safe_divide(
                operating_income,
                interest_expense,
            ),
            "cash_to_assets": self._safe_divide(
                cash,
                assets,
            ),
            "liabilities_to_assets": self._safe_divide(
                liabilities,
                assets,
            ),
        }

        return ratios