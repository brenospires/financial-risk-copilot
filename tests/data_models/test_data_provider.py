import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

sys.path.append(str(Path(__file__).resolve().parents[2]))

from data_models.data_domain import DataDomain
from data_models.data_provider import DataProvider
from data_models.time_series_frequency import TimeSeriesFrequency


class TestDataProvider(unittest.TestCase):
    def test_normalizes_name_and_defaults_to_active(self) -> None:
        provider = DataProvider(
            name=" SEC ",
            data_domains={
                DataDomain.COMPANY,
                DataDomain.FINANCIAL_STATEMENT,
            },
            supported_frequencies={
                TimeSeriesFrequency.QUARTERLY,
                TimeSeriesFrequency.ANNUAL,
            },
        )

        self.assertEqual(provider.name, "SEC")
        self.assertEqual(
            provider.data_domains,
            {
                DataDomain.COMPANY,
                DataDomain.FINANCIAL_STATEMENT,
            },
        )
        self.assertTrue(provider.active)

    def test_rejects_empty_name(self) -> None:
        with self.assertRaises(ValidationError):
            DataProvider(
                name=" ",
                data_domains={DataDomain.FINANCIAL_STATEMENT},
                supported_frequencies={TimeSeriesFrequency.ANNUAL},
            )

    def test_rejects_empty_supported_frequencies(self) -> None:
        with self.assertRaises(ValidationError):
            DataProvider(
                name="SEC",
                data_domains={DataDomain.FINANCIAL_STATEMENT},
                supported_frequencies=set(),
            )

    def test_allows_company_provider_without_frequencies(self) -> None:
        provider = DataProvider(
            name="SEC",
            data_domains={DataDomain.COMPANY},
        )

        self.assertIsNone(provider.supported_frequencies)

    def test_rejects_empty_data_domains(self) -> None:
        with self.assertRaises(ValidationError):
            DataProvider(
                name="SEC",
                data_domains=set(),
            )


if __name__ == "__main__":
    unittest.main()
