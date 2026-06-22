"""Shared numeric operations with explicit missing-data behavior."""

import pandas as pd


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
