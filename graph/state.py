from typing import TypedDict, Any, Literal, get_args

Intent = Literal[
    "company_risk_analysis",
    "macro_conditions_analysis",
    "company_comparison",
    "company_trend_analysis",
    "company_overview",
    "full_risk_overview",
    "unsupported",
]

SUPPORTED_INTENTS: tuple[str, ...] = get_args(Intent)

class AgentState(TypedDict, total=False):
    """
    Shared LangGraph state.

    This state is passed from node to node and progressively updated.

    We use total=False because the initial graph input will usually contain
    only user_query. Each node then adds only the fields it is responsible for.
    """

    user_query: str

    # Planner outputs
    intent: Intent
    tickers: list[str]
    company_names: list[str]
    start_year: int | None
    end_year: int | None
    needs_sec_data: bool
    needs_fred_data: bool
    needs_comparison: bool
    macro_indicators: list[str]
    plan: list[dict[str, Any]]

    # Research outputs
    company_data: dict[str, dict[str, Any]]
    macro_data: dict[str, dict[str, Any]]

    # Computation outputs
    company_metrics: dict[str, dict[str, Any]]
    comparison_metrics: dict[str, Any] | None
    macro_summary: dict[str, Any] | None

    # Control / diagnostics
    missing_data: list[dict[str, Any]]
    errors: list[str]

    # Writer input/output
    analysis_context: dict[str, Any]
    final_answer: str