import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.numeric import (
    safe_divide,
    divide_or_none,
    absolute_or_none,
    subtract_or_none,
    to_float_or_none,
)


class TestSafeDivide(unittest.TestCase):
    def test_divides_aligned_series(self) -> None:
        numerator = pd.Series([10.0, 20.0], dtype="Float64")
        denominator = pd.Series([2.0, 4.0], dtype="Float64")

        result = safe_divide(numerator, denominator)

        self.assertEqual(result.tolist(), [5.0, 5.0])

    def test_masks_missing_values_and_zero_denominators(self) -> None:
        numerator = pd.Series([10.0, pd.NA, 30.0], dtype="Float64")
        denominator = pd.Series([0.0, 2.0, pd.NA], dtype="Float64")

        result = safe_divide(numerator, denominator)

        self.assertTrue(result.isna().all())


class TestScalarNumericOperations(unittest.TestCase):
    def test_converts_numeric_scalars_to_float(self) -> None:
        self.assertEqual(to_float_or_none(10), 10.0)
        self.assertEqual(to_float_or_none("10.5"), 10.5)

    def test_returns_none_for_missing_or_non_numeric_values(self) -> None:
        self.assertIsNone(to_float_or_none(None))
        self.assertIsNone(to_float_or_none(pd.NA))
        self.assertIsNone(to_float_or_none("not numeric"))
        self.assertIsNone(to_float_or_none([1.0]))

    def test_subtracts_nullable_values(self) -> None:
        self.assertEqual(subtract_or_none(10.0, 4.0), 6.0)
        self.assertIsNone(subtract_or_none(pd.NA, 4.0))
        self.assertIsNone(subtract_or_none(10.0, "not numeric"))

    def test_returns_absolute_nullable_value(self) -> None:
        self.assertEqual(absolute_or_none(-10.0), 10.0)
        self.assertEqual(absolute_or_none(10.0), 10.0)
        self.assertIsNone(absolute_or_none(pd.NA))
        self.assertIsNone(absolute_or_none("not numeric"))

    def test_divides_nullable_values(self) -> None:
        self.assertEqual(divide_or_none(10.0, 2.0), 5.0)
        self.assertIsNone(divide_or_none(pd.NA, 2.0))
        self.assertIsNone(divide_or_none(10.0, pd.NA))
        self.assertIsNone(divide_or_none(10.0, 0.0))


if __name__ == "__main__":
    unittest.main()
