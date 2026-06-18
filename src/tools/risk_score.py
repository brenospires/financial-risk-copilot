from typing import Dict, Optional, Any


class FinancialRiskScore:
    """
    Multi-factor financial risk score.

    The model returns a score from 0 to 100.
    Higher score means higher estimated financial risk.

    This project uses a general cross-industry scorecard to keep the portfolio
    implementation simple and interpretable. In real-world risk systems,
    different models should be built for different industries, since capital
    structure, margins, liquidity needs, asset intensity, and cash-flow dynamics
    vary significantly across sectors.
    """

    COMPONENT_WEIGHTS = {
        "liquidity": 0.20,
        "leverage": 0.25,
        "profitability": 0.25,
        "cash_flow": 0.15,
        "distress": 0.15,
    }

    def __init__(
        self,
        ratios: Dict[str, Optional[float]],
        metrics: Optional[Dict[str, Optional[float]]] = None,
    ):
        self.ratios = ratios
        self.metrics = metrics or {}

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

    def _clip(
        self,
        value: float,
        lower: float = 0.0,
        upper: float = 100.0,
    ) -> float:
        return max(lower, min(value, upper))

    def _score_positive_ratio(
        self,
        value: Optional[float],
        strong: float,
        weak: float,
    ) -> Optional[float]:
        """
        For ratios where higher is better.

        strong or above -> 0 risk points
        weak or below   -> 100 risk points
        """

        if value is None:
            return None

        if value >= strong:
            return 0.0

        if value <= weak:
            return 100.0

        return 100.0 * (strong - value) / (strong - weak)

    def _score_negative_ratio(
        self,
        value: Optional[float],
        strong: float,
        weak: float,
    ) -> Optional[float]:
        """
        For ratios where lower is better.

        strong or below -> 0 risk points
        weak or above   -> 100 risk points
        """

        if value is None:
            return None

        if value <= strong:
            return 0.0

        if value >= weak:
            return 100.0

        return 100.0 * (value - strong) / (weak - strong)

    def _average_available(self, values: list[Optional[float]]) -> Optional[float]:
        available_values = [
            value
            for value in values
            if value is not None
        ]

        if not available_values:
            return None

        return sum(available_values) / len(available_values)

    def _get_ratio(self, name: str) -> Optional[float]:
        return self.ratios.get(name)

    def _get_metric(self, name: str) -> Optional[float]:
        return self.metrics.get(name)

    def calculate_liquidity_score(self) -> Dict[str, Any]:
        current_ratio = self._get_ratio("current_ratio")
        cash_to_assets = self._get_ratio("cash_to_assets")

        current_ratio_score = self._score_positive_ratio(
            value=current_ratio,
            strong=2.0,
            weak=1.0,
        )

        cash_to_assets_score = self._score_positive_ratio(
            value=cash_to_assets,
            strong=0.15,
            weak=0.03,
        )

        score = self._average_available([
            current_ratio_score,
            cash_to_assets_score,
        ])

        return {
            "score": score,
            "metrics": {
                "current_ratio": current_ratio,
                "cash_to_assets": cash_to_assets,
            },
            "signals": self._build_signals({
                "current_ratio": current_ratio_score,
                "cash_to_assets": cash_to_assets_score,
            }),
        }

    def calculate_leverage_score(self) -> Dict[str, Any]:
        debt_to_equity = self._get_ratio("debt_to_equity")
        debt_to_assets = self._get_ratio("debt_to_assets")
        liabilities_to_assets = self._get_ratio("liabilities_to_assets")
        interest_coverage = self._get_ratio("interest_coverage")

        debt_to_equity_score = self._score_negative_ratio(
            value=debt_to_equity,
            strong=0.5,
            weak=2.5,
        )

        debt_to_assets_score = self._score_negative_ratio(
            value=debt_to_assets,
            strong=0.25,
            weak=0.70,
        )

        liabilities_to_assets_score = self._score_negative_ratio(
            value=liabilities_to_assets,
            strong=0.40,
            weak=0.80,
        )

        interest_coverage_score = self._score_positive_ratio(
            value=interest_coverage,
            strong=8.0,
            weak=2.0,
        )

        score = self._average_available([
            debt_to_equity_score,
            debt_to_assets_score,
            liabilities_to_assets_score,
            interest_coverage_score,
        ])

        return {
            "score": score,
            "metrics": {
                "debt_to_equity": debt_to_equity,
                "debt_to_assets": debt_to_assets,
                "liabilities_to_assets": liabilities_to_assets,
                "interest_coverage": interest_coverage,
            },
            "signals": self._build_signals({
                "debt_to_equity": debt_to_equity_score,
                "debt_to_assets": debt_to_assets_score,
                "liabilities_to_assets": liabilities_to_assets_score,
                "interest_coverage": interest_coverage_score,
            }),
        }

    def calculate_profitability_score(self) -> Dict[str, Any]:
        net_margin = self._get_ratio("net_margin")
        operating_margin = self._get_ratio("operating_margin")
        return_on_assets = self._get_ratio("return_on_assets")
        return_on_equity = self._get_ratio("return_on_equity")

        net_margin_score = self._score_positive_ratio(
            value=net_margin,
            strong=0.15,
            weak=0.00,
        )

        operating_margin_score = self._score_positive_ratio(
            value=operating_margin,
            strong=0.20,
            weak=0.00,
        )

        return_on_assets_score = self._score_positive_ratio(
            value=return_on_assets,
            strong=0.10,
            weak=0.00,
        )

        return_on_equity_score = self._score_positive_ratio(
            value=return_on_equity,
            strong=0.15,
            weak=0.00,
        )

        score = self._average_available([
            net_margin_score,
            operating_margin_score,
            return_on_assets_score,
            return_on_equity_score,
        ])

        return {
            "score": score,
            "metrics": {
                "net_margin": net_margin,
                "operating_margin": operating_margin,
                "return_on_assets": return_on_assets,
                "return_on_equity": return_on_equity,
            },
            "signals": self._build_signals({
                "net_margin": net_margin_score,
                "operating_margin": operating_margin_score,
                "return_on_assets": return_on_assets_score,
                "return_on_equity": return_on_equity_score,
            }),
        }

    def calculate_cash_flow_score(self) -> Dict[str, Any]:
        operating_cash_flow = self._get_metric("operating_cash_flow")
        capital_expenditures = self._get_metric("capital_expenditures")
        revenue = self._get_metric("revenue")
        liabilities = self._get_metric("liabilities")

        free_cash_flow = None
        if operating_cash_flow is not None and capital_expenditures is not None:
            free_cash_flow = operating_cash_flow - abs(capital_expenditures)

        operating_cash_flow_margin = self._safe_divide(
            operating_cash_flow,
            revenue,
        )

        operating_cash_flow_to_liabilities = self._safe_divide(
            operating_cash_flow,
            liabilities,
        )

        free_cash_flow_margin = self._safe_divide(
            free_cash_flow,
            revenue,
        )

        operating_cash_flow_margin_score = self._score_positive_ratio(
            value=operating_cash_flow_margin,
            strong=0.15,
            weak=0.00,
        )

        operating_cash_flow_to_liabilities_score = self._score_positive_ratio(
            value=operating_cash_flow_to_liabilities,
            strong=0.25,
            weak=0.00,
        )

        free_cash_flow_margin_score = self._score_positive_ratio(
            value=free_cash_flow_margin,
            strong=0.10,
            weak=0.00,
        )

        score = self._average_available([
            operating_cash_flow_margin_score,
            operating_cash_flow_to_liabilities_score,
            free_cash_flow_margin_score,
        ])

        return {
            "score": score,
            "metrics": {
                "operating_cash_flow": operating_cash_flow,
                "capital_expenditures": capital_expenditures,
                "free_cash_flow": free_cash_flow,
                "operating_cash_flow_margin": operating_cash_flow_margin,
                "operating_cash_flow_to_liabilities": operating_cash_flow_to_liabilities,
                "free_cash_flow_margin": free_cash_flow_margin,
            },
            "signals": self._build_signals({
                "operating_cash_flow_margin": operating_cash_flow_margin_score,
                "operating_cash_flow_to_liabilities": operating_cash_flow_to_liabilities_score,
                "free_cash_flow_margin": free_cash_flow_margin_score,
            }),
        }

    def calculate_distress_score(self) -> Dict[str, Any]:
        altman_z = self.calculate_altman_z_score()

        if altman_z is None:
            score = None
        elif altman_z >= 3.0:
            score = 0.0
        elif altman_z <= 1.8:
            score = 100.0
        else:
            score = 100.0 * (3.0 - altman_z) / (3.0 - 1.8)

        return {
            "score": score,
            "metrics": {
                "altman_z_score": altman_z,
            },
            "signals": self._build_signals({
                "altman_z_score": score,
            }),
        }

    def calculate_altman_z_score(self) -> Optional[float]:
        assets = self._get_metric("assets")
        liabilities = self._get_metric("liabilities")
        current_assets = self._get_metric("current_assets")
        current_liabilities = self._get_metric("current_liabilities")
        retained_earnings = self._get_metric("retained_earnings")
        ebit = self._get_metric("ebit")
        revenue = self._get_metric("revenue")
        equity = self._get_metric("equity")

        if current_assets is not None and current_liabilities is not None:
            working_capital = current_assets - current_liabilities
        else:
            working_capital = self._get_metric("working_capital")

        x1 = self._safe_divide(working_capital, assets)
        x2 = self._safe_divide(retained_earnings, assets)
        x3 = self._safe_divide(ebit, assets)
        x4 = self._safe_divide(equity, liabilities)
        x5 = self._safe_divide(revenue, assets)

        components = [x1, x2, x3, x4, x5]

        if any(component is None for component in components):
            return None

        return (
            1.2 * x1
            + 1.4 * x2
            + 3.3 * x3
            + 0.6 * x4
            + 1.0 * x5
        )

    def calculate(self) -> Dict[str, Any]:
        components = {
            "liquidity": self.calculate_liquidity_score(),
            "leverage": self.calculate_leverage_score(),
            "profitability": self.calculate_profitability_score(),
            "cash_flow": self.calculate_cash_flow_score(),
            "distress": self.calculate_distress_score(),
        }

        weighted_score = 0.0
        total_weight = 0.0

        for component_name, component_result in components.items():
            component_score = component_result["score"]

            if component_score is None:
                continue

            weight = self.COMPONENT_WEIGHTS[component_name]

            weighted_score += component_score * weight
            total_weight += weight

        if total_weight == 0:
            risk_score = None
            risk_level = "Unavailable"
        else:
            risk_score = weighted_score / total_weight
            risk_score = self._clip(risk_score)

            if risk_score < 30:
                risk_level = "Low"
            elif risk_score < 60:
                risk_level = "Moderate"
            else:
                risk_level = "High"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "components": components,
            "weights": self.COMPONENT_WEIGHTS,
        }

    def _build_signals(self, scored_metrics: Dict[str, Optional[float]]) -> list[str]:
        signals = []

        for metric_name, score in scored_metrics.items():
            if score is None:
                continue

            if score >= 75:
                signals.append(f"{metric_name} indicates elevated risk")
            elif score >= 50:
                signals.append(f"{metric_name} indicates moderate risk")

        return signals