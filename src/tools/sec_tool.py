import time
from typing import Any, Dict, Optional

import requests


class SECTool:
    """
    Simple SEC EDGAR API client.

    This class retrieves:
    - ticker to CIK mapping
    - company submissions
    - company XBRL facts

    SEC requires a descriptive User-Agent header.
    Example:
        "financial-risk-copilot brenospires@gmail.com"
    """

    BASE_SEC_URL = "https://www.sec.gov"
    BASE_DATA_URL = "https://data.sec.gov"

    def __init__(
        self,
        user_agent: str,
        request_delay: float = 0.2,
        timeout: int = 30,
    ):
        if not user_agent:
            raise ValueError("user_agent is required for SEC API requests.")

        self.headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
        }
        
        self.request_delay = request_delay
        self.timeout = timeout
        self._ticker_cache: Optional[Dict[str, Dict[str, Any]]] = None

    def _get_json(self, url: str) -> Dict[str, Any]:
        """
        Internal helper to call SEC endpoints safely.
        """
        time.sleep(self.request_delay)

        response = requests.get(
            url,
            headers=self.headers,
            timeout=self.timeout,
        )

        response.raise_for_status()
        return response.json()

    def get_company_tickers(self) -> Dict[str, Dict[str, Any]]:
        """
        Download and cache the SEC ticker-to-CIK mapping.
        """
        if self._ticker_cache is None:
            url = f"{self.BASE_SEC_URL}/files/company_tickers.json"
            self._ticker_cache = self._get_json(url)

        return self._ticker_cache

    def get_company_by_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Return SEC company metadata for a ticker.

        Example output:
        {
            "cik_str": 320193,
            "ticker": "AAPL",
            "title": "Apple Inc."
        }
        """
        ticker = ticker.upper().strip()
        companies = self.get_company_tickers()

        for company in companies.values():
            if company["ticker"].upper() == ticker:
                return company

        raise ValueError(f"Ticker not found in SEC mapping: {ticker}")

    def get_cik_from_ticker(self, ticker: str) -> str:
        """
        Return a zero-padded 10-digit CIK string.
        """
        company = self.get_company_by_ticker(ticker)
        return str(company["cik_str"]).zfill(10)

    def get_company_submissions(self, ticker: str) -> Dict[str, Any]:
        """
        Retrieve recent SEC filing metadata for a company.
        """
        cik = self.get_cik_from_ticker(ticker)
        url = f"{self.BASE_DATA_URL}/submissions/CIK{cik}.json"

        return self._get_json(url)

    def get_company_facts(self, ticker: str) -> Dict[str, Any]:
        """
        Retrieve XBRL company facts for a company.
        """
        cik = self.get_cik_from_ticker(ticker)
        url = f"{self.BASE_DATA_URL}/api/xbrl/companyfacts/CIK{cik}.json"

        return self._get_json(url)

    def get_recent_filings(
        self,
        ticker: str,
        form_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Return recent filings as a list of dictionaries.

        If form_type is provided, filter by form type.
        Example:
            form_type="10-K"
            form_type="10-Q"
        """
        submissions = self.get_company_submissions(ticker)
        recent = submissions["filings"]["recent"]

        filings = []
        total_filings = len(recent["accessionNumber"])

        for i in range(total_filings):
            filing = {
                "accession_number": recent["accessionNumber"][i],
                "filing_date": recent["filingDate"][i],
                "report_date": recent["reportDate"][i],
                "form": recent["form"][i],
                "primary_document": recent["primaryDocument"][i],
                "primary_doc_description": recent["primaryDocDescription"][i],
            }

            if form_type is None or filing["form"] == form_type:
                filings.append(filing)

            if len(filings) >= limit:
                break

        return filings
    
    def get_filing_url(
        self,
        ticker: str,
        accession_number: str,
        primary_document: str,
    ) -> str:
        """
        Build the SEC filing URL.
        """

        cik = self.get_cik_from_ticker(ticker)

        accession_no_dash = accession_number.replace("-", "")

        return (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{accession_no_dash}/{primary_document}"
        )
    
    def download_filing(
        self,
        ticker: str,
        accession_number: str,
        primary_document: str,
    ) -> str:
        """
        Download filing document.
        """

        url = self.get_filing_url(
            ticker,
            accession_number,
            primary_document,
        )

        response = requests.get(
            url,
            headers=self.headers,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.text