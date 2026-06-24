"""Generic helpers for constructing wide time-series data frames."""

from typing import Any, Literal

import numpy as np
import pandas as pd

from config.trend_analysis import (
    MINIMUM_TREND_PERIODS,
    TREND_CLIPPING_RANGE,
)


ComparisonPeriod = Literal["dod", "mom", "qoq", "yoy"]

COMPARISON_OFFSETS: dict[ComparisonPeriod, pd.DateOffset] = {
    "dod": pd.DateOffset(days=1),
    "mom": pd.DateOffset(months=1),
    "qoq": pd.DateOffset(months=3),
    "yoy": pd.DateOffset(years=1),
}


def pivot_time_series(
    records: list[dict[str, Any]],
    *,
    values: str,
    columns: str,
    timestamp: str,
    group_columns: tuple[str, ...] = (),
    expected_columns: tuple[str, ...] = (),
) -> pd.DataFrame:
    """
    Pivot long-form time-series records into a grouped wide data frame.

    ``group_columns`` and ``timestamp`` form the output index, ``columns``
    supplies the wide column names, and ``values`` supplies cell values.
    Expected columns that are absent from the records are added with ``pd.NA``.
    Duplicate canonical observations are rejected instead of aggregated.
    """

    if not records:
        raise ValueError("Time-series records are required")

    if timestamp in group_columns:
        raise ValueError("timestamp cannot also be a group column")

    if len(group_columns) != len(set(group_columns)):
        raise ValueError("group_columns cannot contain duplicates")

    frame = pd.DataFrame.from_records(records)
    index_columns = (*group_columns, timestamp)
    required_columns = {*index_columns, columns, values}
    missing_columns = sorted(required_columns - set(frame.columns))

    if missing_columns:
        missing_names = ", ".join(missing_columns)
        raise ValueError(f"Missing time-series columns: {missing_names}")

    frame[timestamp] = pd.to_datetime(frame[timestamp], errors="raise")
    identity_columns = [*index_columns, columns]
    duplicate_rows = frame.duplicated(
        subset=identity_columns,
        keep=False,
    )

    if duplicate_rows.any():
        raise ValueError("Duplicate canonical time-series observations")

    result = frame.pivot(
        index=list(index_columns),
        columns=columns,
        values=values,
    )
    additional_columns = [
        column
        for column in result.columns
        if column not in expected_columns
    ]
    ordered_columns = [*expected_columns, *additional_columns]
    result = result.reindex(columns=ordered_columns)
    result = result.convert_dtypes()
    result.columns.name = None

    return result.sort_index()


def carry_forward_time_series(
    series: pd.Series,
    target_index: pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    """Carry observations forward and retain their original timestamps."""

    ordered = _prepare_datetime_series(series)
    index = ordered.index if target_index is None else target_index.sort_values()
    aligned = ordered.reindex(index)
    source_timestamp = pd.Series(
        pd.NaT,
        index=index,
        dtype="datetime64[ns]",
    )
    observed = aligned.notna()
    source_timestamp.loc[observed] = index[observed]

    return pd.DataFrame(
        {
            "value": aligned.ffill(),
            "source_timestamp": source_timestamp.ffill(),
            "is_carried_forward": aligned.isna() & source_timestamp.ffill().notna(),
        },
        index=index,
    )


def regularize_time_series(
    series: pd.Series,
    *,
    months_per_period: int,
    tolerance_days: int,
) -> pd.DataFrame:
    """Align observations to an anchored periodic grid and carry gaps forward."""

    if months_per_period <= 0:
        raise ValueError("months_per_period must be positive")

    if tolerance_days < 0:
        raise ValueError("tolerance_days cannot be negative")

    ordered = _prepare_datetime_series(series)
    if ordered.empty:
        return pd.DataFrame(
            columns=(
                "value",
                "source_timestamp",
                "is_carried_forward",
                "is_observed",
            )
        )

    expected_index = _build_periodic_index(
        ordered.index,
        months_per_period=months_per_period,
        tolerance_days=tolerance_days,
    )
    aligned = pd.Series(pd.NA, index=expected_index, dtype="Float64")
    observed_sources = pd.Series(
        pd.NaT,
        index=expected_index,
        dtype="datetime64[ns]",
    )

    for timestamp, value in ordered.items():
        distances = abs(expected_index - timestamp)
        position = int(np.argmin(distances))
        distance_days = distances[position].total_seconds() / 86_400

        if distance_days > tolerance_days:
            raise ValueError(
                f"Observation {timestamp.date()} cannot be aligned to "
                "the expected reporting grid"
            )

        if pd.notna(value):
            if pd.notna(aligned.iloc[position]):
                raise ValueError("Multiple observations map to one reporting period")
            aligned.iloc[position] = float(value)
            observed_sources.iloc[position] = timestamp

    carried = carry_forward_time_series(aligned)
    carried["source_timestamp"] = observed_sources.ffill()
    carried["is_observed"] = aligned.notna()

    return carried


def calculate_period_change(
    series: pd.Series,
    period: ComparisonPeriod,
    aligned_periods: bool = False,
) -> pd.DataFrame:
    """Calculate calendar-aligned absolute and relative period changes."""

    ordered = _prepare_datetime_series(series)
    previous = (
        ordered.shift(1)
        if aligned_periods
        else ordered.shift(freq=COMPARISON_OFFSETS[period]).reindex(ordered.index)
    )
    absolute_change = ordered - previous
    valid_baseline = previous.notna() & previous.ne(0)
    relative_change = absolute_change.div(previous.abs()).where(valid_baseline)
    sign_crossing = (
        ordered.notna()
        & previous.notna()
        & ordered.ne(0)
        & previous.ne(0)
        & np.sign(ordered).ne(np.sign(previous))
    )

    return pd.DataFrame(
        {
            "current_value": ordered,
            "previous_value": previous,
            "absolute_change": absolute_change,
            "relative_change": relative_change,
            "sign_crossing": sign_crossing,
        },
        index=ordered.index,
    )


def exponential_moving_average(series: pd.Series, alpha: float) -> pd.Series:
    """Return the exponentially weighted moving average of observed values."""

    if not 0 < alpha <= 1:
        raise ValueError("EMA alpha must be greater than 0 and at most 1")

    clean_series = series.dropna()
    if clean_series.empty:
        return clean_series

    return clean_series.ewm(alpha=alpha, adjust=False).mean()


def calculate_exponential_trend(
    series: pd.Series,
    alpha: float,
    period: ComparisonPeriod,
) -> float | None:
    """Return the normalized latest periodic movement of smoothed levels."""

    clean_series = series.dropna()
    if len(clean_series) < MINIMUM_TREND_PERIODS:
        return None

    ema = exponential_moving_average(clean_series, alpha=alpha)
    scale = _robust_magnitude(clean_series)
    if scale == 0:
        return 0.0

    changes = calculate_period_change(
        ema,
        period,
        aligned_periods=True,
    )
    latest_change = changes["absolute_change"].iloc[-1]
    if pd.isna(latest_change):
        return None

    normalized_trend = float(latest_change) / scale
    return _clip_trend(normalized_trend)


def calculate_linear_trend(series: pd.Series) -> float | None:
    """Return a timestamp-aware normalized slope for a long time series."""

    clean_series = _prepare_datetime_series(series).dropna()
    if len(clean_series) < MINIMUM_TREND_PERIODS:
        return None

    elapsed_days = (
        clean_series.index - clean_series.index[0]
    ).total_seconds() / 86_400
    if elapsed_days[-1] == 0:
        return None

    interval_days = float(np.median(np.diff(elapsed_days)))
    slope_per_day = np.polyfit(elapsed_days, clean_series.to_numpy(dtype=float), 1)[0]
    scale = _robust_magnitude(clean_series)
    if scale == 0:
        return 0.0

    normalized_slope = slope_per_day * interval_days / scale
    return _clip_trend(normalized_slope)


def calculate_cagr(series: pd.Series) -> float | None:
    """Return CAGR when sufficient positive observations span at least one year."""

    clean_series = _prepare_datetime_series(series).dropna()
    if len(clean_series) < MINIMUM_TREND_PERIODS:
        return None

    first_value = float(clean_series.iloc[0])
    latest_value = float(clean_series.iloc[-1])
    elapsed_years = (
        clean_series.index[-1] - clean_series.index[0]
    ).total_seconds() / (86_400 * 365.2425)

    if first_value <= 0 or latest_value <= 0 or elapsed_years < 1:
        return None

    return float((latest_value / first_value) ** (1 / elapsed_years) - 1)


def _prepare_datetime_series(series: pd.Series) -> pd.Series:
    """Validate, normalize, and sort a datetime-indexed series."""

    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("Time-series calculations require a DatetimeIndex")

    if series.index.has_duplicates:
        raise ValueError("Time-series timestamps cannot contain duplicates")

    result = series.copy()
    result.index = pd.to_datetime(result.index, errors="raise", utc=True).tz_localize(None)
    return result.sort_index()


def _build_periodic_index(
    observed_index: pd.DatetimeIndex,
    *,
    months_per_period: int,
    tolerance_days: int,
) -> pd.DatetimeIndex:
    """Build an expected grid anchored to the latest reporting timestamp."""

    earliest = observed_index.min()
    current = observed_index.max()
    lower_bound = earliest - pd.Timedelta(days=tolerance_days)
    timestamps = [current]

    while True:
        candidate = current - pd.DateOffset(months=months_per_period)
        if candidate < lower_bound:
            break
        timestamps.append(candidate)
        current = candidate

    return pd.DatetimeIndex(reversed(timestamps))


def _robust_magnitude(series: pd.Series) -> float:
    """Return a stable absolute scale for normalized trend calculations."""

    magnitude = float(series.astype(float).abs().median())
    if np.isfinite(magnitude):
        return magnitude

    return 0.0


def _clip_trend(value: float) -> float:
    """Clip a normalized trajectory to its configured interval."""

    return float(
        np.clip(
            value,
            TREND_CLIPPING_RANGE[0],
            TREND_CLIPPING_RANGE[1],
        )
    )
