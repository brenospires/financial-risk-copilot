import os
import pandas as pd
from pathlib import Path
from fredapi import Fred
from dotenv import load_dotenv

class FREDTool:

    def __init__(self):
        project_root = Path(__file__).resolve().parents[2]
        env_path = project_root / ".env"

        load_dotenv(dotenv_path=env_path)
        api_key = os.getenv("FRED_API_KEY")

        if not api_key:
            raise ValueError("FRED_API_KEY not found. Create a .env file in the project root.")

        self.fred = Fred(api_key=api_key)

    def get_series(
        self,
        series_id: str,
        start_date: str | None = None,
    ) -> pd.DataFrame:
        series = self.fred.get_series(
            series_id,
            observation_start=start_date,
        )

        return pd.DataFrame({
            "date": series.index,
            "value": series.values,
        })