import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.company import Company


class TestCompany(unittest.TestCase):
    def test_accepts_minimal_company(self) -> None:
        company = Company(name=" Apple Inc. ")

        self.assertEqual(company.name, "Apple Inc.")
        self.assertIsNone(company.id)

    def test_rejects_empty_name(self) -> None:
        with self.assertRaises(ValidationError):
            Company(name="")


if __name__ == "__main__":
    unittest.main()
