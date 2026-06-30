import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from agents.messenger import Messenger


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


class FailingLLM:
    def invoke(self, messages):
        raise RuntimeError("writer unavailable")


class TestMessenger(unittest.TestCase):
    def test_company_risk_analysis_calls_llm_and_updates_final_answer(self) -> None:
        llm = FakeLLM("Full prose risk assessment.")
        state = {
            "status": "ready_for_pipeline",
            "intent": "company_risk_analysis",
            "tickers": ["AAPL"],
            "company_names": ["Apple Inc."],
            "start_date": "2020-01-01",
            "end_date": "2024-12-31",
            "company_data": {
                "AAPL": {
                    "assets": {0: 100.0},
                    "cash": {0: None},
                }
            },
            "company_metrics": {
                "AAPL": {
                    "current_ratio": 1.23456,
                    "cash_ratio": None,
                }
            },
            "errors": [],
        }

        updated = Messenger(llm=llm).update_state(state)

        self.assertEqual(updated["final_answer"], "Full prose risk assessment.")
        self.assertIsNotNone(llm.messages)
        prompt = llm.messages[1].content
        self.assertIn("Apple Inc. (AAPL)", prompt)
        self.assertIn("financial statements in 2024", prompt)
        self.assertIn("3-year trend ending in 2024", prompt)
        self.assertIn('"assets"', prompt)
        self.assertIn('"current_ratio"', prompt)
        self.assertNotIn('"cash"', prompt)
        self.assertNotIn('"cash_ratio"', prompt)
        self.assertIn('adjusted [metric name]', prompt)
        self.assertIn("full text, not bullet points", prompt)
        self.assertIn("low, medium, or high", prompt)

    def test_builds_company_risk_analysis_prompt_with_clean_payload(self) -> None:
        state = {
            "status": "ready_for_pipeline",
            "intent": "company_risk_analysis",
            "tickers": ["AAPL"],
            "company_names": ["Apple Inc."],
            "start_date": "2023-01-01",
            "end_date": "2024-12-31",
            "company_data": {
                "AAPL": {
                    "assets": {0: 100.0},
                    "liabilities": {0: None},
                }
            },
            "company_metrics": {
                "AAPL": {
                    "current_ratio": 1.5,
                    "quick_ratio": None,
                }
            },
            "errors": [],
        }

        prompt = Messenger().build_company_risk_analysis_prompt(state)

        self.assertIn('"assets"', prompt)
        self.assertIn('"current_ratio"', prompt)
        self.assertNotIn('"liabilities"', prompt)
        self.assertNotIn('"quick_ratio"', prompt)
        self.assertIn("adjusted metrics are used", prompt)

    def test_falls_back_when_llm_response_fails(self) -> None:
        state = {
            "status": "ready_for_pipeline",
            "intent": "company_risk_analysis",
            "tickers": ["AAPL"],
            "company_data": {"AAPL": {"assets": {0: 100.0}}},
            "company_metrics": {"AAPL": {"current_ratio": 1.5}},
            "errors": [],
        }

        updated = Messenger(llm=FailingLLM()).update_state(state)

        self.assertIn("writer unavailable", updated["errors"][0])
        self.assertIn("Calculated metrics:", updated["final_answer"])

    def test_chat_intent_guides_user_to_supported_actions(self) -> None:
        state = {
            "status": "ready_for_response",
            "intent": "chat",
            "user_query": "What can you do?",
            "errors": [],
        }

        updated = Messenger().update_state(state)

        self.assertEqual(updated["user_query"], "What can you do?")
        self.assertIn("company financial-risk analysis", updated["final_answer"])
        self.assertIn("company comparisons", updated["final_answer"])
        self.assertIn("company overviews", updated["final_answer"])

    def test_follow_up_without_completed_assessment_returns_guardrail(self) -> None:
        state = {
            "status": "ready_for_response",
            "intent": "follow_up",
            "company_metrics": {},
            "analysis_context": {},
            "final_answer": "",
            "errors": [],
        }

        updated = Messenger().update_state(state)

        self.assertIn("do not have a completed company risk assessment", updated["final_answer"])
        self.assertIn("assess a company's financial risk first", updated["final_answer"])


if __name__ == "__main__":
    unittest.main()
