
import math
from typing import Any, Optional
from datetime import date, datetime, timezone

class MetricsUtils:
    """
    Stateless utility mixin for metric calculation classes.

    Metric classes can inherit from this class to access shared helper methods
    through self._method_name(...).

    Example:
        class FinancialStatementMetrics(MetricsUtils):
        class MacroMetrics(MetricsUtils):
        class MarketMetrics(MetricsUtils):
        class BondMetrics(MetricsUtils):

    Responsibilities:
    - safe numeric conversion
    - safe division
    - date parsing and normalization
    - date filtering and sorting
    - period-over-period calculations
    - first-to-last change calculations
    - frequency detection
    - simple linear trend calculation
    - trend classification
    - generic latest-row and latest-value selection
    - missing/available key diagnostics

    This class must not contain business-specific financial formulas.
    """

    DATE_FORMATS: tuple[str, ...] = (
        "%Y-%m-%d",
        "%Y-%m",
        "%Y",
    )

    def _safe_float(
        self,
        value: Any,
    ) -> Optional[float]:
        """
        Convert a value to float when possible.

        Purpose:
        Makes metric calculations robust to missing values, strings,
        comma-formatted numbers, invalid values, NaN, and infinite values.
        """

        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            numeric_value = float(value)

            if not math.isfinite(numeric_value):
                return None

            return numeric_value

        text = str(value).strip()

        if not text:
            return None

        # Supports simple accounting-style negative values: "(123.45)".
        is_parenthesized_negative = (
            text.startswith("(")
            and text.endswith(")")
        )

        if is_parenthesized_negative:
            text = text[1:-1].strip()

        text = text.replace(",", "")

        try:
            numeric_value = float(text)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(numeric_value):
            return None

        if is_parenthesized_negative:
            numeric_value = -numeric_value

        return numeric_value

    def _safe_int(
        self,
        value: Any,
    ) -> Optional[int]:
        """
        Convert a value to int when possible.

        Purpose:
        Normalizes fiscal year values and other integer-like provider fields.
        """

        numeric_value = self._safe_float(value)

        if numeric_value is None:
            return None

        return int(numeric_value)

    def _safe_divide(
        self,
        numerator: Any,
        denominator: Any,
    ) -> Optional[float]:
        """
        Safely divide two numeric values.

        Purpose:
        Prevents missing values and zero denominators from breaking metric
        calculations.
        """

        numerator_value = self._safe_float(numerator)
        denominator_value = self._safe_float(denominator)

        if numerator_value is None or denominator_value is None:
            return None

        if denominator_value == 0:
            return None

        return numerator_value / denominator_value

    def _average_available(
        self,
        values: list[Any],
    ) -> Optional[float]:
        """
        Calculate the average of available numeric values.

        Purpose:
        Supports fallback logic when some values are missing but others are
        available.
        """

        available_values = [
            self._safe_float(value)
            for value in values
        ]

        available_values = [
            value
            for value in available_values
            if value is not None
        ]

        if not available_values:
            return None

        return sum(available_values) / len(available_values)

    def _parse_date(
        self,
        value: Any,
    ) -> Optional[datetime]:
        """
        Parse a date-like value into a naive datetime object.

        Purpose:
        Supports filtering, sorting, frequency detection, and period selection.
        """

        if value is None:
            return None

        if isinstance(value, datetime):
            parsed_date = value
        elif isinstance(value, date):
            parsed_date = datetime.combine(value, datetime.min.time())
        else:
            text = str(value).strip()

            if not text:
                return None

            parsed_date = None

            for date_format in self.DATE_FORMATS:
                try:
                    parsed_date = datetime.strptime(
                        text[: len(date_format)],
                        date_format,
                    )
                    break
                except ValueError:
                    continue

            if parsed_date is None:
                try:
                    parsed_date = datetime.fromisoformat(
                        text.replace("Z", "+00:00")
                    )
                except ValueError:
                    return None

        if parsed_date.tzinfo is not None:
            parsed_date = (
                parsed_date
                .astimezone(timezone.utc)
                .replace(tzinfo=None)
            )

        return parsed_date

    def _normalize_date(
        self,
        value: Any,
    ) -> Optional[str]:
        """
        Normalize a date-like value to YYYY-MM-DD format.

        Purpose:
        Creates stable date values for downstream output.
        """

        parsed_date = self._parse_date(value)

        if parsed_date is None:
            return None

        return parsed_date.strftime("%Y-%m-%d")

    def _filter_by_date(
        self,
        rows: list[dict[str, Any]],
        date_key: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
    ) -> list[dict[str, Any]]:
        """
        Filter rows by a date window.

        Purpose:
        Supports provider-agnostic date filtering for company, macro, market,
        and bond data.
        """

        parsed_start_date = self._parse_date(start_date)
        parsed_end_date = self._parse_date(end_date)

        filtered_rows: list[dict[str, Any]] = []

        for row in rows:
            row_date = self._parse_date(row.get(date_key))

            if row_date is None:
                continue

            if parsed_start_date is not None and row_date < parsed_start_date:
                continue

            if parsed_end_date is not None and row_date > parsed_end_date:
                continue

            filtered_rows.append(row)

        return filtered_rows

    def _sort_by_date(
        self,
        rows: list[dict[str, Any]],
        date_key: str,
        reverse: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Sort rows chronologically by a date field.

        Purpose:
        Ensures period-over-period and trend calculations use ordered data.
        """

        valid_rows = [
            row
            for row in rows
            if self._parse_date(row.get(date_key)) is not None
        ]

        return sorted(
            valid_rows,
            key=lambda row: self._parse_date(row.get(date_key)),
            reverse=reverse,
        )

    def _calculate_absolute_change(
        self,
        previous_value: Any,
        current_value: Any,
    ) -> Optional[float]:
        """
        Calculate absolute change from previous value to current value.

        Purpose:
        Useful for rates, spreads, and metrics where percentage change is less
        interpretable than level change.
        """

        previous_numeric = self._safe_float(previous_value)
        current_numeric = self._safe_float(current_value)

        if previous_numeric is None or current_numeric is None:
            return None

        return current_numeric - previous_numeric

    def _calculate_period_change(
        self,
        previous_value: Any,
        current_value: Any,
    ) -> Optional[float]:
        """
        Calculate percentage change from previous value to current value.

        Purpose:
        Supports period-over-period, first-to-last, YoY, QoQ, MoM, and other
        generic change calculations.

        Formula:
            (current - previous) / abs(previous)
        """

        previous_numeric = self._safe_float(previous_value)
        current_numeric = self._safe_float(current_value)

        if previous_numeric is None or current_numeric is None:
            return None

        if previous_numeric == 0:
            return None

        return (current_numeric - previous_numeric) / abs(previous_numeric)

    def _detect_period_frequency(
        self,
        rows: list[dict[str, Any]],
        date_key: str = "date",
    ) -> str:
        """
        Infer the approximate frequency of a dated time series.

        Possible outputs:
        - daily
        - weekly
        - monthly
        - quarterly
        - annual
        - irregular
        - unavailable
        """

        ordered_rows = self._sort_by_date(
            rows=rows,
            date_key=date_key,
        )

        dates = [
            self._parse_date(row.get(date_key))
            for row in ordered_rows
        ]

        dates = [
            row_date
            for row_date in dates
            if row_date is not None
        ]

        if len(dates) < 2:
            return "unavailable"

        day_differences = [
            (dates[index] - dates[index - 1]).days
            for index in range(1, len(dates))
        ]

        if not day_differences:
            return "unavailable"

        median_gap = sorted(day_differences)[len(day_differences) // 2]

        if median_gap <= 2:
            return "daily"

        if 5 <= median_gap <= 9:
            return "weekly"

        if 25 <= median_gap <= 35:
            return "monthly"

        if 80 <= median_gap <= 100:
            return "quarterly"

        if 350 <= median_gap <= 380:
            return "annual"

        return "irregular"

    def _calculate_period_over_period_changes(
        self,
        rows: list[dict[str, Any]],
        value_key: str = "value",
        date_key: str = "date",
    ) -> list[dict[str, Any]]:
        """
        Calculate period-over-period changes for an ordered time series.

        Purpose:
        Provides generic PoP change logic for financial statement, macro,
        market, and bond-related data.
        """

        ordered_rows = self._sort_by_date(
            rows=rows,
            date_key=date_key,
        )

        frequency = self._detect_period_frequency(
            rows=ordered_rows,
            date_key=date_key,
        )

        changes: list[dict[str, Any]] = []

        for index in range(1, len(ordered_rows)):
            previous_row = ordered_rows[index - 1]
            current_row = ordered_rows[index]

            previous_value = self._safe_float(previous_row.get(value_key))
            current_value = self._safe_float(current_row.get(value_key))

            changes.append(
                {
                    "date": current_row.get(date_key),
                    "previous_date": previous_row.get(date_key),
                    "value": current_value,
                    "previous_value": previous_value,
                    "absolute_change": self._calculate_absolute_change(
                        previous_value=previous_value,
                        current_value=current_value,
                    ),
                    "percentage_change": self._calculate_period_change(
                        previous_value=previous_value,
                        current_value=current_value,
                    ),
                    "frequency": frequency,
                }
            )

        return changes

    def _calculate_first_to_last_change(
        self,
        rows: list[dict[str, Any]],
        value_key: str = "value",
        date_key: str = "date",
    ) -> dict[str, Any]:
        """
        Calculate change between the first and latest available observations.

        Purpose:
        Provides a simple period summary when detailed period-over-period
        comparison is unnecessary.
        """

        ordered_rows = self._sort_by_date(
            rows=rows,
            date_key=date_key,
        )

        if len(ordered_rows) < 2:
            return {
                "first_date": None,
                "latest_date": None,
                "first_value": None,
                "latest_value": None,
                "absolute_change": None,
                "percentage_change": None,
            }

        first_row = ordered_rows[0]
        latest_row = ordered_rows[-1]

        first_value = self._safe_float(first_row.get(value_key))
        latest_value = self._safe_float(latest_row.get(value_key))

        return {
            "first_date": first_row.get(date_key),
            "latest_date": latest_row.get(date_key),
            "first_value": first_value,
            "latest_value": latest_value,
            "absolute_change": self._calculate_absolute_change(
                previous_value=first_value,
                current_value=latest_value,
            ),
            "percentage_change": self._calculate_period_change(
                previous_value=first_value,
                current_value=latest_value,
            ),
        }

    def _calculate_linear_trend(
        self,
        rows: list[dict[str, Any]],
        value_key: str = "value",
        date_key: str = "date",
        tolerance: float = 0.0,
    ) -> dict[str, Any]:
        """
        Estimate a simple linear trend over ordered observations.

        Purpose:
        Produces slope and direction without requiring pandas, numpy, or a
        complex statistical model.
        """

        ordered_rows = self._sort_by_date(
            rows=rows,
            date_key=date_key,
        )

        observations: list[dict[str, Any]] = []

        for row in ordered_rows:
            parsed_date = self._parse_date(row.get(date_key))
            value = self._safe_float(row.get(value_key))

            if parsed_date is None or value is None:
                continue

            observations.append(
                {
                    "date": parsed_date,
                    "value": value,
                }
            )

        if len(observations) < 2:
            return {
                "slope": None,
                "direction": "unavailable",
                "observation_count": len(observations),
            }

        first_date = observations[0]["date"]

        x_values = [
            (observation["date"] - first_date).days
            for observation in observations
        ]

        y_values = [
            observation["value"]
            for observation in observations
        ]

        x_mean = sum(x_values) / len(x_values)
        y_mean = sum(y_values) / len(y_values)

        numerator = sum(
            (x_value - x_mean) * (y_value - y_mean)
            for x_value, y_value in zip(x_values, y_values)
        )

        denominator = sum(
            (x_value - x_mean) ** 2
            for x_value in x_values
        )

        slope = None

        if denominator != 0:
            slope = numerator / denominator

        return {
            "slope": slope,
            "direction": self._classify_trend_direction(
                slope=slope,
                tolerance=tolerance,
            ),
            "observation_count": len(observations),
        }

    def _classify_trend_direction(
        self,
        slope: Any,
        tolerance: float = 0.0,
    ) -> str:
        """
        Classify a numeric trend slope.

        Possible outputs:
        - positive
        - negative
        - stable
        - unavailable
        """

        numeric_slope = self._safe_float(slope)

        if numeric_slope is None:
            return "unavailable"

        if abs(numeric_slope) <= tolerance:
            return "stable"

        if numeric_slope > 0:
            return "positive"

        return "negative"

    def _latest_available_row(
        self,
        rows: list[dict[str, Any]],
        date_key: str = "date",
        as_of_date: Optional[Any] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Select the latest available row up to as_of_date.

        Purpose:
        Supports snapshot calculations across financial statement, macro,
        market, and bond-related data.
        """

        filtered_rows = self._filter_by_date(
            rows=rows,
            date_key=date_key,
            end_date=as_of_date,
        )

        ordered_rows = self._sort_by_date(
            rows=filtered_rows,
            date_key=date_key,
        )

        if not ordered_rows:
            return None

        return ordered_rows[-1]

    def _latest_values_by_key(
        self,
        rows: list[dict[str, Any]],
        group_key: str,
        value_key: str = "value",
        date_key: str = "date",
        as_of_date: Optional[Any] = None,
    ) -> dict[str, Optional[float]]:
        """
        Select the latest numeric value for each group.

        Purpose:
        Lets metric classes build latest metric maps without reimplementing
        generic grouping, sorting, date filtering, or numeric conversion.

        Example:
            _latest_values_by_key(
                rows=financials,
                group_key="metric_name",
                value_key="value",
                date_key="end_date",
                as_of_date="2024-12-31",
            )
        """

        filtered_rows = self._filter_by_date(
            rows=rows,
            date_key=date_key,
            end_date=as_of_date,
        )

        ordered_rows = self._sort_by_date(
            rows=filtered_rows,
            date_key=date_key,
        )

        latest_values: dict[str, Optional[float]] = {}

        for row in ordered_rows:
            key = row.get(group_key)

            if key is None:
                continue

            latest_values[str(key)] = self._safe_float(row.get(value_key))

        return latest_values

    def _calculate_available_keys(
        self,
        values: dict[str, Any],
    ) -> list[str]:
        """
        Return keys whose values are available.

        Purpose:
        Supports diagnostics and missing-data reporting.
        """

        available_keys: list[str] = []

        for key, value in values.items():
            if value is not None:
                available_keys.append(key)

        return available_keys

    def _calculate_missing_keys(
        self,
        values: dict[str, Any],
        required_keys: list[str],
    ) -> list[str]:
        """
        Return required keys that are missing or unavailable.

        Purpose:
        Supports fallback logic and transparent diagnostics.
        """

        missing_keys: list[str] = []

        for key in required_keys:
            if values.get(key) is None:
                missing_keys.append(key)

        return missing_keys