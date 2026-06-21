from abc import ABC, abstractmethod
from datetime import date

from data_models.financial_statement import FinancialStatement
from data_models.time_series_frequency import TimeSeriesFrequency


class FinancialStatementDataProvider(ABC):
    """Contract for external financial-statement data providers."""

    @abstractmethod
    def fetch_financial_statements(
        self,
        ticker: str,
        market: str,
        frequency: TimeSeriesFrequency,
        start_date: date,
        end_date: date | None = None,
    ) -> list[FinancialStatement]:
        """
        Retrieve and normalize financial statements for one company.

        Providing only start_date requests an exact-date snapshot. Providing
        both dates requests an inclusive time series. Implementations must
        reject reversed ranges and must not perform database reads or writes.
        """

        raise NotImplementedError
