from datetime import datetime, timedelta
from typing import Any, Optional
from fredapi import Fred
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.settings import FRED_API_KEY
from src.database.fred_repository import FREDRepository

class FREDTool:
    """
    FRED provider facade.

    This class owns the FRED data workflow:
    - FRED API calls
    - database-first retrieval
    - API fallback
    - observation normalization
    - persistence through FREDRepository
    - normalized output for ResearcherNode

    This class does not calculate macro summaries or final risk interpretation.
    Those responsibilities belong to the financial metrics layer.
    """

    DEFAULT_INDICATORS: dict[str, str] = {
        "GDP": "Gross Domestic Product",
        "UNRATE": "Unemployment Rate",
        "CPIAUCSL": "Consumer Price Index",
        "FEDFUNDS": "Federal Funds Rate",
        "DGS10": "10-Year Treasury Rate",
        "T10Y2Y": "10Y-2Y Treasury Spread",
    }

    DEFAULT_START_DATE = "2018-01-01"

    # Used to avoid refetching every time a user asks for data up to "today".
    # Some FRED series are monthly or quarterly, so the latest observation may
    # naturally lag the current date.
    CURRENT_DATA_MAX_LAG_DAYS = 180

    def __init__(
        self,
        api_key: Optional[str] = None,
    ) -> None:
        resolved_api_key = api_key or FRED_API_KEY

        if not resolved_api_key:
            raise ValueError(
                "FRED_API_KEY is required. "
                "Set FRED_API_KEY in your .env file or pass api_key explicitly."
            )

        self.fred = Fred(api_key=resolved_api_key)
        self._repository: Optional[FREDRepository] = None

    def get_macro_data(
        self,
        indicators: Optional[list[str] | dict[str, str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Public method used by ResearcherNode.

        Returns normalized macroeconomic data for one or more FRED indicators.

        If indicators is None, the default macro basket is used.
        """

        start_date = start_date or self.DEFAULT_START_DATE

        normalized_indicators = self._normalize_indicators(indicators)

        results: dict[str, Any] = {}
        errors: list[str] = []

        for series_id, indicator_name in normalized_indicators.items():
            result = self.get_indicator_data(
                series_id=series_id,
                indicator_name=indicator_name,
                start_date=start_date,
                end_date=end_date,
                refresh=refresh,
            )

            results[series_id] = result

            for error in result.get("errors", []):
                errors.append(error)

        return {
            "indicators": results,
            "start_date": start_date,
            "end_date": end_date,
            "errors": errors,
        }

    def get_indicator_data(
        self,
        series_id: str,
        indicator_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Return normalized data for a single FRED series.

        Workflow:
        1. Normalize series ID.
        2. Check SQLite first.
        3. If data is missing, incomplete, or refresh=True, fetch from FRED API.
        4. Normalize observations.
        5. Persist through FREDRepository.
        6. Re-query SQLite.
        7. Return standardized data.
        """

        series_id = self._normalize_series_id(series_id)
        indicator_name = indicator_name or self.DEFAULT_INDICATORS.get(series_id, series_id)
        start_date = start_date or self.DEFAULT_START_DATE

        repository = self._get_repository()

        errors: list[str] = []
        source = "database"

        try:
            repository.save_indicator_metadata(
                series_id=series_id,
                indicator_name=indicator_name,
            )

            if refresh or not self._has_required_data(
                series_id=series_id,
                start_date=start_date,
                end_date=end_date,
            ):
                observations = self._fetch_series(
                    series_id=series_id,
                    indicator_name=indicator_name,
                    start_date=start_date,
                    end_date=end_date,
                )

                repository.save_observations(observations)
                source = "api_then_database"

        except Exception as exc:
            errors.append(f"FRED fetch failed for {series_id}: {exc}")
            source = "database_after_api_error"

        observations = repository.get_observations(
            series_id=series_id,
            start_date=start_date,
            end_date=end_date,
        )

        return self._build_indicator_response(
            series_id=series_id,
            indicator_name=indicator_name,
            observations=observations,
            start_date=start_date,
            end_date=end_date,
            source=source,
            errors=errors,
        )

    def _get_repository(self) -> FREDRepository:
        """
        Lazily instantiate the FRED repository.

        FREDRepository should own the project database path internally,
        preferably through config.settings.DATABASE_PATH.
        """

        if self._repository is None:
            self._repository = FREDRepository()

        return self._repository

    def _fetch_series(
        self,
        series_id: str,
        indicator_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch a FRED series from the API and normalize it.

        The fredapi package returns a pandas Series. This method converts it
        into plain dictionaries so the result can safely be stored in LangGraph
        state and SQLite.
        """

        series = self.fred.get_series(
            series_id,
            observation_start=start_date,
            observation_end=end_date,
        )

        observations: list[dict[str, Any]] = []

        for date_value, raw_value in series.items():
            value = self._safe_float(raw_value)

            if value is None:
                continue

            observations.append(
                {
                    "series_id": series_id,
                    "indicator_name": indicator_name,
                    "date": self._normalize_date(date_value),
                    "value": value,
                }
            )

        return observations

    def _normalize_indicators(
        self,
        indicators: Optional[list[str] | dict[str, str]],
    ) -> dict[str, str]:
        """
        Normalize planner-provided indicators into this structure:

        {
            "GDP": "Gross Domestic Product",
            "UNRATE": "Unemployment Rate"
        }

        If indicators is None, the default macro basket is used.
        """

        if indicators is None:
            return dict(self.DEFAULT_INDICATORS)

        if isinstance(indicators, dict):
            return {
                self._normalize_series_id(series_id): indicator_name
                for series_id, indicator_name in indicators.items()
            }

        normalized: dict[str, str] = {}

        for series_id in indicators:
            normalized_series_id = self._normalize_series_id(series_id)

            normalized[normalized_series_id] = self.DEFAULT_INDICATORS.get(
                normalized_series_id,
                normalized_series_id,
            )

        return normalized

    def _has_required_data(
        self,
        series_id: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> bool:
        """
        Check whether SQLite has enough observations for the requested window.

        For historical windows, this checks whether the stored data covers the
        requested start and end dates.

        For current or future-looking windows, it accepts a reasonable lag
        because FRED series can be monthly or quarterly.
        """

        repository = self._get_repository()

        observations = repository.get_observations(
            series_id=series_id,
            start_date=start_date,
            end_date=end_date,
        )

        if not observations:
            return False

        dates = [
            self._parse_date(row.get("date"))
            for row in observations
            if row.get("date")
        ]

        dates = [date for date in dates if date is not None]

        if not dates:
            return False

        first_available_date = min(dates)
        latest_available_date = max(dates)

        parsed_start_date = self._parse_date(start_date)
        parsed_end_date = self._parse_date(end_date)

        if parsed_start_date is not None and first_available_date > parsed_start_date:
            return False

        if parsed_end_date is None:
            return True

        today = datetime.utcnow()
        freshness_cutoff = today - timedelta(days=self.CURRENT_DATA_MAX_LAG_DAYS)

        if parsed_end_date >= freshness_cutoff:
            return latest_available_date >= freshness_cutoff

        return latest_available_date >= parsed_end_date

    def _build_indicator_response(
        self,
        series_id: str,
        indicator_name: str,
        observations: list[dict[str, Any]],
        start_date: Optional[str],
        end_date: Optional[str],
        source: str,
        errors: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Build the standardized output consumed by ResearcherNode.
        """

        sorted_observations = sorted(
            observations,
            key=lambda row: row.get("date") or "",
        )

        first_observation_date = None
        latest_observation_date = None

        if sorted_observations:
            first_observation_date = sorted_observations[0].get("date")
            latest_observation_date = sorted_observations[-1].get("date")

        return {
            "series_id": series_id,
            "indicator_name": indicator_name,
            "source": source,
            "start_date": start_date,
            "end_date": end_date,
            "observations": sorted_observations,
            "first_observation_date": first_observation_date,
            "latest_observation_date": latest_observation_date,
            "observation_count": len(sorted_observations),
            "errors": errors or [],
        }

    def _normalize_series_id(self, series_id: str) -> str:
        return str(series_id).upper().strip()

    def _normalize_date(self, value: Any) -> str:
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d")

        parsed_date = self._parse_date(str(value))

        if parsed_date is not None:
            return parsed_date.strftime("%Y-%m-%d")

        return str(value)

    def _parse_date(self, value: Optional[Any]) -> Optional[datetime]:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        text = str(value)

        for date_format in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                return datetime.strptime(text[: len(date_format)], date_format)
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None

        # Handles NaN values without importing pandas or numpy.
        if numeric_value != numeric_value:
            return None

        return numeric_value