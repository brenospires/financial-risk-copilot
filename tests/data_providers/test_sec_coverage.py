import sys
import unittest
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.settings import SEC_USER_AGENT
from config.system_defaults import SEC_PROVIDER
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.time_series_frequency import TimeSeriesFrequency
from tools.data_providers.sec import SECProvider


COMPANIES = {
    "MSFT": "NASDAQ",
    "GOOGL": "NASDAQ",
    "AMZN": "NASDAQ",
    "JPM": "NYSE",
    "XOM": "NYSE",
    "JNJ": "NYSE",
    "WMT": "NYSE",
    "CAT": "NYSE",
    "KO": "NYSE",
    "NVDA": "NASDAQ",
}
LOW_COVERAGE_THRESHOLD = 0.7


@unittest.skipUnless(
    SEC_USER_AGENT,
    "SEC_USER_AGENT is required for live SEC coverage tests",
)
def test_sec_provider_coverage() -> None:
    """Compare live quarterly SEC measure coverage across companies."""

    sec = SECProvider(provider=SEC_PROVIDER)
    measure_count = len(FinancialStatementMeasure)
    range_support: Counter[FinancialStatementMeasure] = Counter()
    single_date_support: Counter[FinancialStatementMeasure] = Counter()
    results: list[dict[str, object]] = []

    for ticker, market in COMPANIES.items():
        statements = sec.fetch_financial_statements(
            ticker=ticker,
            market=market,
            frequency=TimeSeriesFrequency.QUARTERLY,
            start_date=date(2023, 1, 1),
            end_date=date(2024, 12, 31),
        )
        statements_by_date: dict[date, list[object]] = defaultdict(list)

        for statement in statements:
            statements_by_date[statement.end_date].append(statement)

        assert statements_by_date, f"No SEC statements returned for {ticker}"

        best_date = max(
            statements_by_date,
            key=lambda reporting_date: (
                len(
                    {
                        statement.measure
                        for statement in statements_by_date[reporting_date]
                    }
                ),
                reporting_date,
            ),
        )
        single_date_statements = sec.fetch_financial_statements(
            ticker=ticker,
            market=market,
            frequency=TimeSeriesFrequency.QUARTERLY,
            start_date=best_date,
        )
        range_measures = {statement.measure for statement in statements}
        single_date_measures = {
            statement.measure for statement in single_date_statements
        }

        range_support.update(range_measures)
        single_date_support.update(single_date_measures)
        results.append(
            {
                "ticker": ticker,
                "best_date": best_date.isoformat(),
                "range_coverage": len(range_measures),
                "single_date_coverage": len(single_date_measures),
                "missing_single_date": sorted(
                    measure.value
                    for measure in (
                        set(FinancialStatementMeasure) - single_date_measures
                    )
                ),
            }
        )

        assert single_date_statements
        assert all(
            statement.end_date == best_date
            for statement in single_date_statements
        )

    print("\nCompany coverage:")
    for result in results:
        print(result)

    print("\nMeasure support across 10 companies:")
    for measure in FinancialStatementMeasure:
        print(
            {
                "measure": measure.value,
                "range_support": f"{range_support[measure]}/10",
                "single_date_support": f"{single_date_support[measure]}/10",
            }
        )

    average_range_coverage = sum(
        int(result["range_coverage"]) for result in results
    ) / len(results)
    average_single_date_coverage = sum(
        int(result["single_date_coverage"]) for result in results
    ) / len(results)
    complete_companies = [
        str(result["ticker"])
        for result in results
        if result["single_date_coverage"] == measure_count
    ]
    universally_supported_measures = [
        measure.value
        for measure in FinancialStatementMeasure
        if single_date_support[measure] == len(COMPANIES)
    ]
    low_coverage_measures = [
        measure.value
        for measure in FinancialStatementMeasure
        if single_date_support[measure] / len(COMPANIES)
        < LOW_COVERAGE_THRESHOLD
    ]

    print("\nSummary:")
    print(
        {
            "companies": len(results),
            "available_measures": measure_count,
            "average_range_coverage": f"{average_range_coverage:.1f}/23",
            "average_single_date_coverage": (
                f"{average_single_date_coverage:.1f}/23"
            ),
        }
    )
    print(
        {
            "complete_companies": complete_companies,
            "universally_supported_measures": universally_supported_measures,
            "low_coverage_measures": low_coverage_measures,
        }
    )


if __name__ == "__main__":
    test_sec_provider_coverage()
