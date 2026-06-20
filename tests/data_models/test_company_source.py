import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.company_source import CompanySource


class TestCompanySource(unittest.TestCase):
    def test_normalizes_market_codes(self) -> None:
        source = CompanySource(
            company_id=1,
            provider_id=1,
            provider_company_id="0000320193",
            ticker="aapl",
            market="US",
            exchange="NASDAQ",
            currency="usd",
        )

        self.assertEqual(source.ticker, "AAPL")
        self.assertEqual(source.currency, "USD")

    def test_rejects_invalid_foreign_key(self) -> None:
        with self.assertRaises(ValidationError):
            CompanySource(
                company_id=0,
                provider_id=1,
                provider_company_id="0000320193",
                ticker="AAPL",
                market="US",
            )


if __name__ == "__main__":
    unittest.main()
