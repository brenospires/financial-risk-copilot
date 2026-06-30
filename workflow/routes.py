from agents.messenger import MessengerAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from workflow.state import AgentState


def get_route(state: AgentState) -> AgentState:
    if state["status"] in {"collecting_inputs", "done", "planner_error"} or state["intent"] in ["chat", "follow_up"]:
        state = PlannerAgent().get_status(
            state["user_query"],
            current_state=state,
        )

    if state["status"] == "ready_for_pipeline" and state["intent"] in ["company_risk_analysis", "company_overview", "company_comparison"]:
        state = ResearcherAgent(state).retrieve_data()

    if state["status"] == "ready_for_response" and state["intent"] in ["company_risk_analysis", "company_overview", "company_comparison"]:
        state = MessengerAgent(state).generate_response()

    return state
