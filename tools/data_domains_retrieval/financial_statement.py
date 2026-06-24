from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

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
    ) -> pd.DataFrame:
        """Retrieve and normalize financial statements without persistence."""

        ...
