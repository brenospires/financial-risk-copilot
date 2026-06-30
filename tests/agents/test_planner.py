import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import agents.planner as planner
from agents.planner import Planner, default_date_range


class FakeResponse:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages

        return FakeResponse(self.content)


def planner_with_noop_researcher(llm: FakeLLM) -> Planner:
    return Planner(llm=llm, researcher=lambda state: state)


class TestPlanner(unittest.TestCase):
    def test_builds_ready_state_from_llm_response(self) -> None:
        llm = FakeLLM(
            """
            {
              "status": "ready_for_pipeline",
              "intent": "company_risk_analysis",
              "tickers": ["aapl"],
              "company_names": ["Apple Inc."],
              "start_date": "2019-01-01",
              "end_date": "2024-12-31",
              "missing_inputs": [],
              "follow_up_questions": []
            }
            """
        )

        state = planner_with_noop_researcher(llm).update_state(
            "Analyze the financial risk of AAPL."
        )

        self.assertEqual(state["status"], "ready_for_pipeline")
        self.assertEqual(state["intent"], "company_risk_analysis")
        self.assertEqual(state["tickers"], ["AAPL"])
        self.assertEqual(state["company_names"], ["Apple Inc."])
        self.assertEqual(state["start_date"], "2019-01-01")
        self.assertEqual(state["end_date"], "2024-12-31")
        self.assertTrue(state["needs_sec_data"])
        self.assertFalse(state["needs_comparison"])
        self.assertEqual(len(state["plan"]), 1)
        self.assertEqual(state["plan"][0]["agent"], "researcher")
        self.assertEqual(state["plan"][0]["action"], "research_company_risk")
        self.assertEqual(state["plan"][0]["tickers"], ["AAPL"])

    def test_defaults_to_past_five_years_when_dates_are_missing(self) -> None:
        llm = FakeLLM(
            """
            {
              "status": "ready_for_pipeline",
              "intent": "company_risk_analysis",
              "tickers": ["MSFT"],
              "company_names": ["Microsoft Corporation"],
              "start_date": null,
              "end_date": null,
              "missing_inputs": [],
              "follow_up_questions": []
            }
            """
        )

        state = planner_with_noop_researcher(llm).update_state("Analyze MSFT risk.")

        self.assertEqual(state["status"], "ready_for_pipeline")
        self.assertEqual(state["tickers"], ["MSFT"])
        self.assertEqual(state["company_names"], ["Microsoft Corporation"])
        self.assertEqual(state["start_date"], default_date_range()[0])
        self.assertEqual(state["end_date"], default_date_range()[1])

    def test_completes_ticker_from_company_name_in_one_planner_call(self) -> None:
        llm = FakeLLM(
            """
            {
              "status": "ready_for_pipeline",
              "intent": "company_risk_analysis",
              "tickers": ["AAPL"],
              "company_names": ["Apple Inc."],
              "start_date": null,
              "end_date": null,
              "missing_inputs": [],
              "follow_up_questions": []
            }
            """
        )

        state = planner_with_noop_researcher(llm).update_state("Analyze Apple risk.")

        self.assertEqual(state["status"], "ready_for_pipeline")
        self.assertEqual(state["tickers"], ["AAPL"])
        self.assertEqual(state["company_names"], ["Apple Inc."])
        self.assertEqual(state["missing_inputs"], [])
        self.assertEqual(state["follow_up_questions"], [])
        self.assertTrue(state["needs_sec_data"])
        self.assertEqual(len(state["plan"]), 1)
        self.assertEqual(state["plan"][0]["action"], "research_company_risk")

    def test_comparison_requires_second_ticker_even_if_llm_omits_missing_input(self) -> None:
        llm = FakeLLM(
            """
            {
              "status": "ready_for_pipeline",
              "intent": "company_comparison",
              "tickers": ["MSFT"],
              "company_names": [],
              "start_date": null,
              "end_date": null,
              "missing_inputs": [],
              "follow_up_questions": []
            }
            """
        )

        state = planner_with_noop_researcher(llm).update_state("Compare MSFT.")

        self.assertEqual(state["status"], "collecting_inputs")
        self.assertIn("comparison_ticker", state["missing_inputs"])
        self.assertEqual(state["follow_up_questions"], ["Which second ticker should I compare against?"])
        self.assertFalse(state["needs_comparison"])
        self.assertEqual(state["plan"], [])

    def test_preserves_existing_state_across_follow_up_answers(self) -> None:
        current_state = {
            "status": "collecting_inputs",
            "intent": "company_comparison",
            "tickers": ["MSFT"],
            "company_names": [],
            "start_date": "2020-01-01",
            "end_date": "2024-12-31",
            "missing_inputs": ["comparison_ticker"],
            "follow_up_questions": ["Which second ticker should I compare against?"],
        }
        llm = FakeLLM(
            """
            {
              "status": "ready_for_pipeline",
              "intent": "company_comparison",
              "tickers": ["MSFT", "GOOGL"],
              "company_names": [],
              "start_date": null,
              "end_date": null,
              "missing_inputs": [],
              "follow_up_questions": []
            }
            """
        )

        state = planner_with_noop_researcher(llm).update_state(
            "Use GOOGL.",
            current_state=current_state,
        )

        self.assertEqual(state["status"], "ready_for_pipeline")
        self.assertEqual(state["tickers"], ["MSFT", "GOOGL"])
        self.assertEqual(state["start_date"], "2020-01-01")
        self.assertEqual(state["end_date"], "2024-12-31")
        self.assertTrue(state["needs_comparison"])
        self.assertEqual(len(state["plan"]), 1)
        self.assertEqual(state["plan"][0]["agent"], "researcher")
        self.assertEqual(state["plan"][0]["action"], "research_company_comparison")
        self.assertEqual(state["plan"][0]["tickers"], ["MSFT", "GOOGL"])

    def test_builds_overview_research_plan_for_company_overview(self) -> None:
        llm = FakeLLM(
            """
            {
              "status": "ready_for_pipeline",
              "intent": "company_overview",
              "tickers": ["TSLA"],
              "company_names": ["Tesla, Inc."],
              "start_date": null,
              "end_date": null,
              "missing_inputs": [],
              "follow_up_questions": []
            }
            """
        )

        state = planner_with_noop_researcher(llm).update_state(
            "Give me a Tesla overview."
        )

        self.assertEqual(state["status"], "ready_for_pipeline")
        self.assertEqual(state["intent"], "company_overview")
        self.assertEqual(state["tickers"], ["TSLA"])
        self.assertEqual(len(state["plan"]), 1)
        self.assertEqual(state["plan"][0]["agent"], "researcher")
        self.assertEqual(state["plan"][0]["action"], "research_company_overview")
        self.assertEqual(state["plan"][0]["tickers"], ["TSLA"])

    def test_builds_direct_response_state_for_chat(self) -> None:
        llm = FakeLLM(
            """
            {
              "status": "ready_for_response",
              "intent": "chat",
              "tickers": [],
              "company_names": [],
              "start_date": null,
              "end_date": null,
              "missing_inputs": [],
              "follow_up_questions": []
            }
            """
        )

        state = planner_with_noop_researcher(llm).update_state("Hi there.")

        self.assertEqual(state["user_query"], "Hi there.")
        self.assertEqual(state["status"], "ready_for_response")
        self.assertEqual(state["intent"], "chat")
        self.assertFalse(state["needs_sec_data"])
        self.assertFalse(state["needs_comparison"])
        self.assertEqual(state["plan"], [])

    def test_direct_response_intents_clear_missing_inputs(self) -> None:
        llm = FakeLLM(
            """
            {
              "status": "collecting_inputs",
              "intent": "chat",
              "tickers": [],
              "company_names": [],
              "start_date": null,
              "end_date": null,
              "missing_inputs": ["tickers"],
              "follow_up_questions": ["Which ticker should I use?"]
            }
            """
        )

        state = planner_with_noop_researcher(llm).update_state("What can you do?")

        self.assertEqual(state["status"], "ready_for_response")
        self.assertEqual(state["intent"], "chat")
        self.assertEqual(state["missing_inputs"], [])
        self.assertEqual(state["follow_up_questions"], [])
        self.assertFalse(state["needs_sec_data"])
        self.assertEqual(state["plan"], [])

    def test_builds_direct_response_state_for_follow_up(self) -> None:
        llm = FakeLLM(
            """
            {
              "status": "ready_for_response",
              "intent": "follow_up",
              "tickers": ["AAPL"],
              "company_names": ["Apple Inc."],
              "start_date": null,
              "end_date": null,
              "missing_inputs": [],
              "follow_up_questions": []
            }
            """
        )

        state = planner_with_noop_researcher(llm).update_state(
            "What drove the risk rating?"
        )

        self.assertEqual(state["user_query"], "What drove the risk rating?")
        self.assertEqual(state["status"], "ready_for_response")
        self.assertEqual(state["intent"], "follow_up")
        self.assertEqual(state["tickers"], ["AAPL"])
        self.assertFalse(state["needs_sec_data"])
        self.assertEqual(state["plan"], [])

    def test_calls_researcher_after_completed_extraction(self) -> None:
        llm = FakeLLM(
            """
            {
              "status": "ready_for_pipeline",
              "intent": "company_risk_analysis",
              "tickers": ["AAPL"],
              "company_names": ["Apple Inc."],
              "start_date": "2023-01-01",
              "end_date": "2024-12-31",
              "missing_inputs": [],
              "follow_up_questions": []
            }
            """
        )

        def researcher(state):
            state["company_metrics"] = {"AAPL": {"current_ratio": 1.5}}

            return state

        state = Planner(llm=llm, researcher=researcher).update_state(
            "Analyze Apple risk."
        )

        self.assertEqual(
            state["company_metrics"],
            {"AAPL": {"current_ratio": 1.5}},
        )

    def test_invalid_planner_response_becomes_error_state_without_regex_fallback(self) -> None:
        original_builder = planner.build_state_from_llm

        def fail_planner(*args, **kwargs):
            raise ValueError("No valid JSON object found.")

        planner.build_state_from_llm = fail_planner

        try:
            state = planner.build_state_with_llm("Analyze AAPL risk.")
        finally:
            planner.build_state_from_llm = original_builder

        self.assertEqual(state["status"], "planner_error")
        self.assertEqual(state["user_query"], "Analyze AAPL risk.")
        self.assertEqual(state["tickers"], [])
        self.assertEqual(state["plan"], [])
        self.assertFalse(state["needs_sec_data"])
        self.assertIn("No valid JSON object found.", state["errors"])

    def test_prompt_includes_status_and_follow_up_contract(self) -> None:
        from agents.planner import PLANNER_SYSTEM_PROMPT

        self.assertIn("status", PLANNER_SYSTEM_PROMPT)
        self.assertIn("follow_up_questions", PLANNER_SYSTEM_PROMPT)
        self.assertIn("Collect company identity in one planner call", PLANNER_SYSTEM_PROMPT)
        self.assertIn("past 10 years", PLANNER_SYSTEM_PROMPT)
        self.assertIn("ready_for_response", PLANNER_SYSTEM_PROMPT)
        self.assertIn("follow_up", PLANNER_SYSTEM_PROMPT)
        self.assertIn("chat", PLANNER_SYSTEM_PROMPT)
        self.assertIn("If status is collecting_inputs", PLANNER_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
