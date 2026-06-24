import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from utils.dataframe import get_single_row_value


class TestGetSingleRowValue(unittest.TestCase):
    def test_returns_value_from_existing_column(self) -> None:
        data = pd.DataFrame(
            [
                {
                    "revenue": 100.0,
                }
            ]
        )

        value = get_single_row_value(data, "revenue")

        self.assertEqual(value, 100.0)

    def test_returns_none_for_missing_column(self) -> None:
        data = pd.DataFrame(
            [
                {
                    "revenue": 100.0,
                }
            ]
        )

        value = get_single_row_value(data, "gdp")

        self.assertIsNone(value)

    def test_preserves_missing_value_from_existing_column(self) -> None:
        data = pd.DataFrame(
            [
                {
                    "revenue": pd.NA,
                }
            ]
        )

        value = get_single_row_value(data, "revenue")

        self.assertTrue(pd.isna(value))


if __name__ == "__main__":
    unittest.main()
