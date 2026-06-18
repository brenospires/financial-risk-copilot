import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.database.fred_repository import FREDRepository

def save_fred_indicators(fred_data: dict) -> None:
    """
    Persist FRED indicators into SQLite.
    """

    repository = FREDRepository()
    repository.create_tables()

    for series_id, content in fred_data.items():
        repository.save_indicator(
            series_id=series_id,
            indicator_name=content["description"],
            df=content["data"],
        )