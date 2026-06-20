import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.provider import DataProvider


class TestDataProvider(unittest.TestCase):
    def test_normalizes_name_and_defaults_to_active(self) -> None:
        provider = DataProvider(name=" SEC ")

        self.assertEqual(provider.name, "SEC")
        self.assertTrue(provider.active)

    def test_rejects_empty_name(self) -> None:
        with self.assertRaises(ValidationError):
            DataProvider(name=" ")


if __name__ == "__main__":
    unittest.main()
