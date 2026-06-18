import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.tools.fred_indicators import retrieve_fred_indicators
from src.tools.fred_persistence import save_fred_indicators
from src.database.fred_repository import FREDRepository


def main():
    print("Retrieving FRED indicators...")

    fred_data = retrieve_fred_indicators(
        start_date="2020-01-01"
    )

    print("Saving FRED indicators to SQLite...")

    save_fred_indicators(fred_data)

    print("Reading GDP from SQLite...")

    repository = FREDRepository()
    gdp_data = repository.get_indicator("GDP")

    print(f"Rows retrieved for GDP: {len(gdp_data)}")

    if not gdp_data:
        raise ValueError("No GDP data found in SQLite.")

    print("First 5 GDP rows:")
    for row in gdp_data[:5]:
        print(row)

    print("\nFRED pipeline test completed successfully.")


if __name__ == "__main__":
    main()