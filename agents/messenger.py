from utils.prompts import load_prompt, render_prompt
from utils.tokens import update_token_usage
from workflow.state import AgentState
from llm.llm import get_llm
import random

class MessengerAgent:
    def __init__(self, state: AgentState, llm=None):
        self.state = state
        self.llm = llm or get_llm()

    def generate_response(self) -> AgentState:
        """Generate a response based on the current state."""
        
        # Reset messenger current-call token counters
        self.state["messenger_prompt_tokens"] = 0
        self.state["messenger_output_tokens"] = 0
        self.state["messenger_total_tokens"] = 0
        self.state["messenger_token_limit"] = self.state.get("messenger_token_limit", 40960)
        
        print(f"Generating response for intent: {self.state['intent']} and status: {self.state['status']}")

        if self.state["status"] != "ready_for_response":
            raise ValueError("Cannot generate responses when the state is not ready for response.")

        if self.state["intent"] == "company_risk_analysis":
            self._build_single_company_analysis("company_risk_analysis.md")
        elif self.state["intent"] == "company_overview":
            self._build_single_company_analysis("company_overview_analysis.md")
        elif self.state["intent"] == "follow_up":
            self._give_followup()
        elif self.state["intent"] == "chat":
            self._generate_chat_response()  # <-- ADD THIS

        # Set status to done for company analysis intents
        if self.state["intent"] in {"company_risk_analysis", "company_overview", "company_comparison"}:
            self.state["last_report"] = self.state.get("answer")
            self.state["last_metrics"] = self.state.get("company_metrics")
            self.state["status"] = "done"
        
        # Chat and follow_up stay at ready_for_response
        elif self.state["intent"] in {"chat", "follow_up"}:
            self.state["status"] = "ready_for_response"
        
        return self.state


    # For chat intent the Planer agent already generates a response in order to
    # use lass LLM calls, but we are keeping this placeholder in case we need
    # to generate a separate response for chat in the future.
    def _generate_chat_response(self) -> None:  # <-- ADD THIS METHOD
        """Generate a chat response for general questions."""
        pass


    def _build_single_company_analysis(self, prompt_file_name: str) -> None:
        """Generate company risk analysis response based on the current state."""
        
        financial_statements = self._remove_none_metrics(self.state['company_data'])
        report_metrics = self._remove_none_metrics(self.state["company_metrics"])

        prompt = load_prompt(prompt_file_name)
        prompt = render_prompt(prompt,
            company_name=self.state['company_names'][0],
            company_ticker=self.state['tickers'][0],
            ticker=self.state['tickers'][0],
            financial_statements=financial_statements,
            report_metrics=report_metrics,
            start_date=self.state['start_date'],
            end_date=self.state['end_date'])

        response = self.llm.invoke(prompt)
        update_token_usage(self.state, response, agent_name="messenger")
        self.state["answer"] = str(response.content)

    def _give_followup(self):
        
        print("Generating follow-up response...")

        NO_ANALYSIS_RESPONSES = [
            "I don't have a completed company analysis to answer from yet. Please ask for a company risk assessment, company overview or company comparison first.",
            "I don't have any previous analysis available yet. Start by asking me to analyze a company, compare two companies, or generate a company overview.",
            "There's no completed analysis in this session yet. Ask me for a company risk assessment, company overview, or company comparison first.",
            "I need a previous company analysis before I can answer follow-up questions. Try asking me to analyze or compare a company first.",
            "I don't have enough context yet. Please run a company risk analysis, overview, or comparison before asking follow-up questions.",
            "I haven't analyzed any company yet in this session. Ask me for a risk assessment, overview, or comparison to get started.",
            "I can answer follow-up questions after an analysis is completed. Please start with a company risk assessment, overview, or comparison.",
            "There's no analysis context available yet. Ask me to analyze a company first, and I'll be able to answer follow-up questions after that.",
            "I don't have a report to reference yet. Please request a company overview, risk assessment, or comparison first.",
            "I need an existing analysis before answering that. Start with a company risk assessment, company overview, or company comparison.",
        ]

        user_query = self.state.get("user_query")
        last_report = self.state.get("last_report")
        last_metrics = self.state.get("last_metrics")

        if not user_query or not last_report or not last_metrics:
            self.state["answer"] = random.choice(NO_ANALYSIS_RESPONSES)
            return

        prompt = load_prompt("follow_up.md")
        prompt = render_prompt(prompt, 
            query=user_query, 
            last_report=last_report,
            last_metrics=last_metrics)

        response = self.llm.invoke(prompt)
        update_token_usage(self.state, response, agent_name="messenger")
        self.state["answer"] = str(response.content)


    @staticmethod
    def _remove_none_metrics(metrics: dict) -> dict:
        return {
            ticker: {
                name: value
                for name, value in ticker_metrics.items()
                if value is not None
            }
            for ticker, ticker_metrics in metrics.items()
        }
