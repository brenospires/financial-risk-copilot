import traceback
from agents.messenger import MessengerAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearcherAgent
from workflow.state import AgentState

def get_route(state: AgentState, user_query: str) -> AgentState:
    company_intents = {
        "company_risk_analysis",
        "company_overview",
        "company_comparison",
    }

    try:        
        state["user_query"] = user_query
        state["agents_passed"] = []
        state["intents_passed"] = []
        state["llm_usage_by_agent"] = {}
        state["planner_prompt_tokens"] = 0
        state["planner_output_tokens"] = 0
        state["planner_total_tokens"] = 0
        state["messenger_prompt_tokens"] = 0
        state["messenger_output_tokens"] = 0
        state["messenger_total_tokens"] = 0

        # DEBUG: Log incoming state
        print(f"\n[ROUTES DEBUG] get_route called with query: {user_query[:80]}...")
        print(f"  Incoming state status: {state.get('status')}")
        print(f"  Incoming state intent: {state.get('intent')}")
        print(f"  Incoming state has answer: {bool(state.get('answer'))}")
        if state.get('answer'):
            print(f"  Incoming answer preview: {str(state.get('answer'))[:100]}...")

        # Always plan first for a new user query
        # Create a clean context for planner - don't pass old analysis data
        state_context = {
            "user_query": state.get("user_query", user_query),
            "tickers": state.get("tickers", []),
            "company_names": state.get("company_names", []),
            "start_date": state.get("start_date"),
            "end_date": state.get("end_date"),
            "last_report": state.get("last_report"),  # Keep for follow-up context only
            "last_metrics": state.get("last_metrics"),
            "agents_passed": state.get("agents_passed", []),
            "intents_passed": state.get("intents_passed", []),
            "llm_usage_by_agent": state.get("llm_usage_by_agent", {}),
            "prompt_tokens": state.get("prompt_tokens", 0),
            "output_tokens": state.get("output_tokens", 0),
            "total_tokens": state.get("total_tokens", 0),
            "context_window_tokens": state.get("context_window_tokens", 0),
            "context_memory_pct": state.get("context_memory_pct", 0.0),
            "planner_prompt_tokens": state.get("planner_prompt_tokens", 0),
            "planner_output_tokens": state.get("planner_output_tokens", 0),
            "planner_total_tokens": state.get("planner_total_tokens", 0),
            "planner_token_limit": state.get("planner_token_limit", 0),
            "messenger_prompt_tokens": state.get("messenger_prompt_tokens", 0),
            "messenger_output_tokens": state.get("messenger_output_tokens", 0),
            "messenger_total_tokens": state.get("messenger_total_tokens", 0),
            "messenger_token_limit": state.get("messenger_token_limit", 0),
        }

        # Always plan first for a new user query
        # Planner agent is the intent extractor and workflow controller, 
        # therefore it should always run first to determine the next steps in the workflow.
        new_state = PlannerAgent().get_status(
            state["user_query"],
            current_state=state_context,
        )
        
        # Track that planner ran
        agents_passed = new_state.get("agents_passed", [])
        if "planner" not in agents_passed:
            agents_passed.append("planner")

        new_state["agents_passed"] = agents_passed
        
        # Track the intent
        intents_passed = new_state.get("intents_passed", [])
        if new_state.get("intent") and new_state["intent"] not in intents_passed:
            intents_passed.append(new_state["intent"])
        new_state["intents_passed"] = intents_passed

        # Chat should be ready_for_response (not directly returned)
        if new_state["intent"] == "chat":
            new_state["status"] = "ready_for_response"
            new_state["start_date"] = None
            new_state["end_date"] = None
            new_state["tickers"] = []
            new_state["company_names"] = []
            new_state["missing_inputs"] = []
            new_state["follow_up_questions"] = []

        # Follow-ups should be answered from the previous generated report.
        if new_state["intent"] == "follow_up":
            new_state["status"] = "ready_for_response"
            new_state["answer"] = ""
            new_state["last_report"] = state.get("last_report")
            new_state["start_date"] = None
            new_state["end_date"] = None
            new_state["tickers"] = []
            new_state["company_names"] = []
            new_state["missing_inputs"] = []
            new_state["follow_up_questions"] = []

        # Unsupported should return directly
        if new_state["status"] == "unsupported" or new_state["intent"] == "unsupported":
            new_state["start_date"] = None
            new_state["end_date"] = None
            new_state["tickers"] = []
            new_state["company_names"] = []
            new_state["missing_inputs"] = []
            new_state["follow_up_questions"] = []
            return new_state

        # Missing inputs: ask follow-up question
        if new_state["status"] == "collecting_inputs":
            return new_state

        # Company workflows: run pipeline, then generate response in same turn
        if new_state["status"] == "ready_for_pipeline" and new_state["intent"] in company_intents:
            new_state = ResearcherAgent(new_state).retrieve_data()
            new_state["missing_inputs"] = []
            new_state["follow_up_questions"] = []
            
            # Track that researcher ran
            agents_passed = new_state.get("agents_passed", [])
            if "researcher" not in agents_passed:
                agents_passed.append("researcher")
            new_state["agents_passed"] = agents_passed

        # ALL ready_for_response requests go through messenger (includes chat, follow_up, company analysis)
        if new_state["status"] == "ready_for_response":
            new_state = MessengerAgent(new_state).generate_response()
            
            # Track that messenger ran
            agents_passed = new_state.get("agents_passed", [])
            if "messenger" not in agents_passed:
                agents_passed.append("messenger")
            new_state["agents_passed"] = agents_passed

        if new_state["status"] == "done" and new_state["intent"] in company_intents:
            new_state["status"] = "ready_for_response"
            new_state["start_date"] = None
            new_state["end_date"] = None
            new_state["tickers"] = []
            new_state["company_names"] = []
            new_state["missing_inputs"] = []
            new_state["follow_up_questions"] = []
            new_state["intent"] = "follow_up"
            new_state["last_report"] = new_state["answer"]
            new_state["last_metrics"] = new_state["company_metrics"]
            new_state["current_company"] = new_state["company_names"][0] if new_state["company_names"] else None

            

        return new_state

    except Exception as exc:
        error_stack = traceback.format_exc()
        print(error_stack)
  
        return AgentState(
            status="unsupported",
            intent="chat",
            answer=(
                "I'm sorry, but I couldn't process your request due to an unexpected internal error. "
                "Please try again in a few moments. If the problem persists, consider rephrasing your request."
            ),
            errors=[str(exc)],
        )
    
