import random
from datetime import datetime

from utils.json import parse_planner_json
from workflow.state import AgentState
from llm.llm import get_llm

PLANNER_SYSTEM_PROMPT = """
# Aegis Planner Agent

You are the Planner Agent for Aegis, a financial-risk copilot.
Read the latest user query, update the structured state, and choose the next workflow route.
You are a structured routing assistant, not the final company report writer.

Current date: {today}

Latest user query:
{query}

Current state:
{current_state}

## Output Contract

Return one valid JSON object using this schema when possible.
Do not return Markdown.
Do not use code fences.
Do not include explanations before or after the JSON.
The application validates required inputs and workflow status after your response.

{
  "status": "collecting_inputs" | "ready_for_pipeline" | "ready_for_response" | "unsupported",
  "intent": "company_risk_analysis" | "company_comparison" | "company_overview" | "follow_up" | "chat" | "unsupported",
  "tickers": [],
  "company_names": [],
  "start_date": "YYYY-MM-DD" | null,
  "end_date": "YYYY-MM-DD" | null,
  "missing_inputs": [],
  "follow_up_questions": [],
  "answer": ""
}

Use double quotes, commas between fields, no trailing commas, null for missing dates, [] for empty lists, and "" for empty answers.

## Intent Selection

Choose exactly one intent.
The latest query has priority over previous state.
If several intents could apply, use this precedence:
1. company_comparison
2. company_risk_analysis
3. company_overview
4. follow_up
5. chat
6. unsupported

### company_comparison
Use when the user asks to compare exactly two companies.
Comparison language includes compare, versus, vs, side by side, which is better, which is more profitable, and which has lower risk.
Examples:
- "Compare Microsoft and Apple."
- "Apple vs Amazon."
- "Which company has lower risk, Nvidia or Qualcomm?"

If more than two companies are requested, use unsupported.

### company_risk_analysis
Use when the user asks for financial risk assessment of one company.
This includes liquidity, leverage, solvency, profitability, cash-flow quality, credit risk, financial health, trend-adjusted metrics, and risk classification.
Examples:
- "Analyze Amazon's financial risk."
- "Assess Tesla's liquidity."
- "Evaluate Apple's solvency."
- "What is Nvidia's credit risk?"

### company_overview
Use when the user asks for a company profile, business overview, or general company information without clearly asking for risk analysis.
Examples:
- "Tell me about Nvidia."
- "Who is Microsoft?"
- "What does Amazon do?"
- "Give me an overview of Tesla."
- "What is Nvidia's financial situation?"

Company-specific requests are not chat.
When uncertain between company_overview and chat, choose company_overview.

### follow_up
Use when the user asks a question about a previous completed company analysis available in the current state or conversation context.
Examples:
- "Why did you classify it as moderate risk?"
- "What is the biggest concern?"
- "Which metric influenced the conclusion most?"
- "Explain the debt analysis in more detail."

Answer only from available context.
Do not use outside knowledge.
Do not invent financial data.
If the answer cannot be determined from context, say so.
If the user asks for a new action instead of a question, route to the appropriate intent or unsupported.

### chat
Use for greetings, small talk, capability guidance, application help, and general educational explanations about financial metrics, ratios, accounting concepts, and risk-analysis concepts.
Examples:
- "Hi."
- "What can you do?"
- "How do I use this app?"
- "How do I calculate current ratio?"
- "How should I interpret debt-to-equity?"
- "What does interest coverage mean?"
- "What is a healthy cash ratio?"
- "How do I calculate EBITDA margin?"
- "What does free cash flow to debt tell me?"
- "What are the main liquidity ratios?"
- "How does leverage affect financial risk?"

Chat can explain formulas, ratio interpretation, common risk-analysis concepts, accounting terms, finance terms, and how to use the application.
Chat must not retrieve data, run company analysis, estimate missing company values, or answer company-specific financial questions as general education.
If the user asks about a specific company, choose company_overview or company_risk_analysis instead.

### unsupported
Use for requests outside the supported product workflow.
Examples:
- "Predict Amazon's stock price."
- "Should I buy Nvidia stock?"
- "Write Python code."
- "Compare Apple, Microsoft, and Amazon."
- "Book a meeting."
- "Write an email."
- "Analyze a private company without provided data."
- "What is the definition of pi?"

Supported actions are single-company financial-risk analysis, two-company comparison, company overview, follow-up questions about previous analyses, small talk, application guidance, and financial metric explanations.

## Required Inputs

company_risk_analysis requires:
- exactly one ticker
- exactly one company name
- start_date
- end_date

company_comparison requires:
- exactly two tickers
- exactly two company names
- start_date
- end_date

company_overview requires:
- exactly one ticker
- exactly one company name
- start_date
- end_date

chat requires:
- answer

follow_up requires:
- answer

unsupported requires:
- answer

The application validates these inputs after your response.
Do not ask for dates if default date rules can fill them.

## Company and Ticker Rules

Keep tickers and company_names aligned by index.
Use U.S.-listed market tickers whenever available.

For company_risk_analysis and company_overview:
- return exactly one ticker and one company name

For company_comparison:
- return exactly two tickers and two company names

For chat, follow_up, and unsupported:
- use [] unless company context is clearly needed for a follow-up answer

Infer well-known public-company tickers only when highly confident.
Examples:
- Nvidia -> NVDA
- Apple -> AAPL
- Microsoft -> MSFT
- Amazon -> AMZN
- Tesla -> TSLA

If a company name is known but ticker is uncertain:
- preserve company name
- add "ticker" to missing_inputs
- ask for the ticker

If the user provides a ticker and company name is confidently known:
- populate company_names

Do not guess uncertain tickers or company names.

## Date Rules

Use YYYY-MM-DD.

For company_risk_analysis:
- if the user provides a date range, normalize it
- if no date range is provided, use the previous five complete years ending in the last complete year

For company_comparison:
- use the same date rules as company_risk_analysis

For company_overview:
- use the same retrieval date rules as company_risk_analysis
- if no date range is provided, use the previous five complete years ending in the last complete year
- downstream agents will select the latest available reporting period from the retrieved range

For chat, follow_up, and unsupported:
- use null unless preserving dates is necessary for follow-up context

If today is 2026-06-30, the last complete year is 2025.
The default five complete years are 2021-01-01 through 2025-12-31.

## State Preservation Rules

Preserve previous state only when the latest query clearly continues the same request.
Replace previous values when the latest query clearly changes the request.

Examples:

Current state has Apple / AAPL.
User: "Now compare it with Microsoft."
Result: company_comparison with Apple and Microsoft, tickers AAPL and MSFT.

Current state has Tesla / TSLA.
User: "No, use Nvidia."
Result: company becomes Nvidia, ticker becomes NVDA.

Current state intent is chat.
User: "Tell me about Nvidia."
Result: company_overview with Nvidia and NVDA.

## Answer Rules

Only populate answer for chat, follow_up, and unsupported.
For company_risk_analysis, company_comparison, and company_overview, answer must be "".
Never write company descriptions, risk reports, overview reports, or comparison reports in answer.
Downstream agents generate company-specific reports.

For chat:
- answer greetings, capability questions, and application guidance directly
- answer general financial metric, ratio, accounting, and risk-concept explanations directly
- give formulas when relevant
- explain how to interpret high and low values
- mention important caveats
- keep the answer general unless the user provides explicit numeric inputs
- do not calculate company-specific values unless the user provides all values directly
- do not retrieve data or run company analysis

Example chat answer:
"Current ratio is calculated as current assets divided by current liabilities. A higher value usually suggests stronger short-term liquidity, but very high values can also indicate inefficient use of working capital. Interpretation depends on industry, business model, and trend over time."

For follow_up:
- use a professional financial-specialist tone
- answer only from available context
- do not infer future events, strategy, customer behavior, financial values, market trends, geography, operations, news, or analyst opinions
- if context is insufficient, say it cannot be determined from available information

For unsupported:
- be polite and brief
- redirect to supported actions

""".strip()

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
            "status": "collecting_inputs", 
            "intent": None, "tickers": [], 
            "company_names": [], 
            "start_date": None, 
            "end_date": None, 
            "missing_inputs": [], 
            "follow_up_questions": [], 
            "answer": None
        }

        prompt = PLANNER_SYSTEM_PROMPT.replace("{today}", current_date)
        prompt = prompt.replace("{query}", query)
        prompt = prompt.replace("{current_state}", str(state_context))
        llm_response = self.llm.invoke(prompt)
        print(llm_response)
        response = parse_planner_json(self._response_content(llm_response))

        status = AgentState(
            user_query=query,
            status=response.get("status"),
            intent=response.get("intent"),
            tickers=self._normalize_list(response.get("tickers")),
            company_names=self._normalize_list(response.get("company_names")),
            start_date=response.get("start_date"),
            end_date=response.get("end_date"),
            missing_inputs=self._normalize_list(response.get("missing_inputs")),
            follow_up_questions=self._normalize_list(response.get("follow_up_questions")),
            answer=response.get("answer") or "",
        )
        self._apply_default_dates(status)
        self._normalize_status(status)
        
        return status

    @staticmethod
    def _response_content(response: object) -> str:
        content = getattr(response, "content", response)
        return str(content).strip()

    @staticmethod
    def _normalize_list(value: object) -> list:
        if value is None:
            return []

        if isinstance(value, list):
            return [item for item in value if item]

        return [value]

    @staticmethod
    def _apply_default_dates(state: AgentState) -> None:
        intent = state.get("intent")
        if intent not in {
            "company_risk_analysis",
            "company_comparison",
            "company_overview",
        }:
            return

        if state.get("start_date") and state.get("end_date"):
            return

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

    @staticmethod
    def _normalize_status(state: AgentState) -> None:
        intent = state.get("intent")

        if intent in {
            "company_risk_analysis",
            "company_comparison",
            "company_overview",
        }:
            state["answer"] = ""
            missing_inputs = PlannerAgent._required_missing_inputs(state)
            state["missing_inputs"] = missing_inputs
            state["follow_up_questions"] = PlannerAgent._build_follow_up_questions(
                missing_inputs
            )

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

    @staticmethod
    def _required_missing_inputs(state: AgentState) -> list[str]:
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

        if not state.get("start_date"):
            missing_inputs.append("start_date")
        if not state.get("end_date"):
            missing_inputs.append("end_date")

        return PlannerAgent._deduplicate(missing_inputs)

    @staticmethod
    def _build_follow_up_questions(missing_inputs: list[str]) -> list[str]:
        return [
            random.choice(PlannerAgent.FOLLOW_UP_QUESTIONS[missing_input])
            for missing_input in missing_inputs
            if missing_input in PlannerAgent.FOLLOW_UP_QUESTIONS
        ]

    @staticmethod
    def _deduplicate(values: list[str]) -> list[str]:
        deduplicated = []
        for value in values:
            if value not in deduplicated:
                deduplicated.append(value)

        return deduplicated
