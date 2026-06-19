
import time
import requests
from datetime import datetime
from typing import Any, Dict, List, Optional

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from config.settings import SEC_USER_AGENT
from src.database.sec_repository import SECRepository

class SECTool:
    """
    SEC provider facade.

    This class owns the SEC data workflow:
    - SEC API calls
    - database-first retrieval
    - API fallback
    - SEC metric normalization
    - persistence through SECRepository
    - normalized output for ResearcherNode

    This class does not calculate ratios, trends, comparisons, or risk scores.
    Those responsibilities belong to the financial metrics layer.
    """

    BASE_SEC_URL = "https://www.sec.gov"
    BASE_DATA_URL = "https://data.sec.gov"

    METRIC_CANDIDATES: dict[str, list[str]] = {
        # Income Statement
        "revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],
        "net_income": [
            "NetIncomeLoss",
        ],
        "operating_income": [
            "OperatingIncomeLoss",
        ],
        "gross_profit": [
            "GrossProfit",
        ],
        "interest_expense": [
            "InterestExpenseNonOperating",
            "InterestExpense",
        ],

        # Balance Sheet
        "assets": [
            "Assets",
        ],
        "current_assets": [
            "AssetsCurrent",
        ],
        "liabilities": [
            "Liabilities",
        ],
        "current_liabilities": [
            "LiabilitiesCurrent",
        ],
        "equity": [
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ],
        "cash": [
            "CashAndCashEquivalentsAtCarryingValue",
            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        ],
        "inventory": [
            "InventoryNet",
        ],
        "accounts_receivable": [
            "AccountsReceivableNetCurrent",
        ],
        "accounts_payable": [
            "AccountsPayableCurrent",
        ],
        "retained_earnings": [
            "RetainedEarningsAccumulatedDeficit",
        ],
        "working_capital": [
            "WorkingCapital",
        ],

        # Debt
        # For now, debt is approximated using the best available SEC tag.
        # Later, we can improve this by explicitly summing short-term and long-term debt.
        "debt": [
            "LongTermDebtAndFinanceLeaseObligations",
            "LongTermDebt",
            "LongTermDebtCurrent",
            "ShortTermBorrowings",
            "ShortTermDebt",
            "LongTermDebtAndFinanceLeaseObligationsCurrent",
            "ShortTermBorrowingsAndFinanceLeaseObligations",
        ],
        "long_term_debt": [
            "LongTermDebtAndFinanceLeaseObligations",
            "LongTermDebt",
        ],

        # Cash Flow Statement
        "operating_cash_flow": [
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        ],
        "capital_expenditures": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
        ],
        "free_cash_flow": [
            "FreeCashFlow",
        ],

        # Distress / risk score inputs
        "ebit": [
            "OperatingIncomeLoss",
        ],

        # Shares
        "shares_outstanding": [
            "CommonStockSharesOutstanding",
            "EntityCommonStockSharesOutstanding",
        ],
    }

    CORE_METRICS: tuple[str, ...] = (
        "assets",
        "liabilities",
        "equity",
        "revenue",
        "net_income",
        "current_assets",
        "current_liabilities",
        "cash",
        "debt",
        "operating_income",
        "interest_expense",
        "operating_cash_flow",
        "capital_expenditures",
        "retained_earnings",
        "working_capital",
        "ebit",
    )

    def __init__(
        self,
        user_agent: Optional[str] = None,
        request_delay: float = 0.2,
        timeout: int = 30,
    ) -> None:
        resolved_user_agent = user_agent or SEC_USER_AGENT

        if not resolved_user_agent:
            raise ValueError(
                "SEC user_agent is required. "
                "Set SEC_USER_AGENT in your .env file or pass user_agent explicitly."
            )

        self.headers = {
            "User-Agent": resolved_user_agent,
            "Accept-Encoding": "gzip, deflate",
        }

        self.request_delay = request_delay
        self.timeout = timeout

        self._ticker_cache: Optional[dict[str, dict[str, Any]]] = None
        self._repository: Optional[SECRepository] = None

    def get_company_data(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """
        Public method used by ResearcherNode.

        It returns normalized SEC data for one ticker and optional date range.

        Workflow:
        1. Normalize ticker.
        2. Check SQLite first.
        3. If data is missing or refresh=True, fetch from SEC API.
        4. Normalize SEC company facts.
        5. Persist normalized data through SECRepository.
        6. Re-query SQLite.
        7. Return standardized data.

        Notes:
        SEC data is not naturally monthly like market prices or FRED series.
        This method accepts date ranges, but the returned data depends on
        available filing periods, usually annual 10-K and quarterly 10-Q facts.
        """

        ticker = self._normalize_ticker(ticker)
        errors: list[str] = []
        source = "database"

        try:
            if refresh or not self._has_required_data(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
            ):
                self._fetch_and_persist_company_data(ticker)
                source = "api_then_database"

        except Exception as exc:
            errors.append(f"SEC fetch failed for {ticker}: {exc}")
            source = "database_after_api_error"

        repository = self._get_repository()

        company = repository.get_company(ticker)
        metrics = repository.get_metrics(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )

        return self._build_company_data_response(
            ticker=ticker,
            company=company,
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
            source=source,
            errors=errors,
        )

    def get_company_tickers(self) -> dict[str, dict[str, Any]]:
        """
        Download and cache the SEC ticker-to-CIK mapping.
        """

        if self._ticker_cache is None:
            url = f"{self.BASE_SEC_URL}/files/company_tickers.json"
            self._ticker_cache = self._get_json(url)

        return self._ticker_cache

    def get_company_by_ticker(self, ticker: str) -> dict[str, Any]:
        """
        Return SEC company metadata for one ticker.

        Example SEC output:
        {
            "cik_str": 320193,
            "ticker": "AAPL",
            "title": "Apple Inc."
        }
        """

        ticker = self._normalize_ticker(ticker)
        companies = self.get_company_tickers()

        for company in companies.values():
            company_ticker = str(company.get("ticker", "")).upper().strip()

            if company_ticker == ticker:
                return company

        raise ValueError(f"Ticker not found in SEC mapping: {ticker}")

    def get_cik_from_ticker(self, ticker: str) -> str:
        """
        Return a zero-padded 10-digit CIK string.
        """

        company = self.get_company_by_ticker(ticker)
        return str(company["cik_str"]).zfill(10)

    def _get_repository(self) -> SECRepository:
        """
        Lazily instantiate the SEC repository.

        SECRepository should own the project database path internally,
        preferably through src.config.settings.DATABASE_PATH.
        """

        if self._repository is None:
            self._repository = SECRepository()

        return self._repository

    def _get_json(self, url: str) -> dict[str, Any]:
        """
        Internal SEC HTTP helper.

        Applies SEC-specific headers, timeout, and request delay.
        """

        time.sleep(self.request_delay)

        response = requests.get(
            url,
            headers=self.headers,
            timeout=self.timeout,
        )

        response.raise_for_status()
        return response.json()

    def _fetch_company_facts(self, ticker: str) -> dict[str, Any]:
        """
        Fetch raw SEC company facts from the SEC API.
        """

        cik = self.get_cik_from_ticker(ticker)
        url = f"{self.BASE_DATA_URL}/api/xbrl/companyfacts/CIK{cik}.json"

        return self._get_json(url)

    def _fetch_company_submissions(self, ticker: str) -> dict[str, Any]:
        """
        Fetch raw SEC company submissions metadata.

        This endpoint provides company-level metadata such as SIC code and
        SIC description, which are useful as an industry proxy.
        """

        cik = self.get_cik_from_ticker(ticker)
        url = f"{self.BASE_DATA_URL}/submissions/CIK{cik}.json"

        return self._get_json(url)

    def _fetch_and_persist_company_data(self, ticker: str) -> None:
        """
        Fetch raw company data from SEC, normalize it, and persist it.

        Because SEC company facts are returned as a broad historical payload,
        we fetch once and upsert all available normalized facts.
        """

        ticker = self._normalize_ticker(ticker)

        company = self.get_company_by_ticker(ticker)
        cik = str(company["cik_str"]).zfill(10)

        facts = self._fetch_company_facts(ticker)
        submissions = self._fetch_company_submissions(ticker)

        normalized_company = self._normalize_company(
            ticker=ticker,
            company=company,
            facts=facts,
            submissions=submissions,
        )

        normalized_metrics = self._extract_metrics(
            ticker=ticker,
            cik=cik,
            facts=facts,
        )

        repository = self._get_repository()
        repository.save_company(normalized_company)
        repository.save_metrics(normalized_metrics)
        
    def _normalize_company(
        self,
        ticker: str,
        company: dict[str, Any],
        facts: dict[str, Any],
        submissions: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize company metadata before persistence.

        SEC provides SIC and SIC description through the company submissions
        endpoint. We use those fields as the company's industry proxy.
        """

        cik = str(company["cik_str"]).zfill(10)

        company_name = (
            company.get("title")
            or facts.get("entityName")
            or facts.get("name")
            or submissions.get("name")
        )

        return {
            "ticker": ticker,
            "cik": cik,
            "company_name": company_name,
            "sic": submissions.get("sic"),
            "sic_description": submissions.get("sicDescription"),
            "updated_at": datetime.utcnow().isoformat(),
        }

    def _extract_metrics(
        self,
        ticker: str,
        cik: str,
        facts: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Convert raw SEC company facts into normalized metric rows.

        This method extracts multiple annual and quarterly periods.
        It does not return only the latest value.
        """

        rows_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}

        for metric_name, sec_metric_candidates in self.METRIC_CANDIDATES.items():
            for priority, sec_metric_name in enumerate(sec_metric_candidates):
                fact_values = self._get_fact_values(
                    facts=facts,
                    metric_name=metric_name,
                    sec_metric_name=sec_metric_name,
                )

                relevant_values = self._filter_statement_values(fact_values)

                for fact_value in relevant_values:
                    row = self._normalize_metric_row(
                        ticker=ticker,
                        cik=cik,
                        metric_name=metric_name,
                        sec_metric_name=sec_metric_name,
                        item=fact_value["item"],
                        unit=fact_value["unit"],
                        candidate_priority=priority,
                    )

                    key = (
                        row["ticker"],
                        row["metric_name"],
                        row["fiscal_year"],
                        row["fiscal_period"],
                        row["end_date"],
                    )

                    existing_row = rows_by_key.get(key)

                    if existing_row is None:
                        rows_by_key[key] = row
                        continue

                    if self._is_better_metric_row(row, existing_row):
                        rows_by_key[key] = row

        rows = list(rows_by_key.values())

        for row in rows:
            row.pop("_candidate_priority", None)

        return sorted(
            rows,
            key=lambda row: (
                row.get("ticker") or "",
                row.get("end_date") or "",
                row.get("metric_name") or "",
            ),
        )

    def _get_fact_values(
        self,
        facts: dict[str, Any],
        metric_name: str,
        sec_metric_name: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve fact values for a given US-GAAP SEC metric.

        Returns a list of dictionaries containing:
        - unit
        - raw SEC fact item
        """

        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        metric_payload = us_gaap.get(sec_metric_name)

        if not metric_payload:
            return []

        units = metric_payload.get("units", {})

        selected_units = self._select_units(
            metric_name=metric_name,
            available_units=units,
        )

        values: list[dict[str, Any]] = []

        for unit in selected_units:
            for item in units.get(unit, []):
                values.append(
                    {
                        "unit": unit,
                        "item": item,
                    }
                )

        return values

    def _select_units(
        self,
        metric_name: str,
        available_units: dict[str, list[dict[str, Any]]],
    ) -> list[str]:
        """
        Select the most relevant SEC units for a canonical metric.

        Most financial statement metrics should use USD.
        Shares outstanding should use shares.
        """

        if metric_name == "shares_outstanding":
            if "shares" in available_units:
                return ["shares"]

            return []

        if "USD" in available_units:
            return ["USD"]

        return []

    def _filter_statement_values(
        self,
        fact_values: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Keep annual and quarterly financial statement values.

        The agent needs trend support, so this method keeps both:
        - 10-K / FY facts
        - 10-Q / Q1, Q2, Q3, Q4 facts
        """

        relevant_values: list[dict[str, Any]] = []

        for fact_value in fact_values:
            item = fact_value["item"]

            form = item.get("form")
            fiscal_year = item.get("fy")
            fiscal_period = item.get("fp")
            value = item.get("val")
            end_date = item.get("end")

            if form not in {"10-K", "10-Q"}:
                continue

            if fiscal_year is None:
                continue

            if fiscal_period not in {"FY", "Q1", "Q2", "Q3", "Q4"}:
                continue

            if value is None:
                continue

            if end_date is None:
                continue

            relevant_values.append(fact_value)

        return relevant_values

    def _normalize_metric_row(
        self,
        ticker: str,
        cik: str,
        metric_name: str,
        sec_metric_name: str,
        item: dict[str, Any],
        unit: str,
        candidate_priority: int,
    ) -> dict[str, Any]:
        """
        Normalize one SEC fact item into the canonical metric schema.
        """

        return {
            "ticker": ticker,
            "cik": cik,
            "metric_name": metric_name,
            "sec_metric_name": sec_metric_name,
            "value": self._safe_float(item.get("val")),
            "fiscal_year": self._safe_int(item.get("fy")),
            "fiscal_period": item.get("fp"),
            "end_date": item.get("end"),
            "filed": item.get("filed"),
            "form": item.get("form"),
            "unit": unit,
            "frame": item.get("frame"),
            "_candidate_priority": candidate_priority,
        }

    def _is_better_metric_row(
        self,
        candidate_row: dict[str, Any],
        existing_row: dict[str, Any],
    ) -> bool:
        """
        Decide which row to keep when two SEC facts map to the same
        canonical metric and period.

        Priority rule:
        1. Prefer earlier metric candidate in METRIC_CANDIDATES.
        2. If same priority, prefer later filed date.
        """

        candidate_priority = candidate_row.get("_candidate_priority", 999)
        existing_priority = existing_row.get("_candidate_priority", 999)

        if candidate_priority < existing_priority:
            return True

        if candidate_priority > existing_priority:
            return False

        candidate_filed = candidate_row.get("filed") or ""
        existing_filed = existing_row.get("filed") or ""

        return candidate_filed > existing_filed

    def _has_required_data(
        self,
        ticker: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> bool:
        """
        Check whether the repository already contains enough data
        for the requested analysis window.

        For long ranges, this checks yearly coverage.
        For short ranges, this only checks if any metrics exist inside the window.
        """

        repository = self._get_repository()

        metrics = repository.get_metrics(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
        )

        if not metrics:
            return False

        start = self._parse_date(start_date)
        end = self._parse_date(end_date)

        if start is None or end is None:
            return True

        range_days = (end - start).days

        if range_days < 365:
            return True

        expected_years = set(range(start.year, end.year + 1))

        available_years = {
            self._safe_int(row.get("fiscal_year"))
            for row in metrics
            if self._safe_int(row.get("fiscal_year")) is not None
        }

        return expected_years.issubset(available_years)

    def _build_company_data_response(
        self,
        ticker: str,
        company: Optional[dict[str, Any]],
        metrics: list[dict[str, Any]],
        start_date: Optional[str],
        end_date: Optional[str],
        source: str,
        errors: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Build the standardized output consumed by ResearcherNode.
        """

        years_available = sorted(
            {
                self._safe_int(row.get("fiscal_year"))
                for row in metrics
                if self._safe_int(row.get("fiscal_year")) is not None
            }
        )

        periods_available = sorted(
            {
                f"{row.get('fiscal_year')}-{row.get('fiscal_period')}"
                for row in metrics
                if row.get("fiscal_year") is not None
                and row.get("fiscal_period") is not None
            }
        )

        metric_names_available = sorted(
            {
                row.get("metric_name")
                for row in metrics
                if row.get("metric_name")
            }
        )

        missing_core_metrics = [
            metric
            for metric in self.CORE_METRICS
            if metric not in metric_names_available
        ]

        missing_years = self._get_missing_years(
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "ticker": ticker,
            "company_name": self._get_company_name(company),
            "cik": self._get_company_cik(company),
            "sic": self._get_company_sic(company),
            "sic_description": self._get_company_sic_description(company),
            "source": source,
            "start_date": start_date,
            "end_date": end_date,
            "financials": metrics,
            "years_available": years_available,
            "periods_available": periods_available,
            "missing_years": missing_years,
            "missing_core_metrics": missing_core_metrics,
            "errors": errors or [],
        }

    def _get_missing_years(
        self,
        metrics: list[dict[str, Any]],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> list[int]:
        """
        Identify missing fiscal years inside a requested long-range window.
        """

        start = self._parse_date(start_date)
        end = self._parse_date(end_date)

        if start is None or end is None:
            return []

        if (end - start).days < 365:
            return []

        expected_years = set(range(start.year, end.year + 1))

        available_years = {
            self._safe_int(row.get("fiscal_year"))
            for row in metrics
            if self._safe_int(row.get("fiscal_year")) is not None
        }

        return sorted(expected_years - available_years)

    def _get_company_name(
        self,
        company: Optional[dict[str, Any]],
    ) -> Optional[str]:
        if not company:
            return None

        return (
            company.get("company_name")
            or company.get("title")
            or company.get("name")
        )

    def _get_company_cik(
        self,
        company: Optional[dict[str, Any]],
    ) -> Optional[str]:
        if not company:
            return None

        cik = company.get("cik") or company.get("cik_str")

        if cik is None:
            return None

        return str(cik).zfill(10)
    
    def _get_company_sic(
        self,
        company: Optional[dict[str, Any]],
    ) -> Optional[str]:
        if not company:
            return None

        sic = company.get("sic")

        if sic is None:
            return None

        return str(sic)


    def _get_company_sic_description(
        self,
        company: Optional[dict[str, Any]],
    ) -> Optional[str]:
        if not company:
            return None

        return company.get("sic_description") or company.get("sicDescription")

    def _normalize_ticker(self, ticker: str) -> str:
        return ticker.upper().strip().replace("$", "")

    def _safe_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_date(self, value: Optional[str]) -> Optional[datetime]:
        if value is None:
            return None

        for date_format in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                return datetime.strptime(value[: len(date_format)], date_format)
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None