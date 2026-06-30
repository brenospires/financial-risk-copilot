from typing import TypedDict, Any, Literal, get_args

Intent = Literal[
    # Full single-company financial-risk assessment.
    "company_risk_analysis",
    # Side-by-side assessment of two companies.
    "company_comparison",
    # General company profile or business overview.
    "company_overview",
    # Question about the most recent completed assessment.
    "follow_up",
    # Small talk or capability guidance.
    "chat",
    # Request outside the currently supported workflow.
    "unsupported",
]

PlannerStatus = Literal[
    # More user input is needed before any response or pipeline run.
    "collecting_inputs",
    # The state has enough inputs to run data retrieval and computations.
    "ready_for_pipeline",
    # The state should go directly to the messenger without data retrieval.
    "ready_for_response",
    # The request is outside the product scope or violates workflow limits.
    "unsupported",
    # Runtime failure while extracting or normalizing planner state.
    "planner_error",
    # Asks if the user wants to ask follow-up questions after a completed assessment.
]

SUPPORTED_INTENTS: tuple[str, ...] = get_args(Intent)
SUPPORTED_PLANNER_STATUSES: tuple[str, ...] = get_args(PlannerStatus)


class AgentState(TypedDict, total=False):
    """
    Shared LangGraph state.

    This state is passed from node to node and progressively updated.

    We use total=False because the initial workflow input will usually contain
    only user_query. Each node then adds only the fields it is responsible for.
    """

    user_query: str

    # Planner outputs
    user_query: str
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
    answer: str | None

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
