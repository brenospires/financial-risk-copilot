from typing import TypedDict, Optional, Dict, Any, List, Literal

ExecutionStatus = Literal[
    "not_started",
    "running",
    "completed",
    "failed"
]

class FinancialAgentState(TypedDict, total=False):
    """
    Shared state used by the LangGraph workflow.

    In LangGraph, every node receives the current state and returns updates
    to this same state. This object defines which fields can exist during
    one execution of the financial analysis agent.
    """

    # User input
    user_query: str
    ticker: str

    # Execution control
    current_node: Optional[str]
    last_completed_node: Optional[str]
    execution_status: ExecutionStatus
    errors: List[str]

    # Planner output
    plan: List[str]

    # Researcher output
    sec_metrics: List[Dict[str, Any]]
    financial_ratios: Dict[str, Optional[float]]
    risk_score: Dict[str, Any]
    fred_indicators: Dict[str, Any]
    research_summary: str

    # Writer output
    final_answer: str