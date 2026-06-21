import sys
import unittest
from datetime import date
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.system_defaults import FRED_PROVIDER, SEC_PROVIDER
from data_models.data_domain import DataDomain
from data_models.data_provider import DataProvider
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency
from tools.data_providers.sec import SECProvider


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self.payload = payload
        self.raise_for_status_called = False

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True

    def json(self) -> Any:
        return self.payload


class FakeSession:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }
        )

        if url not in self.responses:
            raise AssertionError(f"Unexpected SEC request: {url}")

        return FakeResponse(self.responses[url])


class TestSECProvider(unittest.TestCase):
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK0000320193.json"

    def setUp(self) -> None:
        self.sec_provider = SEC_PROVIDER.model_copy(deep=True)

    def provider(
        self,
        responses: dict[str, Any] | None = None,
        provider: DataProvider | None = None,
    ) -> SECProvider:
        return SECProvider(
            provider=provider or self.sec_provider,
            user_agent="financial-risk-copilot tests@example.com",
            request_delay=0,
            timeout=10,
            session=FakeSession(responses or {}),
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
        fiscal_period: str = "FY",
        frame: str | None = None,
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "val": value,
            "end": end_date,
            "form": form,
            "filed": filed_date,
            "fy": fiscal_year,
            "fp": fiscal_period,
        }

        if start_date is not None:
            item["start"] = start_date

        if frame is not None:
            item["frame"] = frame

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

    @staticmethod
    def values_by_measure(statements: list[Any]) -> dict[Any, float]:
        return {
            statement.measure: statement.value for statement in statements
        }

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

    def test_classifies_and_maps_every_supported_measure(self) -> None:
        classified_measures = (
            SECProvider.SNAPSHOT_MEASURES | SECProvider.PERIOD_MEASURES
        )

        self.assertEqual(classified_measures, set(FinancialStatementMeasure))
        self.assertFalse(
            SECProvider.SNAPSHOT_MEASURES & SECProvider.PERIOD_MEASURES
        )
        self.assertEqual(
            set(SECProvider.MEASURE_CANDIDATES),
            set(FinancialStatementMeasure),
        )

    def test_fetch_company_normalizes_ticker_and_maps_metadata(self) -> None:
        session = FakeSession(
            {
                self.TICKERS_URL: {
                    "0": {
                        "cik_str": 320193,
                        "ticker": "AAPL",
                        "title": "Apple Inc.",
                    }
                }
            }
        )
        provider = SECProvider(
            provider=self.sec_provider,
            user_agent="financial-risk-copilot tests@example.com",
            request_delay=0,
            timeout=10,
            session=session,
        )

        company = provider.fetch_company(ticker=" $aapl ", market="NASDAQ")

        self.assertEqual(company.provider_id, 1)
        self.assertEqual(company.ticker, "AAPL")
        self.assertEqual(company.market, "NASDAQ")
        self.assertEqual(company.name, "Apple Inc.")
        self.assertIsNone(company.country)
        self.assertIsNone(company.sector)
        self.assertEqual(len(session.calls), 1)

    def test_fetch_company_uses_submissions_as_name_fallback(self) -> None:
        provider = self.provider(
            {
                self.TICKERS_URL: {
                    "0": {
                        "cik_str": 320193,
                        "ticker": "AAPL",
                        "title": "",
                    }
                },
                self.SUBMISSIONS_URL: {"name": "Apple Inc."},
            }
        )

        company = provider.fetch_company(ticker="AAPL", market="NASDAQ")

        self.assertEqual(company.name, "Apple Inc.")

    def test_fetch_annual_statements_deduplicates_and_derives_measures(
        self,
    ) -> None:
        annual_start = "2024-01-01"
        annual_end = "2024-12-31"
        facts = self.company_facts(
            {
                "Assets": [
                    self.fact(
                        100,
                        annual_end,
                        filed_date="2025-02-01",
                    ),
                    self.fact(
                        110,
                        annual_end,
                        form="10-K/A",
                        filed_date="2025-03-01",
                    ),
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
        provider = self.provider({self.FACTS_URL: facts, self.TICKERS_URL: {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }})

        statements = provider.fetch_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        values = self.values_by_measure(statements)

        self.assertEqual(values[FinancialStatementMeasure.ASSETS], 110)
        self.assertEqual(values[FinancialStatementMeasure.REVENUE], 200)
        self.assertEqual(values[FinancialStatementMeasure.WORKING_CAPITAL], 40)
        self.assertEqual(values[FinancialStatementMeasure.DEBT], 50)
        self.assertEqual(values[FinancialStatementMeasure.FREE_CASH_FLOW], 30)
        self.assertEqual(values[FinancialStatementMeasure.EBIT], 65)
        self.assertEqual(values[FinancialStatementMeasure.EBITDA], 85)
        self.assertTrue(all(statement.provider_id == 1 for statement in statements))
        self.assertTrue(all(statement.company_id is None for statement in statements))
        self.assertEqual(
            statements,
            sorted(
                statements,
                key=lambda statement: (
                    statement.end_date,
                    statement.start_date or date.min,
                    statement.measure.value,
                ),
            ),
        )

    def test_exact_date_request_returns_only_matching_period(self) -> None:
        facts = self.company_facts(
            {
                "Assets": [
                    self.fact(90, "2023-12-31", fiscal_year=2023),
                    self.fact(110, "2024-12-31"),
                ]
            }
        )
        provider = self.provider({self.FACTS_URL: facts, self.TICKERS_URL: {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }})

        statements = provider.fetch_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 12, 31),
        )

        self.assertEqual(len(statements), 1)
        self.assertEqual(statements[0].end_date, date(2024, 12, 31))
        self.assertEqual(statements[0].value, 110)

    def test_quarterly_request_excludes_cumulative_flow(self) -> None:
        facts = self.company_facts(
            {
                "RevenueFromContractWithCustomerExcludingAssessedTax": [
                    self.fact(
                        25,
                        "2024-03-31",
                        start_date="2024-01-01",
                        form="10-Q",
                        filed_date="2024-05-01",
                        fiscal_period="Q1",
                        frame="CY2024Q1",
                    ),
                    self.fact(
                        70,
                        "2024-06-30",
                        start_date="2024-01-01",
                        form="10-Q",
                        filed_date="2024-08-01",
                        fiscal_period="Q2",
                    ),
                    self.fact(
                        45,
                        "2024-06-30",
                        start_date="2024-04-01",
                        form="10-Q",
                        filed_date="2024-08-01",
                        fiscal_period="Q2",
                        frame="CY2024Q2",
                    ),
                ]
            }
        )
        provider = self.provider({self.FACTS_URL: facts, self.TICKERS_URL: {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }})

        statements = provider.fetch_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.QUARTERLY,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        self.assertEqual([statement.value for statement in statements], [25, 45])
        self.assertTrue(
            all(
                statement.observation_type is ObservationType.PERIOD
                for statement in statements
            )
        )

    def test_selects_one_reporting_unit_for_requested_period(self) -> None:
        facts = self.company_facts(
            {
                "Assets": {
                    "EUR": [self.fact(80, "2023-12-31", fiscal_year=2023)],
                    "USD": [self.fact(110, "2024-12-31")],
                },
                "Liabilities": {
                    "USD": [self.fact(60, "2024-12-31")],
                },
            }
        )
        provider = self.provider({self.FACTS_URL: facts, self.TICKERS_URL: {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }})

        statements = provider.fetch_financial_statements(
            ticker="AAPL",
            market="NASDAQ",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

        self.assertEqual({statement.unit for statement in statements}, {"USD"})
        self.assertEqual(len(statements), 2)

    def test_maps_ifrs_facts_from_foreign_filer(self) -> None:
        facts = {
            "facts": {
                "ifrs-full": {
                    "Assets": {
                        "units": {
                            "EUR": [
                                self.fact(
                                    500,
                                    "2024-12-31",
                                    form="20-F",
                                )
                            ]
                        }
                    },
                    "Revenue": {
                        "units": {
                            "EUR": [
                                self.fact(
                                    300,
                                    "2024-12-31",
                                    start_date="2024-01-01",
                                    form="20-F",
                                )
                            ]
                        }
                    },
                }
            }
        }
        provider = self.provider({self.FACTS_URL: facts, self.TICKERS_URL: {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }})

        statements = provider.fetch_financial_statements(
            ticker="AAPL",
            market="NYSE",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        values = self.values_by_measure(statements)

        self.assertEqual(values[FinancialStatementMeasure.ASSETS], 500)
        self.assertEqual(values[FinancialStatementMeasure.REVENUE], 300)
        self.assertEqual({statement.unit for statement in statements}, {"EUR"})

    def test_respects_provider_frequency_configuration(self) -> None:
        annual_only_provider = DataProvider(
            id=1,
            name="SEC",
            data_domains={
                DataDomain.COMPANY,
                DataDomain.FINANCIAL_STATEMENT,
            },
            supported_frequencies={TimeSeriesFrequency.ANNUAL},
        )
        provider = self.provider(provider=annual_only_provider)

        with self.assertRaises(ValueError):
            provider.fetch_financial_statements(
                ticker="AAPL",
                market="NASDAQ",
                frequency=TimeSeriesFrequency.QUARTERLY,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 3, 31),
            )

    def test_rejects_unsupported_frequency_and_reversed_dates(self) -> None:
        provider = self.provider()

        with self.assertRaises(ValueError):
            provider.fetch_financial_statements(
                ticker="AAPL",
                market="NASDAQ",
                frequency=TimeSeriesFrequency.MONTHLY,
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
        session = FakeSession(
            {
                self.TICKERS_URL: {
                    "0": {
                        "cik_str": 320193,
                        "ticker": "AAPL",
                        "title": "Apple Inc.",
                    }
                },
                self.FACTS_URL: self.company_facts({"Assets": []}),
            }
        )
        provider = SECProvider(
            provider=self.sec_provider,
            user_agent="financial-risk-copilot tests@example.com",
            request_delay=0,
            timeout=10,
            session=session,
        )

        for _ in range(2):
            provider.fetch_financial_statements(
                ticker="AAPL",
                market="NASDAQ",
                frequency=TimeSeriesFrequency.ANNUAL,
                start_date=date(2024, 12, 31),
            )

        requested_urls = [call["url"] for call in session.calls]
        self.assertEqual(requested_urls.count(self.TICKERS_URL), 1)
        self.assertEqual(requested_urls.count(self.FACTS_URL), 1)


if __name__ == "__main__":
    unittest.main()
