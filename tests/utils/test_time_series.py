import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.time_series import (
    calculate_cagr,
    calculate_exponential_trend,
    calculate_linear_trend,
    calculate_period_change,
    carry_forward_time_series,
    exponential_moving_average,
    pivot_time_series,
    regularize_time_series,
)


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


class TestTimeSeriesCalculations(unittest.TestCase):
    def test_carries_values_with_source_timestamp(self) -> None:
        series = pd.Series(
            [1.0, 3.0],
            index=pd.to_datetime(["2024-01-31", "2024-03-31"]),
        )
        target_index = pd.date_range("2024-01-31", "2024-03-31", freq="ME")

        carried = carry_forward_time_series(series, target_index)

        self.assertEqual(carried.loc["2024-02-29", "value"], 1.0)
        self.assertEqual(
            carried.loc["2024-02-29", "source_timestamp"],
            pd.Timestamp("2024-01-31"),
        )
        self.assertTrue(carried.loc["2024-02-29", "is_carried_forward"])
        self.assertFalse(carried.loc["2024-03-31", "is_carried_forward"])

    def test_regularizes_fiscal_dates_and_inserts_missing_periods(self) -> None:
        series = pd.Series(
            [1.0, 3.0, 4.0],
            index=pd.to_datetime(
                ["2023-12-30", "2024-06-29", "2024-09-28"]
            ),
        )

        regularized = regularize_time_series(
            series,
            months_per_period=3,
            tolerance_days=45,
        )

        self.assertEqual(list(regularized["value"]), [1.0, 1.0, 3.0, 4.0])
        self.assertEqual(int(regularized["is_observed"].sum()), 3)
        self.assertTrue(regularized["is_carried_forward"].iloc[1])
        self.assertEqual(
            regularized["source_timestamp"].iloc[1],
            pd.Timestamp("2023-12-30"),
        )

    def test_calculates_calendar_aligned_period_changes(self) -> None:
        cases = {
            "dod": ("2024-01-01", "2024-01-02"),
            "mom": ("2024-01-29", "2024-02-29"),
            "qoq": ("2024-03-30", "2024-06-30"),
            "yoy": ("2023-12-31", "2024-12-31"),
        }

        for period, dates in cases.items():
            with self.subTest(period=period):
                series = pd.Series([2.0, 3.0], index=pd.to_datetime(dates))
                changes = calculate_period_change(series, period)
                latest = changes.iloc[-1]

                self.assertEqual(latest["absolute_change"], 1.0)
                self.assertEqual(latest["relative_change"], 0.5)

    def test_period_change_handles_zero_and_sign_crossing(self) -> None:
        zero_series = pd.Series(
            [0.0, 1.0],
            index=pd.to_datetime(["2023-12-31", "2024-12-31"]),
        )
        crossing_series = pd.Series(
            [-1.0, 1.0],
            index=pd.to_datetime(["2023-12-31", "2024-12-31"]),
        )

        zero_change = calculate_period_change(zero_series, "yoy").iloc[-1]
        crossing = calculate_period_change(crossing_series, "yoy").iloc[-1]

        self.assertTrue(pd.isna(zero_change["relative_change"]))
        self.assertTrue(crossing["sign_crossing"])
        self.assertEqual(crossing["relative_change"], 2.0)

    def test_period_change_uses_adjacent_regularized_periods(self) -> None:
        series = pd.Series(
            [1.0, 2.0, 3.0],
            index=pd.to_datetime(
                ["2024-06-30", "2024-09-30", "2024-12-31"]
            ),
        )

        changes = calculate_period_change(
            series,
            "qoq",
            aligned_periods=True,
        )

        self.assertEqual(changes.iloc[-1]["absolute_change"], 1.0)
        self.assertEqual(changes.iloc[-1]["relative_change"], 0.5)

    def test_exponential_trend_requires_three_observations(self) -> None:
        short_series = pd.Series([1.0, 2.0])
        constant_series = pd.Series(
            [2.0, 2.0, 2.0],
            index=pd.date_range("2022-12-31", periods=3, freq="YE"),
        )

        self.assertIsNone(
            calculate_exponential_trend(
                short_series,
                alpha=0.5,
                period="yoy",
            )
        )
        self.assertEqual(
            calculate_exponential_trend(
                constant_series,
                alpha=0.5,
                period="yoy",
            ),
            0.0,
        )

    def test_linear_trend_preserves_relative_magnitude(self) -> None:
        index = pd.date_range("2000-12-31", periods=21, freq="YE")
        tiny_series = pd.Series(
            [1.0 + value * 0.0001 for value in range(21)],
            index=index,
        )
        large_series = pd.Series(
            [1.0 + value * 100.0 for value in range(21)],
            index=index,
        )

        tiny_trend = calculate_linear_trend(tiny_series)
        large_trend = calculate_linear_trend(large_series)

        self.assertGreater(large_trend, tiny_trend)
        self.assertLess(tiny_trend, 0.001)
        self.assertLess(large_trend, 1.0)

    def test_linear_trend_returns_zero_for_constant_series(self) -> None:
        series = pd.Series(
            [2.0] * 21,
            index=pd.date_range("2000-12-31", periods=21, freq="YE"),
        )

        self.assertAlmostEqual(calculate_linear_trend(series), 0.0)

    def test_cagr_requires_positive_endpoints_and_one_year(self) -> None:
        positive_series = pd.Series(
            [100.0, 110.0, 121.0],
            index=pd.to_datetime(["2022-12-31", "2023-12-31", "2024-12-31"]),
        )
        negative_series = positive_series.copy()
        negative_series.iloc[0] = -100.0

        self.assertAlmostEqual(calculate_cagr(positive_series), 0.1, places=3)
        self.assertIsNone(calculate_cagr(negative_series))

    def test_rejects_invalid_ema_alpha(self) -> None:
        with self.assertRaisesRegex(ValueError, "EMA alpha"):
            exponential_moving_average(pd.Series([1.0]), alpha=0.0)


if __name__ == "__main__":
    unittest.main()
