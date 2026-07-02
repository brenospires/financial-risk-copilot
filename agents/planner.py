import json
import random
from datetime import datetime

from utils.prompts import load_prompt, render_prompt
from utils.json import parse_planner_json
from utils.tokens import update_token_usage
from workflow.state import AgentState
from llm.llm import get_llm

class PlannerAgent:
    """Agent responsible for extracting structured conversation state from user input."""

    FOLLOW_UP_QUESTIONS = {
        "company": [
            "Which company would you like me to analyze?",
            "What company should I use for this request?",
            "Which company are you interested in?",
            "Please tell me the company name or ticker you want to use.",
            "What company should this analysis focus on?",
            "Which company should I look up?",
            "Can you provide the company name or ticker?",
            "What company would you like to review?",
            "Which business should I analyze for you?",
            "Please specify the company for this request.",
        ],
        "both_companies": [
            "Which two companies would you like me to compare?",
            "Please provide the two companies or tickers to compare.",
            "What are the two companies for this comparison?",
            "Which pair of companies should I compare?",
            "Can you send both company names or tickers?",
            "Please tell me the two businesses you want compared.",
            "Which two tickers should I use for the comparison?",
            "What company pair should this comparison focus on?",
            "Please specify both companies for the comparison.",
            "Which two companies should I evaluate side by side?",
        ],
        "second_company": [
            "Which second company should I compare against the first one?",
            "What company should I use as the comparison peer?",
            "Please provide the second company or ticker for the comparison.",
            "Who should I compare it with?",
            "Which company should be on the other side of the comparison?",
            "What second ticker should I use?",
            "Can you send the second company for this comparison?",
            "Which peer company would you like to compare?",
            "What should the first company be compared against?",
            "Please specify the second company for the side-by-side analysis.",
        ],
        "ticker": [
            "What ticker should I use for this company?",
            "Please provide the ticker symbol for the company.",
            "Can you send the company's market ticker?",
            "Which ticker identifies this company?",
            "What stock symbol should I use?",
            "Please tell me the public ticker for this company.",
            "Can you provide the listed ticker symbol?",
            "Which ticker should I use for data retrieval?",
            "What is the company's trading symbol?",
            "Please specify the ticker so I can retrieve the financial data.",
        ],
        "company_name": [
            "What company name should I associate with this ticker?",
            "Please provide the company name for the ticker.",
            "Which company does this ticker refer to?",
            "Can you send the company name as well?",
            "What is the business name for this ticker?",
            "Please tell me the company name to use.",
            "Which company should I label this ticker as?",
            "Can you confirm the company name?",
            "What company is represented by this ticker?",
            "Please specify the company name for context.",
        ],
    }

    def __init__(self, llm=None):
        self.llm = llm or get_llm()

    def get_status(
        self,
        query: str,
        current_state: AgentState | None = None,
    ) -> AgentState:
        """Returns the current status extracted by the LLM."""
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        state_context = current_state or {
            "user_query": query,
            "status": "collecting_inputs", 
            "intent": None, 
            "tickers": [], 
            "company_names": [], 
            "start_date": None, 
            "end_date": None, 
            "missing_inputs": [], 
            "follow_up_questions": [], 
            "answer": None
        }
        
        # Reset planner current-call token counters
        state_context["planner_prompt_tokens"] = 0
        state_context["planner_output_tokens"] = 0
        state_context["planner_total_tokens"] = 0
        # Preserve token limit from current state
        state_context["planner_token_limit"] = current_state.get("planner_token_limit", 40960) if current_state else 40960

        prompt = load_prompt('planner.md')
        prompt = render_prompt(
            prompt,
            today=current_date,
            query=query,
            current_state=str(state_context),
        )
        
        # DEBUG: Log the prompt being sent
        print("\n[PLANNER DEBUG] Prompt being sent to LLM:")
        print(f"  Prompt starts with: {prompt[:100]}...")
        print(f"  Prompt includes 'Output Format': {'Output Format' in prompt}")
        print(f"  Prompt includes 'Reasoning Steps': {'Reasoning Steps' in prompt}")
        
        llm_response = self.llm.invoke(prompt)
        response_content = self._response_content(llm_response)
        
        # DEBUG: Log the actual response before parsing
        print("\n[PLANNER DEBUG] LLM Response received:")
        print(f"  Query: {query[:100]}...")
        print(f"  Response length: {len(response_content)} chars")
        print(f"  Response preview: {response_content[:150]}...")
        print(f"  Contains '{{'': {'{' in response_content}")
        print(f"  Contains '}}'': {'}' in response_content}")
        
        response = parse_planner_json(response_content)
        state = AgentState(**response)
        self._preserve_token_usage(state, state_context)
        update_token_usage(state, llm_response, agent_name="planner")

        if "tickers" in state:
            state["tickers"] = self._normalize_list(state["tickers"], str_mode="upper")

        if "company_names" in state:
            state["company_names"] = self._normalize_list(state["company_names"], str_mode="cammel_case")

        if "intent" not in state:
            state["intent"] = "chat"

        self._apply_default_dates(state)
        self._get_status_from_context(state)
        
        if state["status"] == "collecting_inputs":
            self._required_missing_inputs(state)
            self._build_follow_up_questions(state)

        return state
    
    @staticmethod   
    def _preserve_token_usage(state: AgentState, current_state: AgentState | dict) -> None:
        state["prompt_tokens"] = current_state.get("prompt_tokens", 0)
        state["output_tokens"] = current_state.get("output_tokens", 0)
        state["total_tokens"] = current_state.get("total_tokens", 0)
        state["context_window_tokens"] = current_state.get("context_window_tokens", 0)
        state["context_memory_pct"] = current_state.get("context_memory_pct", 0.0)
        state["llm_usage_by_agent"] = current_state.get("llm_usage_by_agent", {})
        state["planner_prompt_tokens"] = current_state.get("planner_prompt_tokens", 0)
        state["planner_output_tokens"] = current_state.get("planner_output_tokens", 0)
        state["planner_total_tokens"] = current_state.get("planner_total_tokens", 0)
        state["planner_token_limit"] = current_state.get("planner_token_limit", 0)
        state["messenger_prompt_tokens"] = current_state.get("messenger_prompt_tokens", 0)
        state["messenger_output_tokens"] = current_state.get("messenger_output_tokens", 0)
        state["messenger_total_tokens"] = current_state.get("messenger_total_tokens", 0)
        state["messenger_token_limit"] = current_state.get("messenger_token_limit", 0)

    @staticmethod
    def _response_content(response: object) -> str:
        content = getattr(response, "content", response)
        return str(content).strip()

    @staticmethod
    def _normalize_list(value: object, str_mode: str) -> list:
        if value is None:
            return []
        
        if str_mode == "cammel_case":
            func = str.capitalize
        elif str_mode == "lower":
            func = str.lower
        elif str_mode == "upper":
            func = str.upper
        else:
            func = str.capitalize

        if isinstance(value, list):
            return [func(str(item)) for item in value if item]

        return [value]

    def _apply_default_dates(self, state: AgentState) -> None:
        intent = state.get("intent")
        if intent not in {
            "company_risk_analysis",
            "company_comparison",
            "company_overview",
        }:
            state["start_date"] = None
            state["end_date"] = None

        if not state.get("start_date") and not state.get("end_date"):
                
            last_complete_year = datetime.now().year - 1
            start_year = last_complete_year - 4
            default_start_date = f"{start_year}-01-01"

            default_end_date = f"{last_complete_year}-12-31"
            state["start_date"] = state.get("start_date") or default_start_date
            state["end_date"] = state.get("end_date") or default_end_date

            missing_inputs = state.get("missing_inputs") or []
            state["missing_inputs"] = [
                item for item in missing_inputs if item not in {"start_date", "end_date", "date_range"}
            ]

            follow_up_questions = state.get("follow_up_questions") or []
            state["follow_up_questions"] = [
                question
                for question in follow_up_questions
                if "date" not in question.lower() and "range" not in question.lower()
            ]

            if state.get("status") == "collecting_inputs" and not state["missing_inputs"]:
                state["status"] = "ready_for_pipeline"

    # TODO: Make it change status to collecting_inputs if status is done and a new
    # company analysis is requested.
    def _get_status_from_context(self, state: AgentState) -> None:
        intent = state.get("intent")

        if intent in {
            "company_risk_analysis",
            "company_comparison",
            "company_overview",
        }:
            state["answer"] = ""
            missing_inputs = self._required_missing_inputs(state)
            follow_up_questions = self._build_follow_up_questions(state)
            state["missing_inputs"] = missing_inputs
            state["follow_up_questions"] = follow_up_questions

            if missing_inputs:
                state["status"] = "collecting_inputs"
            else:
                state["status"] = "ready_for_pipeline"
            return

        if intent in {"chat", "follow_up"}:
            state["status"] = "ready_for_response"
            state["missing_inputs"] = []
            state["follow_up_questions"] = []
            return

        if intent == "unsupported":
            state["status"] = "unsupported"
            state["missing_inputs"] = []
            state["follow_up_questions"] = []

    def _required_missing_inputs(self, state: AgentState) -> list[str]:
        
        if "missing_inputs" not in state:
            state["missing_inputs"] = []
        
        intent = state.get("intent")
        tickers = state.get("tickers") or []
        company_names = state.get("company_names") or []
        missing_inputs = []
        required_count = 2 if intent == "company_comparison" else 1

        if intent == "company_comparison":
            if len(tickers) == 0 and len(company_names) == 0:
                missing_inputs.append("both_companies")
            elif len(tickers) < 2 and len(company_names) < 2:
                missing_inputs.append("second_company")
            else:
                if len(company_names) > 0 and len(tickers) < required_count:
                    missing_inputs.append("ticker")
                if len(tickers) > 0 and len(company_names) < required_count:
                    missing_inputs.append("company_name")
        elif intent in {"company_risk_analysis", "company_overview"}:
            if len(tickers) == 0 and len(company_names) == 0:
                missing_inputs.append("company")
            elif len(company_names) > 0 and len(tickers) < 1:
                missing_inputs.append("ticker")
            elif len(tickers) > 0 and len(company_names) < 1:
                missing_inputs.append("company_name")

        state["missing_inputs"] = missing_inputs

        return missing_inputs
            
    def _build_follow_up_questions(self, state: AgentState) -> list[str]:
        state["follow_up_questions"] = [
            random.choice(PlannerAgent.FOLLOW_UP_QUESTIONS[missing_input])
            for missing_input in state["missing_inputs"]
            if missing_input in PlannerAgent.FOLLOW_UP_QUESTIONS
        ]

        return state["follow_up_questions"]


    # TODO: Change place to utils if necessary into another location
    @staticmethod
    def _deduplicate(values: list[str]) -> list[str]:
        deduplicated = []
        for value in values:
            if value not in deduplicated:
                deduplicated.append(value)

        return deduplicated
