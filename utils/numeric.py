"""Shared numeric operations with explicit missing-data behavior."""

import pandas as pd


def to_float_or_none(value: object) -> float | None:
    """Return a float for interpretable scalar numeric values."""

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def subtract_or_none(
    left: object,
    right: object,
) -> float | None:
    """Subtract two nullable scalar values."""

    left_value = to_float_or_none(left)
    right_value = to_float_or_none(right)
    if left_value is None or right_value is None:
        return None

    return left_value - right_value


def absolute_or_none(value: object) -> float | None:
    """Return the absolute value of a nullable scalar number."""

    numeric_value = to_float_or_none(value)
    if numeric_value is None:
        return None

    return abs(numeric_value)


def divide_or_none(
    numerator: object,
    denominator: object,
) -> float | None:
    """Divide two nullable scalar values and reject zero denominators."""

    numerator_value = to_float_or_none(numerator)
    denominator_value = to_float_or_none(denominator)
    if numerator_value is None or denominator_value is None:
        return None
    if denominator_value == 0:
        return None

    return numerator_value / denominator_value


def safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    """Divide aligned series and mask missing or zero-denominator rows."""

    valid_rows = (
        numerator.notna()
        & denominator.notna()
        & denominator.ne(0)
    )
    result = numerator.div(denominator)

    return result.where(valid_rows, pd.NA).astype("Float64")
