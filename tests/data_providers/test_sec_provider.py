import sys
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.settings import SEC_USER_AGENT
from config.system_defaults import SEC_PROVIDER
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.time_series_frequency import TimeSeriesFrequency
from tools.data_providers.sec import SECProvider


@unittest.skipUnless(
    SEC_USER_AGENT,
    "SEC_USER_AGENT is required for live SEC provider tests",
)
def test_sec_provider_pipeline() -> None:
    """Live SEC provider integration test for normalization and canonical selection."""

    ticker = "AAPL"
    market = "NASDAQ"
    frequency = TimeSeriesFrequency.QUARTERLY
    start_date = date(2023, 10, 1)
    end_date = date(2024, 9, 30)

    sec = SECProvider(provider=SEC_PROVIDER)

    company = sec.fetch_company(ticker=ticker, market=market)
    statements = sec.fetch_financial_statements(
        ticker=ticker,
        market=market,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
    )
    single_date = date(2024, 6, 29)
    single_date_statements = sec.fetch_financial_statements(
        ticker=ticker,
        market=market,
        frequency=frequency,
        start_date=single_date,
    )

    available_measures = {statement.measure for statement in statements}
    missing_measures = set(FinancialStatementMeasure) - available_measures
    observations_by_measure = Counter(
        statement.measure.value for statement in statements
    )
    observations_by_period = Counter(
        statement.end_date.isoformat() for statement in statements
    )
    observation_identities = Counter(
        (
            statement.measure,
            statement.observation_type,
            statement.start_date,
            statement.end_date,
            statement.unit,
        )
        for statement in statements
    )
    duplicate_observations = {
        identity: count
        for identity, count in observation_identities.items()
        if count > 1
    }
    reporting_units = {statement.unit for statement in statements}
    coverage = len(available_measures) / len(FinancialStatementMeasure)

    print("\nCompany:")
    print(company.model_dump())

    print("\nRequest:")
    print(
        {
            "ticker": ticker,
            "market": market,
            "frequency": frequency.value,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
    )

    print(f"\nNormalized observations: {len(statements)}")
    print(f"Available measures: {len(available_measures)}")
    print(sorted(measure.value for measure in available_measures))
    print(f"Measure coverage: {coverage:.1%}")

    print(f"\nMissing measures: {len(missing_measures)}")
    print(sorted(measure.value for measure in missing_measures))

    print("\nObservations by measure:")
    print(dict(sorted(observations_by_measure.items())))

    print("\nObservations by period:")
    print(dict(sorted(observations_by_period.items())))

    print("\nIntegrity checks:")
    print(
        {
            "expected_quarters": 4,
            "observed_periods": len(observations_by_period),
            "reporting_units": sorted(reporting_units),
            "duplicate_observations": len(duplicate_observations),
        }
    )

    print("\nFirst 20 normalized observations:")
    for statement in statements[:20]:
        print(statement.model_dump())

    single_date_measures = {
        statement.measure for statement in single_date_statements
    }
    single_date_identities = Counter(
        (
            statement.measure,
            statement.observation_type,
            statement.start_date,
            statement.end_date,
            statement.unit,
        )
        for statement in single_date_statements
    )

    print("\nSingle-date request:")
    print(
        {
            "requested_date": single_date.isoformat(),
            "observations": len(single_date_statements),
            "available_measures": len(single_date_measures),
            "missing_measures": sorted(
                measure.value
                for measure in (
                    set(FinancialStatementMeasure) - single_date_measures
                )
            ),
        }
    )

    assert company.ticker == ticker
    assert company.name
    assert statements
    assert company.provider_id == SEC_PROVIDER.id
    assert all(statement.provider_id == SEC_PROVIDER.id for statement in statements)
    assert all(statement.ticker == ticker for statement in statements)
    assert all(statement.market == market for statement in statements)
    assert all(statement.frequency is frequency for statement in statements)
    assert all(
        start_date <= statement.end_date <= end_date
        for statement in statements
    )
    assert statements == sorted(
        statements,
        key=lambda statement: (
            statement.end_date,
            statement.start_date or date.min,
            statement.measure.value,
        ),
    )
    assert len(observations_by_period) == 4
    assert not duplicate_observations
    assert single_date_statements
    assert all(
        statement.end_date == single_date
        for statement in single_date_statements
    )
    assert all(
        statement.provider_id == SEC_PROVIDER.id
        for statement in single_date_statements
    )
    assert all(count == 1 for count in single_date_identities.values())

    print("\nSECProvider pipeline completed successfully.")


if __name__ == "__main__":
    test_sec_provider_pipeline()
