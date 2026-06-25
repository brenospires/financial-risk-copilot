from typing import TypedDict, Any, Literal, get_args

Intent = Literal[
    "company_risk_analysis",
    "company_comparison",
    "company_overview",
    "unsupported",
]

PlannerStatus = Literal[
    "collecting_inputs",
    "ready_for_pipeline",
    "unsupported",
    "planner_error",
]

SUPPORTED_INTENTS: tuple[str, ...] = get_args(Intent)
SUPPORTED_PLANNER_STATUSES: tuple[str, ...] = get_args(PlannerStatus)


class AgentState(TypedDict, total=False):
    """
    Shared LangGraph state.

    This state is passed from node to node and progressively updated.

    We use total=False because the initial graph input will usually contain
    only user_query. Each node then adds only the fields it is responsible for.
    """

    user_query: str

    # Planner outputs
    status: PlannerStatus
    intent: Intent
    tickers: list[str]
    company_names: list[str]
    start_date: str | None
    end_date: str | None
    start_year: int | None
    end_year: int | None
    needs_sec_data: bool
    needs_comparison: bool
    plan: list[dict[str, Any]]
    missing_inputs: list[str]
    follow_up_questions: list[str]

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
