import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.tools.fred_tool import FREDTool

DEFAULT_INDICATORS = {
    "GDP": "Gross Domestic Product",
    "UNRATE": "Unemployment Rate",
    "CPIAUCSL": "Consumer Price Index",
    "FEDFUNDS": "Federal Funds Rate",
    "DGS10": "10-Year Treasury Rate",
    "T10Y2Y": "10Y-2Y Treasury Spread",
}

def retrieve_fred_indicators(
    indicators: dict[str, str] | None = None,
    start_date: str = "2018-01-01",
) -> dict:
    """
    Retrieve macroeconomic indicators from FRED.

    Returns a dictionary where each key is the FRED series ID.
    """

    fred = FREDTool()
    indicators = indicators or DEFAULT_INDICATORS
    results = {}

    for series_id, description in indicators.items():
        df = fred.get_series(
            series_id=series_id,
            start_date=start_date,
        )

        results[series_id] = {
            "description": description,
            "data": df,
        }

    return results