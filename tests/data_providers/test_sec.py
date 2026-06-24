import sys
import unittest
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config import sec as sec_config
from config.system_defaults import FRED_PROVIDER, SEC_PROVIDER
from data_models.data_domain import DataDomain
from data_models.data_provider import DataProvider
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.time_series_frequency import TimeSeriesFrequency
from tools.data_providers.sec import SECProvider


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(
        self,
        url: str,
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        self.calls.append(url)

        if url not in self.responses:
            raise AssertionError(f"Unexpected SEC request: {url}")

        return FakeResponse(self.responses[url])


class TestSECProvider(unittest.TestCase):
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"

    def setUp(self) -> None:
        self.sec_provider = SEC_PROVIDER.model_copy(deep=True)
        self.ticker_payload = {
            "0": {
                "cik_str": 320193,
                "ticker": "AAPL",
                "title": "Apple Inc.",
            }
        }

    def provider(
        self,
        facts: dict[str, Any] | None = None,
        provider: DataProvider | None = None,
    ) -> SECProvider:
        responses = {self.TICKERS_URL: self.ticker_payload}
        if facts is not None:
            responses[self.FACTS_URL] = facts

        return SECProvider(
            provider=provider or self.sec_provider,
            user_agent="financial-risk-copilot tests@example.com",
            request_delay=0,
            timeout=10,
            session=FakeSession(responses),
        )

    @staticmethod
    def fact(
        value: float,
        end_date: str,
        *,
        start_date: str | None = None,
        form: str = "10-K",
        filed_date: str = "2025-02-01",
        fiscal_year: int = 2024,
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "val": value,
            "end": end_date,
            "form": form,
            "filed": filed_date,
            "fy": fiscal_year,
            "fp": "FY",
        }

        if start_date is not None:
            item["start"] = start_date

        return item

    @staticmethod
    def company_facts(
        tags: dict[str, list[dict[str, Any]] | dict[str, list[dict[str, Any]]]],
    ) -> dict[str, Any]:
        taxonomy: dict[str, Any] = {}

        for tag, facts in tags.items():
            units = facts if isinstance(facts, dict) else {"USD": facts}
            taxonomy[tag] = {"units": units}

        return {"facts": {"us-gaap": taxonomy}}

    def test_rejects_invalid_provider_configuration(self) -> None:
        invalid_providers = (
            FRED_PROVIDER.model_copy(deep=True),
            DataProvider(
                id=1,
                name="SEC",
                data_domains={DataDomain.MACROECONOMICS},
            ),
            DataProvider(
                id=1,
                name="SEC",
                data_domains={
                    DataDomain.COMPANY,
                    DataDomain.FINANCIAL_STATEMENT,
                },
                supported_frequencies={TimeSeriesFrequency.ANNUAL},
                active=False,
            ),
        )

        for invalid_provider in invalid_providers:
            with self.subTest(provider=invalid_provider):
                with self.assertRaises(ValueError):
                    self.provider(provider=invalid_provider)

    def test_configuration_classifies_every_measure(self) -> None:
        classified = sec_config.SNAPSHOT_MEASURES | sec_config.PERIOD_MEASURES

        self.assertEqual(classified, set(FinancialStatementMeasure))
        self.assertFalse(
            sec_config.SNAPSHOT_MEASURES & sec_config.PERIOD_MEASURES
        )
        self.assertEqual(
            set(sec_config.MEASURE_CANDIDATES),
            set(FinancialStatementMeasure),
        )

    def test_fetch_company_normalizes_ticker(self) -> None:
        company = self.provider().fetch_company(
            ticker=" $aapl ",
            market="NASDAQ",
        )

        self.assertEqual(company.provider_id, 1)
        self.assertEqual(company.ticker, "AAPL")
        self.assertEqual(company.market, "NASDAQ")
        self.assertEqual(company.name, "Apple Inc.")

    def test_fetch_company_rejects_missing_title(self) -> None:
        self.ticker_payload["0"]["title"] = ""

        with self.assertRaisesRegex(ValueError, "no company name"):
            self.provider().fetch_company("AAPL", "NASDAQ")

    def test_returns_annual_dataframe_and_derives_measures(self) -> None:
        annual_start = "2024-01-01"
        annual_end = "2024-12-31"
        facts = self.company_facts(
            {
                "Assets": [
                    self.fact(100, annual_end),
                    self.fact(110, annual_end, form="10-K/A"),
                ],
                "AssetsCurrent": [self.fact(70, annual_end)],
                "LiabilitiesCurrent": [self.fact(30, annual_end)],
                "ShortTermBorrowings": [self.fact(10, annual_end)],
                "LongTermDebtNoncurrent": [self.fact(40, annual_end)],
                "RevenueFromContractWithCustomerExcludingAssessedTax": [
                    self.fact(200, annual_end, start_date=annual_start)
                ],
                "Revenues": [
                    self.fact(999, annual_end, start_date=annual_start)
                ],
                "OperatingIncomeLoss": [
                    self.fact(55, annual_end, start_date=annual_start)
                ],
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxes": [
                    self.fact(60, annual_end, start_date=annual_start)
                ],
                "InterestExpenseNonOperating": [
                    self.fact(-5, annual_end, start_date=annual_start)
                ],
                "DepreciationDepletionAndAmortization": [
                    self.fact(20, annual_end, start_date=annual_start)
                ],
                "NetCashProvidedByUsedInOperatingActivities": [
                    self.fact(50, annual_end, start_date=annual_start)
                ],
                "PaymentsToAcquirePropertyPlantAndEquipment": [
                    self.fact(20, annual_end, start_date=annual_start)
                ],
            }
        )

        frame = self.provider(facts).fetch_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        row = frame.iloc[0]

        self.assertIsInstance(frame, pd.DataFrame)
        self.assertEqual(len(frame), 1)
        self.assertEqual(
            frame.index.names,
            [
                "provider_id",
                "ticker",
                "market",
                "unit",
                "frequency",
                "end_date",
            ],
        )
        self.assertEqual(
            list(frame.columns),
            [measure.value for measure in FinancialStatementMeasure],
        )
        self.assertEqual(row["assets"], 100)
        self.assertEqual(row["revenue"], 200)
        self.assertEqual(row["working_capital"], 40)
        self.assertEqual(row["debt"], 50)
        self.assertEqual(row["free_cash_flow"], 30)
        self.assertEqual(row["ebit"], 65)
        self.assertEqual(row["ebitda"], 85)

    def test_returns_one_ordered_row_per_reporting_date(self) -> None:
        facts = self.company_facts(
            {
                "Assets": [
                    self.fact(90, "2023-12-31", fiscal_year=2023),
                    self.fact(110, "2024-12-31"),
                ]
            }
        )

        frame = self.provider(facts).fetch_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
        )

        self.assertEqual(len(frame), 2)
        self.assertEqual(
            list(frame.index.get_level_values("end_date")),
            list(pd.to_datetime(["2023-12-31", "2024-12-31"])),
        )
        self.assertEqual(list(frame["assets"]), [90, 110])

    def test_exact_date_returns_only_matching_row(self) -> None:
        facts = self.company_facts(
            {
                "Assets": [
                    self.fact(90, "2023-12-31", fiscal_year=2023),
                    self.fact(110, "2024-12-31"),
                ]
            }
        )

        frame = self.provider(facts).fetch_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 12, 31),
        )

        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.iloc[0]["assets"], 110)

    def test_ignores_unsupported_forms_and_short_periods(self) -> None:
        facts = self.company_facts(
            {
                "Assets": [
                    self.fact(10, "2024-12-31", form="10-Q"),
                    self.fact(20, "2024-12-31", form="20-F"),
                    self.fact(30, "2024-12-31", form="40-F"),
                ],
                "RevenueFromContractWithCustomerExcludingAssessedTax": [
                    self.fact(
                        40,
                        "2024-12-31",
                        start_date="2024-10-01",
                    )
                ],
            }
        )

        frame = self.provider(facts).fetch_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        self.assertTrue(frame.empty)
        self.assertEqual(
            list(frame.columns),
            [measure.value for measure in FinancialStatementMeasure],
        )

    def test_selects_one_reporting_unit(self) -> None:
        facts = self.company_facts(
            {
                "Assets": {
                    "EUR": [self.fact(80, "2024-12-31")],
                    "USD": [self.fact(110, "2024-12-31")],
                },
                "Liabilities": {
                    "USD": [self.fact(60, "2024-12-31")],
                },
            }
        )

        frame = self.provider(facts).fetch_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        self.assertEqual(
            set(frame.index.get_level_values("unit")),
            {"USD"},
        )
        self.assertEqual(frame.iloc[0]["assets"], 110)
        self.assertEqual(frame.iloc[0]["liabilities"], 60)

    def test_rejects_unsupported_frequency_and_reversed_dates(self) -> None:
        provider = self.provider()

        for frequency in (
            TimeSeriesFrequency.MONTHLY,
            TimeSeriesFrequency.QUARTERLY,
        ):
            with self.subTest(frequency=frequency):
                with self.assertRaises(ValueError):
                    provider.fetch_financial_statements(
                        ticker="AAPL",
                        market="NASDAQ",
                        frequency=frequency,
                        start_date=date(2024, 1, 1),
                        end_date=date(2024, 12, 31),
                    )

        with self.assertRaises(ValueError):
            provider.fetch_financial_statements(
                ticker="AAPL",
                market="NASDAQ",
                frequency=TimeSeriesFrequency.ANNUAL,
                start_date=date(2025, 1, 1),
                end_date=date(2024, 12, 31),
            )

    def test_caches_ticker_mapping_and_company_facts(self) -> None:
        provider = self.provider(self.company_facts({"Assets": []}))

        for _ in range(2):
            provider.fetch_financial_statements(
                ticker="AAPL",
                market="NASDAQ",
                frequency=TimeSeriesFrequency.ANNUAL,
                start_date=date(2024, 12, 31),
            )

        session = provider.session
        self.assertEqual(session.calls.count(self.TICKERS_URL), 1)
        self.assertEqual(session.calls.count(self.FACTS_URL), 1)


if __name__ == "__main__":
    unittest.main()
