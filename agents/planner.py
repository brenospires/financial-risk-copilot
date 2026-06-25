import json
from datetime import date, datetime
from typing import Any

from graph.state import (
    AgentState,
    Intent,
    PlannerStatus,
    SUPPORTED_INTENTS,
    SUPPORTED_PLANNER_STATUSES,
)


PLANNER_SYSTEM_PROMPT = """
# Financial Risk Copilot - Conversation State Extraction Prompt

You are the conversation state manager for a financial-risk copilot.

Your only job is to extract and update structured conversation state from:

* the previous conversation,
* the latest user message,
* the current extracted state.

The latest user message is the final user message in the conversation.

Current date:
{today}

Current extracted state:
{current_state}

Return only valid JSON. Do not include Markdown, code fences, or explanations.

## Output Schema

{
  "status": "collecting_inputs" | "ready_for_pipeline" | "unsupported",
  "intent": "company_risk_analysis" | "company_comparison" | "company_overview" | "unsupported",
  "tickers": ["ticker1"],
  "company_names": ["company name"],
  "start_date": "YYYY-MM-DD" | null,
  "end_date": "YYYY-MM-DD" | null,
  "missing_inputs": [],
  "follow_up_questions": []
}

## General Rules

* Preserve information already present in the current extracted state unless the user explicitly changes it.
* Merge newly extracted information with the current extracted state.
* Never guess low-confidence tickers, company names, dates, or user intent.
* Never remove previously collected information unless the user corrects it.
* Ask the minimum number of follow-up questions needed to complete the state.
* Dates are not required unless the user explicitly requests a specific date range but leaves it incomplete.

## Supported Intents

Use:

* company_risk_analysis for financial risk, liquidity, leverage, profitability, cash-flow, or solvency analysis of one company.
* company_comparison for comparison of two companies.
* company_overview for general company information or a company profile.
* unsupported for requests outside these capabilities.

## Status Rules

Use:

* collecting_inputs when the request is related to the supported product scope but required information is missing.
* ready_for_pipeline when all required information is available.
* unsupported when the request is outside the supported product scope or contains more than two companies.

Do not output planner_error. That status is reserved for runtime failures.

## Required Inputs

company_risk_analysis requires:

* one ticker

company_overview requires:

* one ticker

company_comparison requires:

* exactly two tickers

## Company Identifier Rules

Collect company identity in one planner call whenever possible.

If the user provides a company name and the public-company ticker is confidently
known, add both:

* the ticker to tickers
* the company name to company_names

If the user provides a ticker and the company name is confidently known, add
both:

* the ticker to tickers
* the company name to company_names

Keep tickers and company_names in the same order so each ticker corresponds to
the company name at the same list position.

Do not ask a follow-up question only because one side of a known
name/ticker pair was missing from the user message.

If the company name or ticker is ambiguous, unavailable, or low confidence, keep
the user-provided identifier, add the missing or ambiguous identifier to
missing_inputs, set status to collecting_inputs, and ask one clarifying
question.

If the user provides more than two companies, set status to unsupported and ask
the user to choose no more than two companies.

## Date Rules

If the user provides dates, normalize them to YYYY-MM-DD.

If the user does not specify dates, return null for missing dates. The
application will default the range to the previous five years ending today.

## Follow-Up Rules

If status is collecting_inputs, follow_up_questions must contain one concise
question that asks for the next missing input.

Examples:

Missing company ticker:
"Which ticker should I use for the company you want to analyze?"

Comparison with one ticker:
"Which second ticker should I compare against?"

Unclear supported action:
"Would you like a financial risk assessment, a company comparison, or a company overview?"

If status is ready_for_pipeline, missing_inputs and follow_up_questions must be
empty.
""".strip()


REQUIRED_TICKER_COUNT = {
    "company_risk_analysis": 1,
    "company_comparison": 2,
    "company_overview": 1,
}


class Planner:
    def __init__(self, llm=None):
        from llm import get_llm

        self.llm = llm or get_llm()

    @staticmethod
    def parse_planner_response(raw_response: str) -> dict[str, Any]:
        parsed = json.loads(raw_response.strip())

        if not isinstance(parsed, dict):
            raise ValueError("Planner response must be a JSON object.")

        return parsed

    @staticmethod
    def _clean_strings(value: Any, upper: bool = False) -> list[str]:
        if not isinstance(value, list):
            return []

        cleaned: list[str] = []

        for item in value:
            if not isinstance(item, str):
                continue

            text = item.strip()
            if text:
                cleaned.append(text.upper() if upper else text)

        return list(dict.fromkeys(cleaned))

    @staticmethod
    def _normalize_date(value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return None

    @staticmethod
    def _normalize_current_state(current_state: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = {
            "status": "collecting_inputs",
            "intent": "unsupported",
            "tickers": [],
            "company_names": [],
            "start_date": None,
            "end_date": None,
            "missing_inputs": [],
            "follow_up_questions": [],
        }

        if current_state:
            normalized.update(current_state)

        if normalized["status"] not in SUPPORTED_PLANNER_STATUSES:
            normalized["status"] = "collecting_inputs"

        if normalized["intent"] not in SUPPORTED_INTENTS:
            normalized["intent"] = "unsupported"

        normalized["tickers"] = Planner._clean_strings(normalized.get("tickers"), upper=True)
        normalized["company_names"] = Planner._clean_strings(normalized.get("company_names"))
        normalized["missing_inputs"] = Planner._clean_strings(normalized.get("missing_inputs"))
        normalized["follow_up_questions"] = Planner._clean_strings(normalized.get("follow_up_questions"))
        normalized["start_date"] = Planner._normalize_date(normalized.get("start_date"))
        normalized["end_date"] = Planner._normalize_date(normalized.get("end_date"))

        return normalized

    @staticmethod
    def _merge_list(parsed: dict[str, Any], current_state: dict[str, Any], key: str, upper: bool = False) -> list[str]:
        if key not in parsed:
            return current_state[key]

        return Planner._clean_strings(parsed.get(key), upper=upper)

    def update_state(
        self,
        user_query: str,
        current_state: dict[str, Any] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> AgentState:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        current_state = self._normalize_current_state(current_state)
        prompt = PLANNER_SYSTEM_PROMPT.replace(
            "{current_state}",
            json.dumps(current_state, indent=2),
        ).replace(
            "{today}",
            date.today().isoformat(),
        )
        messages: list[SystemMessage | HumanMessage | AIMessage] = [
            SystemMessage(content=prompt)
        ]

        for message in history or []:
            if message.get("role") == "user":
                messages.append(HumanMessage(content=message.get("content", "")))
            elif message.get("role") == "assistant":
                messages.append(AIMessage(content=message.get("content", "")))

        messages.append(HumanMessage(content=user_query))

        response = self.llm.invoke(messages)
        parsed = self.parse_planner_response(str(response.content))

        return self._merge_state(parsed, current_state, user_query)

    def _merge_state(
        self,
        parsed: dict[str, Any],
        current_state: dict[str, Any],
        user_query: str,
    ) -> AgentState:
        status = parsed.get("status", current_state["status"])
        if status not in SUPPORTED_PLANNER_STATUSES:
            status = current_state["status"]

        intent = parsed.get("intent", current_state["intent"])
        if intent not in SUPPORTED_INTENTS:
            intent = "unsupported"

        tickers = self._merge_list(parsed, current_state, "tickers", upper=True)
        company_names = self._merge_list(parsed, current_state, "company_names")
        missing_inputs = self._merge_list(parsed, current_state, "missing_inputs")
        follow_up_questions = self._merge_list(parsed, current_state, "follow_up_questions")

        start_date = self._merge_date(parsed, current_state, "start_date")
        end_date = self._merge_date(parsed, current_state, "end_date")

        if start_date is None or end_date is None:
            start_date, end_date = default_date_range()

        missing_inputs = add_missing_required_inputs(intent, tickers, missing_inputs)
        status = resolve_status(intent, tickers, missing_inputs, status)
        follow_up_questions = resolve_follow_up_questions(
            intent=intent,
            missing_inputs=missing_inputs,
            questions=follow_up_questions,
            status=status,
            ticker_count=len(tickers),
        )

        state: AgentState = {
            "user_query": user_query,
            "status": status,
            "intent": intent,
            "tickers": tickers,
            "company_names": company_names,
            "start_date": start_date,
            "end_date": end_date,
            "start_year": extract_year(start_date),
            "end_year": extract_year(end_date),
            "needs_sec_data": status == "ready_for_pipeline",
            "needs_comparison": status == "ready_for_pipeline" and intent == "company_comparison",
            "plan": [],
            "missing_inputs": missing_inputs,
            "follow_up_questions": follow_up_questions,
            "company_data": {},
            "macro_data": {},
            "company_metrics": {},
            "comparison_metrics": None,
            "macro_summary": None,
            "missing_data": [],
            "errors": [],
            "analysis_context": {},
            "final_answer": "",
        }
        state["plan"] = build_plan(state)

        return state

    @staticmethod
    def _merge_date(parsed: dict[str, Any], current_state: dict[str, Any], key: str) -> str | None:
        if key not in parsed:
            return current_state[key]

        return Planner._normalize_date(parsed.get(key)) or current_state[key]


def build_state_from_llm(
    user_query: str,
    current_state: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> AgentState:
    return Planner().update_state(user_query, current_state=current_state, history=history)


def build_state_with_llm(
    user_query: str,
    current_state: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> AgentState:
    try:
        return build_state_from_llm(user_query, current_state=current_state, history=history)
    except Exception as exc:
        return build_planner_error_state(user_query, current_state, str(exc))


def build_planner_error_state(
    user_query: str,
    current_state: dict[str, Any] | None,
    error: str,
) -> AgentState:
    normalized = Planner._normalize_current_state(current_state)
    start_date = normalized["start_date"]
    end_date = normalized["end_date"]

    if start_date is None or end_date is None:
        start_date, end_date = default_date_range()

    return {
        "user_query": user_query,
        "status": "planner_error",
        "intent": normalized["intent"],
        "tickers": normalized["tickers"],
        "company_names": normalized["company_names"],
        "start_date": start_date,
        "end_date": end_date,
        "start_year": extract_year(start_date),
        "end_year": extract_year(end_date),
        "needs_sec_data": False,
        "needs_comparison": False,
        "plan": [],
        "missing_inputs": normalized["missing_inputs"],
        "follow_up_questions": [],
        "company_data": {},
        "macro_data": {},
        "company_metrics": {},
        "comparison_metrics": None,
        "macro_summary": None,
        "missing_data": [],
        "errors": [error],
        "analysis_context": {},
        "final_answer": "",
    }


def default_date_range() -> tuple[str, str]:
    today = date.today()

    try:
        start_date = today.replace(year=today.year - 5)
    except ValueError:
        start_date = today.replace(year=today.year - 5, day=28)

    return start_date.isoformat(), today.isoformat()


def extract_year(date_text: str | None) -> int | None:
    if not date_text:
        return None

    return int(date_text[:4])


def add_missing_required_inputs(
    intent: Intent,
    tickers: list[str],
    missing_inputs: list[str],
) -> list[str]:
    missing = list(missing_inputs)
    required_tickers = REQUIRED_TICKER_COUNT.get(intent)

    if required_tickers is None:
        return list(dict.fromkeys(missing))

    if len(tickers) >= required_tickers:
        return list(dict.fromkeys(missing))

    if intent == "company_comparison" and len(tickers) == 1:
        missing.append("comparison_ticker")
    else:
        missing.append("tickers")

    return list(dict.fromkeys(missing))


def resolve_status(
    intent: Intent,
    tickers: list[str],
    missing_inputs: list[str],
    parsed_status: PlannerStatus,
) -> PlannerStatus:
    if len(tickers) > 2:
        return "unsupported"

    if intent == "unsupported" and not missing_inputs:
        return "unsupported"

    if missing_inputs:
        return "collecting_inputs"

    if intent in REQUIRED_TICKER_COUNT:
        return "ready_for_pipeline"

    return parsed_status


def resolve_follow_up_questions(
    intent: Intent,
    missing_inputs: list[str],
    questions: list[str],
    status: PlannerStatus,
    ticker_count: int,
) -> list[str]:
    if status == "ready_for_pipeline":
        return []

    if status == "unsupported":
        if questions:
            return questions[:1]

        if ticker_count > 2:
            return ["Please choose no more than two companies for this workflow."]

        return []

    if status != "collecting_inputs":
        return []

    if questions:
        return questions[:1]

    if "intent" in missing_inputs:
        return [
            "Would you like a financial risk assessment, a company comparison, or a company overview?"
        ]

    if "comparison_ticker" in missing_inputs:
        return ["Which second ticker should I compare against?"]

    if "tickers" in missing_inputs and intent == "company_comparison":
        return ["Which two tickers should I compare?"]

    if "tickers" in missing_inputs:
        return ["Which ticker should I use for the company you want to analyze?"]

    return ["What else should I collect before starting the analysis?"]


def build_plan(state: AgentState) -> list[dict[str, Any]]:
    if state.get("status") != "ready_for_pipeline":
        return []

    plan: list[dict[str, Any]] = []

    for ticker in state["tickers"]:
        plan.append(
            {
                "provider": "sec",
                "ticker": ticker,
                "start_date": state.get("start_date"),
                "end_date": state.get("end_date"),
            }
        )

    return plan
