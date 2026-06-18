import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

import re
from typing import Dict, Any
from src.graph.state import FinancialAgentState
from src.tools.risk_score import FinancialRiskScore
from src.database.sec_repository import SECRepository
from src.tools.financial_ratios import FinancialRatios

def planner_node(state: FinancialAgentState) -> FinancialAgentState:
    """
    Extracts the ticker from the user query and defines the analysis plan.

    This first version is deterministic. Later we can replace or enhance this
    with an LLM-based planner.
    """

    user_query = state.get("user_query", "")

    ticker = _extract_ticker(user_query)

    if ticker is None:
        return {
            "current_node": "planner",
            "execution_status": "failed",
            "errors": ["Could not identify a stock ticker in the user query."],
        }

    return {
        "current_node": "planner",
        "last_completed_node": "planner",
        "execution_status": "running",
        "ticker": ticker,
        "plan": [
            "Retrieve SEC financial metrics from SQLite",
            "Calculate financial ratios",
            "Calculate multi-factor financial risk score",
            "Generate final financial risk explanation",
        ],
    }


def researcher_node(state: FinancialAgentState) -> FinancialAgentState:
    """
    Retrieves financial data and calculates ratios and risk score.
    """

    ticker = state.get("ticker")

    if ticker is None:
        return {
            "current_node": "researcher",
            "execution_status": "failed",
            "errors": state.get("errors", []) + ["Ticker is missing from state."],
        }

    repository = SECRepository()
    metrics = repository.get_metrics(ticker)

    if not metrics:
        return {
            "current_node": "researcher",
            "execution_status": "failed",
            "errors": state.get("errors", []) + [
                f"No SEC metrics found for ticker {ticker}."
            ],
        }

    ratios = FinancialRatios(metrics).calculate()

    metric_map = {
        metric["metric_name"]: metric["value"]
        for metric in metrics
    }

    risk_score = FinancialRiskScore(
        ratios=ratios,
        metrics=metric_map,
    ).calculate()

    research_summary = _build_research_summary(
        ticker=ticker,
        ratios=ratios,
        risk_score=risk_score,
    )

    return {
        "current_node": "researcher",
        "last_completed_node": "researcher",
        "execution_status": "running",
        "sec_metrics": metrics,
        "financial_ratios": ratios,
        "risk_score": risk_score,
        "research_summary": research_summary,
    }


def writer_node(state: FinancialAgentState) -> FinancialAgentState:
    """
    Produces the final user-facing answer.

    This first version uses a deterministic template. Later we can replace this
    with an Ollama/LangChain writer node.
    """

    ticker = state.get("ticker")
    ratios = state.get("financial_ratios", {})
    risk_score = state.get("risk_score", {})
    research_summary = state.get("research_summary", "")

    final_answer = f"""
Financial risk analysis for {ticker}

Overall risk level: {risk_score.get("risk_level")}
Risk score: {risk_score.get("risk_score")}

Summary:
{research_summary}

Key ratios:
- Current ratio: {ratios.get("current_ratio")}
- Debt to equity: {ratios.get("debt_to_equity")}
- Debt to assets: {ratios.get("debt_to_assets")}
- Net margin: {ratios.get("net_margin")}
- Return on assets: {ratios.get("return_on_assets")}
- Interest coverage: {ratios.get("interest_coverage")}

Component scores:
"""

    for component_name, component_data in risk_score.get("components", {}).items():
        final_answer += (
            f"- {component_name}: {component_data.get('score')}\n"
        )

    return {
        "current_node": "writer",
        "last_completed_node": "writer",
        "execution_status": "completed",
        "final_answer": final_answer.strip(),
    }


def _extract_ticker(user_query: str) -> str | None:
    """
    Extracts a likely stock ticker from the user query.

    Example:
    'Analyze AAPL financial risk' -> 'AAPL'
    """

    candidates = re.findall(r"\b[A-Z]{1,5}\b", user_query.upper())

    ignored_words = {
        "I",
        "A",
        "THE",
        "FOR",
        "AND",
        "RISK",
        "SCORE",
        "ANALYZE",
        "ANALYSIS",
    }

    for candidate in candidates:
        if candidate not in ignored_words:
            return candidate

    return None


def _build_research_summary(
    ticker: str,
    ratios: Dict[str, Any],
    risk_score: Dict[str, Any],
) -> str:
    """
    Creates a compact analytical summary from calculated metrics.
    """

    risk_level = risk_score.get("risk_level")
    score = risk_score.get("risk_score")

    summary = (
        f"{ticker} has an estimated {risk_level} financial risk profile "
        f"with a risk score of {score}. "
    )

    if ratios.get("net_margin") is not None:
        summary += f"Net margin is {ratios.get('net_margin'):.2%}. "

    if ratios.get("return_on_assets") is not None:
        summary += f"Return on assets is {ratios.get('return_on_assets'):.2%}. "

    if ratios.get("liabilities_to_assets") is not None:
        summary += (
            f"Liabilities represent "
            f"{ratios.get('liabilities_to_assets'):.2%} of assets. "
        )

    return summary