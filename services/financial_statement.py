from datetime import date

from data_models.financial_statement import FinancialStatement
from data_models.time_series_frequency import TimeSeriesFrequency
from database.financial_statement_repository import FinancialStatementRepository
from tools.data_domains_retrieval.financial_statement import (
    FinancialStatementDataProvider,
)


class FinancialStatementService:
    """Coordinate database-first financial-statement retrieval."""

    MAXIMUM_PERIOD_GAP_DAYS = {
        TimeSeriesFrequency.DAILY: 2,
        TimeSeriesFrequency.MONTHLY: 45,
        TimeSeriesFrequency.QUARTERLY: 150,
        TimeSeriesFrequency.ANNUAL: 400,
    }

    def __init__(
        self,
        provider: FinancialStatementDataProvider,
        repository: FinancialStatementRepository,
    ) -> None:
        self.provider = provider
        self.repository = repository

    def get_financial_statements(
        self,
        ticker: str,
        market: str,
        frequency: TimeSeriesFrequency,
        start_date: date,
        end_date: date | None = None,
        refresh: bool = False,
    ) -> list[FinancialStatement]:
        """
        Retrieve persisted statements and fill reporting-period coverage gaps.

        Existing observations are returned without an external request when
        they cover the requested period. When coverage is absent, incomplete,
        or explicitly refreshed, the provider is called once, its canonical
        observations are upserted, and the requested period is queried again.
        Missing measures inside an existing reporting period are not treated as
        temporal coverage gaps.
        """

        statements = self.repository.get_for_period(
            ticker=ticker,
            market=market,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
        )

        if refresh or self._has_data_holes(
            statements=statements,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
        ):
            fetched_statements = self.provider.fetch_financial_statements(
                ticker=ticker,
                market=market,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
            )

            for statement in fetched_statements:
                self.repository.upsert(statement)

            statements = self.repository.get_for_period(
                ticker=ticker,
                market=market,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
            )

        return statements

    def _has_data_holes(
        self,
        statements: list[FinancialStatement],
        frequency: TimeSeriesFrequency,
        start_date: date,
        end_date: date | None,
    ) -> bool:
        """Return whether reporting-period coverage is incomplete."""

        if not statements:
            return True

        if end_date is None:
            return False

        observed_dates = sorted(
            {statement.end_date for statement in statements}
        )
        maximum_gap = self.MAXIMUM_PERIOD_GAP_DAYS[frequency]
        coverage_dates = [start_date, *observed_dates, end_date]

        return any(
            (current_date - previous_date).days > maximum_gap
            for previous_date, current_date in zip(
                coverage_dates,
                coverage_dates[1:],
            )
        )
