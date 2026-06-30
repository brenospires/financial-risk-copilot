from agents.messenger import MessengerAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from workflow.state import AgentState


def get_route(state: AgentState) -> AgentState:
    if state["status"] == "collecting_inputs":
        state = PlannerAgent().get_status(
            state["user_query"],
            current_state=state,
        )

    if state["status"] == "ready_for_pipeline":
        state = ResearcherAgent(state).retrieve_data()

    if state["status"] == "ready_for_response":
        state = MessengerAgent(state).generate_response()

    return state
