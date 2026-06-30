import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from ui.app import (
    build_latest_assessment_state,
    build_research_status_message,
    build_status_response,
    is_completed_risk_assessment,
)


class TestAppResponses(unittest.TestCase):
    def test_status_response_uses_messenger_final_answer(self) -> None:
        response = build_status_response(
            {
                "status": "ready_for_pipeline",
                "final_answer": "Messenger response with calculated metrics.",
                "company_metrics": {
                    "AAPL": {
                        "current_ratio": 1.23456,
                    }
                },
            }
        )

        self.assertEqual(response, "Messenger response with calculated metrics.")

    def test_status_response_uses_direct_response_final_answer(self) -> None:
        response = build_status_response(
            {
                "status": "ready_for_response",
                "final_answer": "Direct chat guidance.",
            }
        )

        self.assertEqual(response, "Direct chat guidance.")

    def test_builds_research_status_message(self) -> None:
        response = build_research_status_message(
            {
                "plan": [{"action": "research_company_risk"}],
                "tickers": ["AMZN"],
                "start_date": "2016-06-25",
                "end_date": "2026-06-25",
            }
        )

        self.assertEqual(
            response,
            "research_company_risk for company AMZN in the data range 2016-06-25 to 2026-06-25.",
        )

    def test_identifies_completed_risk_assessment(self) -> None:
        state = {
            "status": "ready_for_pipeline",
            "intent": "company_risk_analysis",
            "company_metrics": {"AAPL": {"current_ratio": 1.5}},
            "final_answer": "Risk assessment text.",
            "errors": [],
        }

        self.assertTrue(is_completed_risk_assessment(state))
        self.assertEqual(build_latest_assessment_state(state), state)

    def test_rejects_incomplete_assessment_context(self) -> None:
        state = {
            "status": "ready_for_pipeline",
            "intent": "company_risk_analysis",
            "company_metrics": {},
            "final_answer": "",
            "errors": [],
        }

        self.assertFalse(is_completed_risk_assessment(state))
        self.assertIsNone(build_latest_assessment_state(state))

    def test_rejects_failed_assessment_context(self) -> None:
        state = {
            "status": "ready_for_pipeline",
            "intent": "company_risk_analysis",
            "company_metrics": {"AAPL": {"current_ratio": 1.5}},
            "final_answer": "I could not complete the analysis.",
            "errors": ["SEC unavailable"],
        }

        self.assertFalse(is_completed_risk_assessment(state))
        self.assertIsNone(build_latest_assessment_state(state))


if __name__ == "__main__":
    unittest.main()
