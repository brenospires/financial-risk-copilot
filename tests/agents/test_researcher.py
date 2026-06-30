import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from agents.researcher import run_company_risk_analysis, run_research_plan
from data_models.time_series_frequency import TimeSeriesFrequency


class FakeStatementTool:
    def __init__(self, statements: pd.DataFrame):
        self.statements = statements
        self.calls: list[dict[str, object]] = []

    def fetch_financial_statements(
        self,
        ticker: str,
        market: str,
        frequency: TimeSeriesFrequency,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        self.calls.append(
            {
                "ticker": ticker,
                "market": market,
                "frequency": frequency,
                "start_date": start_date,
                "end_date": end_date,
            }
        )

        return self.statements


class FakeAdjustmentTool:
    def __init__(self, adjusted: pd.DataFrame):
        self.adjusted = adjusted
        self.input_frame: pd.DataFrame | None = None

    def adjust_financial_statements_by_trend(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        self.input_frame = df

        return self.adjusted


class FakeMetricsTool:
    def __init__(self, metrics: dict[str, float | None]):
        self.metrics = metrics
        self.input_frame: pd.DataFrame | None = None

    def calculate_metrics(
        self,
        df: pd.DataFrame,
    ) -> dict[str, float | None]:
        self.input_frame = df

        return self.metrics


class FailingStatementTool:
    def fetch_financial_statements(self, **kwargs):
        raise RuntimeError("SEC unavailable")


class TestResearcher(unittest.TestCase):
    def test_company_risk_analysis_updates_company_data_and_metrics(self) -> None:
        index = pd.MultiIndex.from_tuples(
            [
                (1, "AAPL", "USA", "USD", "annual", pd.Timestamp("2023-12-31")),
                (1, "AAPL", "USA", "USD", "annual", pd.Timestamp("2024-12-31")),
            ],
            names=[
                "provider_id",
                "ticker",
                "market",
                "unit",
                "frequency",
                "end_date",
            ],
        )
        statements = pd.DataFrame(
            {
                "assets": [90.0, 100.0],
                "revenue": [180.0, 200.0],
            },
            index=index,
        )
        adjusted = pd.DataFrame(
            {
                "end_date": [pd.Timestamp("2024-12-31")],
                "assets": [105.0],
                "revenue": [210.0],
            }
        )
        metrics = {"current_ratio": 1.5}
        state = {
            "status": "ready_for_pipeline",
            "intent": "company_risk_analysis",
            "tickers": ["AAPL"],
            "company_names": ["Apple Inc."],
            "start_date": "2023-01-01",
            "end_date": "2024-12-31",
            "company_data": {},
            "company_metrics": {},
            "errors": [],
        }

        statement_tool = FakeStatementTool(statements)
        adjustment_tool = FakeAdjustmentTool(adjusted)
        metrics_tool = FakeMetricsTool(metrics)

        updated = run_company_risk_analysis(
            state,
            statement_tool=statement_tool,
            adjustment_tool=adjustment_tool,
            metrics_tool=metrics_tool,
        )

        self.assertEqual(
            statement_tool.calls,
            [
                {
                    "ticker": "AAPL",
                    "market": "USA",
                    "frequency": TimeSeriesFrequency.ANNUAL,
                    "start_date": date(2023, 1, 1),
                    "end_date": date(2024, 12, 31),
                }
            ],
        )
        self.assertIsNotNone(adjustment_tool.input_frame)
        self.assertIn("end_date", adjustment_tool.input_frame.columns)
        self.assertIs(metrics_tool.input_frame, adjusted)
        expected_company_data = statements.reset_index().iloc[[-1]].to_dict()

        self.assertEqual(updated["company_data"]["AAPL"], expected_company_data)
        self.assertEqual(updated["company_metrics"]["AAPL"], metrics)
        self.assertEqual(updated["errors"], [])

    def test_company_risk_analysis_records_errors_without_fake_outputs(self) -> None:
        state = {
            "status": "ready_for_pipeline",
            "intent": "company_risk_analysis",
            "tickers": ["AAPL"],
            "company_names": ["Apple Inc."],
            "start_date": "2023-01-01",
            "end_date": "2024-12-31",
            "company_data": {},
            "company_metrics": {},
            "errors": [],
        }

        updated = run_company_risk_analysis(
            state,
            statement_tool=FailingStatementTool(),
        )

        self.assertEqual(updated["company_data"], {})
        self.assertEqual(updated["company_metrics"], {})
        self.assertIn("SEC unavailable", updated["errors"][0])

    def test_run_research_plan_ignores_unimplemented_intents(self) -> None:
        state = {
            "status": "ready_for_pipeline",
            "intent": "company_overview",
            "tickers": ["AAPL"],
            "company_data": {},
            "company_metrics": {},
            "errors": [],
        }

        self.assertIs(run_research_plan(state), state)


if __name__ == "__main__":
    unittest.main()
