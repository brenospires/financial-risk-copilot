import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.tools.sec_tool import SECTool
from src.tools.sec_metrics import SECMetricExtractor
from src.database.sec_repository import SECRepository

def test_sec_pipeline():
    ticker = "AAPL"
    sec = SECTool(user_agent="financial-risk-copilot brenospires@gmail.com")

    repo = SECRepository()
    repo.create_tables()

    # Company metadata
    company = sec.get_company_by_ticker(ticker)
    cik = sec.get_cik_from_ticker(ticker)

    print("\nCompany:")
    print(company)

    print("\nCIK:")
    print(cik)

    repo.save_company(
        ticker=ticker,
        cik=cik,
        name=company["title"]
    )

    # Company facts and financial metrics
    facts = sec.get_company_facts(ticker)
    print("\nCompany facts keys:")
    print(facts.keys())

    extractor = SECMetricExtractor(facts)
    metrics = extractor.extract_all_metrics()

    print("\nExtracted financial metrics:")
    for metric_name, metric_data in metrics.items():
        print(metric_name, metric_data)

    repo.save_metrics(ticker, metrics)
    saved_metrics = repo.get_metrics(ticker)
    print("\nSaved metrics from SQLite:")

    for metric in saved_metrics:
        print(metric)

    # Recent 10-K filing metadata
    filings = sec.get_recent_filings(
        ticker=ticker,
        form_type="10-K",
        limit=1,
    )

    print("\nRecent 10-K filings:")

    for filing in filings:
        print(filing)

    # Download latest 10-K filing text
    filing = filings[0]

    filing_text = sec.download_filing(
        ticker=ticker,
        accession_number=filing["accession_number"],
        primary_document=filing["primary_document"],
    )

    print("\nFirst 2000 characters:")
    print(filing_text[:2000])

    # Save filing metadata and raw text
    repo.save_filing(
        ticker=ticker,
        filing=filing,
        filing_text=filing_text,
    )

    print("\nSEC pipeline completed successfully.")
    print("Data saved to:")
    print(repo.db_path)

if __name__ == "__main__":
    test_sec_pipeline()