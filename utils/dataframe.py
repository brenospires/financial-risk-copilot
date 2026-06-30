"""Shared DataFrame operations with explicit missing-data behavior."""

import pandas as pd


def get_single_row_value(
    data: pd.DataFrame,
    column_name: str,
) -> object | None:
    """Return one column value from a one-row DataFrame."""

    if column_name not in data.columns:
        return None

    return data[column_name].iloc[0]


def with_end_date_column(data: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with end_date available as a column."""

    if "end_date" in data.columns:
        return data.copy()

    if "end_date" not in data.index.names:
        raise ValueError("Financial statements require an end_date column")

    return data.reset_index()
