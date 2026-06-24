from abc import ABC, abstractmethod

from data_models.company import Company


class CompanyDataProvider(ABC):
    """Contract for external company-data providers."""

    @abstractmethod
    def fetch_company(
        self,
        ticker: str,
        market: str,
    ) -> Company:
        """Retrieve and normalize company data without persistence."""

        ...
