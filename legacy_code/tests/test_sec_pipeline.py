import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.tools.sec_tool import SECTool
from src.database.sec_repository import SECRepository

def test_sec_pipeline():
    ticker = "AAPL"

    sec = SECTool()

    repo = SECRepository()
    repo.create_tables()

    company_data = sec.get_company_data(
        ticker=ticker,
        start_date="2020-01-01",
        end_date="2024-12-31",
        refresh=True,
    )

    print("\nCompany data response keys:")
    print(company_data.keys())

    print("\nCompany metadata:")
    print({
        "ticker": company_data.get("ticker"),
        "company_name": company_data.get("company_name"),
        "cik": company_data.get("cik"),
        "sic": company_data.get("sic"),
        "sic_description": company_data.get("sic_description"),
        "source": company_data.get("source"),
    })

    print("\nYears available:")
    print(company_data.get("years_available"))

    print("\nPeriods available:")
    print(company_data.get("periods_available"))

    print("\nMissing years:")
    print(company_data.get("missing_years"))

    print("\nMissing core metrics:")
    print(company_data.get("missing_core_metrics"))

    print("\nErrors:")
    print(company_data.get("errors"))

    financials = company_data.get("financials", [])

    print(f"\nNumber of normalized SEC metric rows: {len(financials)}")

    print("\nFirst 20 normalized metric rows:")
    for row in financials[:20]:
        print(row)

    saved_company = repo.get_company(ticker)

    print("\nSaved company from SQLite:")
    print(saved_company)

    saved_metrics = repo.get_metrics(
        ticker=ticker,
        start_date="2020-01-01",
        end_date="2024-12-31",
    )

    print(f"\nNumber of saved metric rows from SQLite: {len(saved_metrics)}")

    print("\nFirst 20 saved metric rows from SQLite:")
    for row in saved_metrics[:20]:
        print(row)

    assert company_data["ticker"] == ticker
    assert company_data["company_name"] is not None
    assert company_data["cik"] is not None
    assert "financials" in company_data
    assert isinstance(company_data["financials"], list)

    assert saved_company is not None
    assert saved_company["ticker"] == ticker
    assert saved_company["company_name"] is not None

    assert len(saved_metrics) > 0

    print("\nSEC pipeline completed successfully.")
    print("Data saved to:")
    print(repo.db_path)


if __name__ == "__main__":
    test_sec_pipeline()