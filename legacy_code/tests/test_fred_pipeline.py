import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.tools.fred_tool import FREDTool
from src.database.fred_repository import FREDRepository

def test_fred_pipeline():
    indicators = {
        "GDP": "Gross Domestic Product",
        "UNRATE": "Unemployment Rate",
    }

    fred = FREDTool()
    repository = FREDRepository()

    print("\nRetrieving FRED macro data...")

    macro_data = fred.get_macro_data(
        indicators=indicators,
        start_date="2020-01-01",
        end_date=None,
        refresh=True,
    )

    print("\nMacro data response keys:")
    print(macro_data.keys())

    print("\nErrors:")
    print(macro_data.get("errors"))

    assert "indicators" in macro_data
    assert isinstance(macro_data["indicators"], dict)
    assert len(macro_data["indicators"]) > 0

    for series_id, indicator_data in macro_data["indicators"].items():
        print(f"\nIndicator: {series_id}")
        print({
            "series_id": indicator_data.get("series_id"),
            "indicator_name": indicator_data.get("indicator_name"),
            "source": indicator_data.get("source"),
            "start_date": indicator_data.get("start_date"),
            "end_date": indicator_data.get("end_date"),
            "first_observation_date": indicator_data.get("first_observation_date"),
            "latest_observation_date": indicator_data.get("latest_observation_date"),
            "observation_count": indicator_data.get("observation_count"),
            "errors": indicator_data.get("errors"),
        })

        observations = indicator_data.get("observations", [])

        print(f"Number of observations returned: {len(observations)}")

        print("\nFirst 5 observations:")
        for row in observations[:5]:
            print(row)

        assert indicator_data["series_id"] == series_id
        assert indicator_data["indicator_name"] is not None
        assert isinstance(observations, list)
        assert len(observations) > 0
        assert indicator_data["observation_count"] == len(observations)

    print("\nReading saved observations from SQLite...")

    for series_id in indicators.keys():
        saved_observations = repository.get_observations(
            series_id=series_id,
            start_date="2020-01-01",
        )

        metadata = repository.get_indicator_metadata(series_id)
        coverage = repository.get_coverage(series_id)

        print(f"\nSaved metadata for {series_id}:")
        print(metadata)

        print(f"\nSaved coverage for {series_id}:")
        print(coverage)

        print(f"\nNumber of saved observations for {series_id}: {len(saved_observations)}")

        print("\nFirst 5 saved observations:")
        for row in saved_observations[:5]:
            print(row)

        assert metadata is not None
        assert metadata["series_id"] == series_id
        assert metadata["indicator_name"] == indicators[series_id]

        assert len(saved_observations) > 0
        assert coverage["observation_count"] > 0
        assert coverage["first_observation_date"] is not None
        assert coverage["latest_observation_date"] is not None

    print("\nTesting database-first retrieval...")

    macro_data_from_database = fred.get_macro_data(
        indicators=indicators,
        start_date="2020-01-01",
        end_date=None,
        refresh=False,
    )

    for series_id, indicator_data in macro_data_from_database["indicators"].items():
        print(f"\nDatabase-first source for {series_id}:")
        print(indicator_data.get("source"))

        assert indicator_data.get("source") == "database"
        assert indicator_data.get("observation_count") > 0

    print("\nFRED pipeline completed successfully.")
    print("Data saved to:")
    print(repository.db_path)

if __name__ == "__main__":
    test_fred_pipeline()