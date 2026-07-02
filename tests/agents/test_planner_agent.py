import json
import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from agents.planner import PlannerAgent


class FakeLLM:
    def __init__(self, response: dict):
        self.response = response

    def invoke(self, prompt: str) -> str:
        return json.dumps(self.response)


class TestPlannerAgent(unittest.TestCase):
    def test_company_name_without_ticker_collects_ticker_input(self) -> None:
        llm = FakeLLM(
            {
                "status": "collecting_inputs",
                "intent": "company_risk_analysis",
                "tickers": [],
                "company_names": ["Apple"],
                "start_date": None,
                "end_date": None,
                "missing_inputs": [],
                "follow_up_questions": [],
                "answer": None,
            }
        )

        state = PlannerAgent(llm=llm).get_status("assess risk for apple")

        self.assertEqual(state["status"], "collecting_inputs")
        self.assertEqual(state["intent"], "company_risk_analysis")
        self.assertEqual(state["tickers"], [])
        self.assertEqual(state["company_names"], ["Apple"])
        self.assertEqual(state["missing_inputs"], ["ticker"])
        self.assertEqual(len(state["follow_up_questions"]), 1)


if __name__ == "__main__":
    unittest.main()
