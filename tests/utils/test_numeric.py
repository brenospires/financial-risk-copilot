import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.numeric import safe_divide


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


if __name__ == "__main__":
    unittest.main()
