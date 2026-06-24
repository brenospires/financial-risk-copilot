import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

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
    """Download three annual AMZN 10-K periods as one wide DataFrame."""

    provider = SECProvider(provider=SEC_PROVIDER)
    company = provider.fetch_company(ticker="AMZN", market="NASDAQ")
    frame = provider.fetch_financial_statements(
        ticker="AMZN",
        market="NASDAQ",
        frequency=TimeSeriesFrequency.ANNUAL,
        start_date=date(2023, 1, 1),
        end_date=date(2025, 12, 31),
    )

    assert company.ticker == "AMZN"
    assert company.name
    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 3
    assert not frame.index.has_duplicates
    assert frame.index.names == [
        "provider_id",
        "ticker",
        "market",
        "unit",
        "frequency",
        "end_date",
    ]
    assert list(frame.columns) == [
        measure.value for measure in FinancialStatementMeasure
    ]
    assert set(frame.index.get_level_values("ticker")) == {"AMZN"}
    assert set(frame.index.get_level_values("market")) == {"NASDAQ"}
    assert set(frame.index.get_level_values("unit")) == {"USD"}
    assert set(frame.index.get_level_values("frequency")) == {"annual"}
    assert list(frame.index.get_level_values("end_date")) == list(
        pd.to_datetime(["2023-12-31", "2024-12-31", "2025-12-31"])
    )
    assert frame["assets"].notna().all()
    assert frame["revenue"].notna().all()
    assert frame["working_capital"].notna().all()
    assert frame["debt"].notna().all()
    assert frame["ebit"].notna().all()
    assert frame["ebitda"].notna().all()
    assert frame["free_cash_flow"].notna().all()


if __name__ == "__main__":
    test_sec_provider_pipeline()
