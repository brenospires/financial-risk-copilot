"""Generic helpers for constructing wide time-series data frames."""

from typing import Any

import pandas as pd


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
