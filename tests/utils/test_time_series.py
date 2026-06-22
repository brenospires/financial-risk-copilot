import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.time_series import pivot_time_series


class TestPivotTimeSeries(unittest.TestCase):
    def test_pivots_grouped_records_and_preserves_expected_columns(self) -> None:
        records = [
            {
                "value": 2.0,
                "country": "US",
                "measure": "revenue",
                "timestamp": "2024-12-31",
            },
            {
                "value": 1.0,
                "country": "US",
                "measure": "revenue",
                "timestamp": "2023-12-31",
            },
            {
                "value": 0.5,
                "country": "US",
                "measure": "net_income",
                "timestamp": "2024-12-31",
            },
        ]

        result = pivot_time_series(
            records,
            values="value",
            columns="measure",
            timestamp="timestamp",
            group_columns=("country",),
            expected_columns=("cash", "revenue", "net_income"),
        )

        self.assertEqual(
            list(result.columns),
            ["cash", "revenue", "net_income"],
        )
        self.assertEqual(
            list(result.index.get_level_values("timestamp")),
            [pd.Timestamp("2023-12-31"), pd.Timestamp("2024-12-31")],
        )
        self.assertTrue(pd.isna(result.iloc[0]["cash"]))
        self.assertTrue(pd.isna(result.iloc[0]["net_income"]))
        self.assertEqual(result.iloc[1]["revenue"], 2.0)

    def test_rejects_empty_records(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Time-series records are required",
        ):
            pivot_time_series(
                [],
                values="value",
                columns="measure",
                timestamp="timestamp",
            )

    def test_rejects_missing_required_columns(self) -> None:
        records = [{"timestamp": "2024-12-31", "value": 1.0}]

        with self.assertRaisesRegex(
            ValueError,
            "measure",
        ):
            pivot_time_series(
                records,
                values="value",
                columns="measure",
                timestamp="timestamp",
            )

    def test_rejects_duplicate_canonical_observations(self) -> None:
        records = [
            {
                "value": 1.0,
                "measure": "revenue",
                "timestamp": "2024-12-31",
            },
            {
                "value": 2.0,
                "measure": "revenue",
                "timestamp": "2024-12-31",
            },
        ]

        with self.assertRaisesRegex(
            ValueError,
            "Duplicate canonical",
        ):
            pivot_time_series(
                records,
                values="value",
                columns="measure",
                timestamp="timestamp",
            )

    def test_parses_timezone_aware_timestamp_strings(self) -> None:
        records = [
            {
                "value": 1.0,
                "measure": "revenue",
                "timestamp": "2024-12-31T00:00:00Z",
            },
            {
                "value": 0.5,
                "measure": "net_income",
                "timestamp": "2024-12-31T00:00:00Z",
            },
        ]

        result = pivot_time_series(
            records,
            values="value",
            columns="measure",
            timestamp="timestamp",
            expected_columns=("revenue", "net_income"),
        )

        self.assertEqual(
            list(result.index.get_level_values("timestamp")),
            [pd.Timestamp("2024-12-31T00:00:00Z")],
        )
        self.assertEqual(result.iloc[0]["revenue"], 1.0)

    def test_preserves_expected_columns_when_records_have_extra_metrics(
        self,
    ) -> None:
        records = [
            {
                "value": 1.0,
                "measure": "revenue",
                "timestamp": "2024-12-31",
                "extra": "ignored",
            },
        ]

        result = pivot_time_series(
            records,
            values="value",
            columns="measure",
            timestamp="timestamp",
            expected_columns=("revenue", "cash"),
        )

        self.assertEqual(list(result.columns), ["revenue", "cash"])
        self.assertTrue(pd.isna(result.iloc[0]["cash"]))

    def test_raises_for_invalid_timestamp_strings(self) -> None:
        records = [
            {
                "value": 1.0,
                "measure": "revenue",
                "timestamp": "not-a-date",
            },
        ]

        with self.assertRaises(ValueError):
            pivot_time_series(
                records,
                values="value",
                columns="measure",
                timestamp="timestamp",
            )


if __name__ == "__main__":
    unittest.main()
