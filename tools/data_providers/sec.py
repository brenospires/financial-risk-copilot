import math
import re
import time
from datetime import date
from typing import Any

import requests

from config.settings import (
    SEC_REQUEST_DELAY_SECONDS,
    SEC_REQUEST_TIMEOUT_SECONDS,
    SEC_USER_AGENT,
)
from data_models.company import Company
from data_models.data_domain import DataDomain
from data_models.data_provider import DataProvider
from data_models.financial_statement import FinancialStatement
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency
from tools.data_domains_retrieval.company import CompanyDataProvider
from tools.data_domains_retrieval.financial_statement import (
    FinancialStatementDataProvider,
)
from utils.identifiers import normalize_ticker


class SECProvider(CompanyDataProvider, FinancialStatementDataProvider):
    """SEC implementation for company and financial-statement retrieval."""

    BASE_SEC_URL = "https://www.sec.gov"
    BASE_DATA_URL = "https://data.sec.gov"

    ANNUAL_FORMS = frozenset(
        {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
    )
    QUARTERLY_FORMS = frozenset({"10-Q", "10-Q/A"})

    SUPPORTED_FREQUENCIES = frozenset(
        {
            TimeSeriesFrequency.QUARTERLY,
            TimeSeriesFrequency.ANNUAL,
        }
    )

    SNAPSHOT_MEASURES = frozenset(
        {
            FinancialStatementMeasure.ASSETS,
            FinancialStatementMeasure.CURRENT_ASSETS,
            FinancialStatementMeasure.CASH,
            FinancialStatementMeasure.INVENTORY,
            FinancialStatementMeasure.ACCOUNTS_RECEIVABLE,
            FinancialStatementMeasure.LIABILITIES,
            FinancialStatementMeasure.CURRENT_LIABILITIES,
            FinancialStatementMeasure.DEBT,
            FinancialStatementMeasure.LONG_TERM_DEBT,
            FinancialStatementMeasure.ACCOUNTS_PAYABLE,
            FinancialStatementMeasure.EQUITY,
            FinancialStatementMeasure.RETAINED_EARNINGS,
            FinancialStatementMeasure.WORKING_CAPITAL,
        }
    )

    PERIOD_MEASURES = frozenset(
        {
            FinancialStatementMeasure.REVENUE,
            FinancialStatementMeasure.GROSS_PROFIT,
            FinancialStatementMeasure.OPERATING_INCOME,
            FinancialStatementMeasure.NET_INCOME,
            FinancialStatementMeasure.EBIT,
            FinancialStatementMeasure.EBITDA,
            FinancialStatementMeasure.INTEREST_EXPENSE,
            FinancialStatementMeasure.OPERATING_CASH_FLOW,
            FinancialStatementMeasure.CAPITAL_EXPENDITURES,
            FinancialStatementMeasure.FREE_CASH_FLOW,
        }
    )

    MEASURE_CANDIDATES: dict[
        FinancialStatementMeasure,
        tuple[tuple[str, str], ...],
    ] = {
        FinancialStatementMeasure.ASSETS: (
            ("us-gaap", "Assets"),
            ("ifrs-full", "Assets"),
        ),
        FinancialStatementMeasure.CURRENT_ASSETS: (
            ("us-gaap", "AssetsCurrent"),
            ("ifrs-full", "CurrentAssets"),
        ),
        FinancialStatementMeasure.CASH: (
            ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
            (
                "us-gaap",
                "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
            ),
            ("ifrs-full", "CashAndCashEquivalents"),
        ),
        FinancialStatementMeasure.INVENTORY: (
            ("us-gaap", "InventoryNet"),
            ("ifrs-full", "Inventories"),
        ),
        FinancialStatementMeasure.ACCOUNTS_RECEIVABLE: (
            ("us-gaap", "AccountsReceivableNetCurrent"),
            ("ifrs-full", "TradeAndOtherCurrentReceivables"),
        ),
        FinancialStatementMeasure.LIABILITIES: (
            ("us-gaap", "Liabilities"),
            ("ifrs-full", "Liabilities"),
        ),
        FinancialStatementMeasure.CURRENT_LIABILITIES: (
            ("us-gaap", "LiabilitiesCurrent"),
            ("ifrs-full", "CurrentLiabilities"),
        ),
        FinancialStatementMeasure.DEBT: (
            ("us-gaap", "LongTermDebtAndFinanceLeaseObligations"),
            ("ifrs-full", "Borrowings"),
        ),
        FinancialStatementMeasure.LONG_TERM_DEBT: (
            (
                "us-gaap",
                "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
            ),
            ("us-gaap", "LongTermDebtNoncurrent"),
            ("us-gaap", "LongTermDebt"),
            ("ifrs-full", "NoncurrentBorrowings"),
        ),
        FinancialStatementMeasure.ACCOUNTS_PAYABLE: (
            ("us-gaap", "AccountsPayableCurrent"),
            ("ifrs-full", "TradeAndOtherCurrentPayables"),
        ),
        FinancialStatementMeasure.EQUITY: (
            ("us-gaap", "StockholdersEquity"),
            (
                "us-gaap",
                "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            ),
            ("ifrs-full", "Equity"),
        ),
        FinancialStatementMeasure.RETAINED_EARNINGS: (
            ("us-gaap", "RetainedEarningsAccumulatedDeficit"),
            ("ifrs-full", "RetainedEarnings"),
        ),
        FinancialStatementMeasure.WORKING_CAPITAL: (
            ("us-gaap", "WorkingCapital"),
        ),
        FinancialStatementMeasure.REVENUE: (
            (
                "us-gaap",
                "RevenueFromContractWithCustomerExcludingAssessedTax",
            ),
            ("us-gaap", "Revenues"),
            ("us-gaap", "SalesRevenueNet"),
            ("ifrs-full", "Revenue"),
        ),
        FinancialStatementMeasure.GROSS_PROFIT: (
            ("us-gaap", "GrossProfit"),
            ("ifrs-full", "GrossProfit"),
        ),
        FinancialStatementMeasure.OPERATING_INCOME: (
            ("us-gaap", "OperatingIncomeLoss"),
            ("ifrs-full", "ProfitLossFromOperatingActivities"),
        ),
        FinancialStatementMeasure.NET_INCOME: (
            ("us-gaap", "NetIncomeLoss"),
            ("ifrs-full", "ProfitLoss"),
        ),
        FinancialStatementMeasure.EBIT: (),
        FinancialStatementMeasure.EBITDA: (),
        FinancialStatementMeasure.INTEREST_EXPENSE: (
            ("us-gaap", "InterestExpenseNonOperating"),
            ("us-gaap", "InterestExpense"),
            ("ifrs-full", "FinanceCosts"),
        ),
        FinancialStatementMeasure.OPERATING_CASH_FLOW: (
            ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
            (
                "us-gaap",
                "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            ),
            ("ifrs-full", "CashFlowsFromUsedInOperatingActivities"),
        ),
        FinancialStatementMeasure.CAPITAL_EXPENDITURES: (
            ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
            ("us-gaap", "PaymentsToAcquireProductiveAssets"),
            ("ifrs-full", "PurchaseOfPropertyPlantAndEquipment"),
        ),
        FinancialStatementMeasure.FREE_CASH_FLOW: (),
    }

    AUXILIARY_CANDIDATES: dict[str, tuple[tuple[str, str], ...]] = {
        "current_debt": (
            ("us-gaap", "ShortTermBorrowings"),
            ("us-gaap", "ShortTermDebt"),
            ("us-gaap", "LongTermDebtCurrent"),
            (
                "us-gaap",
                "LongTermDebtAndFinanceLeaseObligationsCurrent",
            ),
            ("ifrs-full", "CurrentBorrowings"),
        ),
        "noncurrent_debt": (
            (
                "us-gaap",
                "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
            ),
            ("us-gaap", "LongTermDebtNoncurrent"),
            ("ifrs-full", "NoncurrentBorrowings"),
        ),
        "pretax_income": (
            (
                "us-gaap",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            ),
            (
                "us-gaap",
                "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
            ),
            ("us-gaap", "IncomeLossFromContinuingOperationsBeforeIncomeTaxes"),
            ("ifrs-full", "ProfitLossBeforeTax"),
        ),
        "depreciation_and_amortization": (
            ("us-gaap", "DepreciationDepletionAndAmortization"),
            ("us-gaap", "DepreciationDepletionAndAmortizationPropertyPlantAndEquipment"),
            ("us-gaap", "DepreciationAndAmortization"),
            ("ifrs-full", "DepreciationAndAmortisationExpense"),
        ),
    }

    AUXILIARY_OBSERVATION_TYPES = {
        "current_debt": ObservationType.SNAPSHOT,
        "noncurrent_debt": ObservationType.SNAPSHOT,
        "pretax_income": ObservationType.PERIOD,
        "depreciation_and_amortization": ObservationType.PERIOD,
    }

    def __init__(
        self,
        provider: DataProvider,
        user_agent: str | None = None,
        request_delay: float = SEC_REQUEST_DELAY_SECONDS,
        timeout: int = SEC_REQUEST_TIMEOUT_SECONDS,
        session: requests.Session | None = None,
    ) -> None:
        self._validate_provider(provider)

        resolved_user_agent = user_agent or SEC_USER_AGENT

        if not resolved_user_agent:
            raise ValueError(
                "SEC user agent is required. Set SEC_USER_AGENT or pass "
                "user_agent explicitly."
            )

        if request_delay < 0:
            raise ValueError("request_delay cannot be negative")

        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self.provider = provider
        self.request_delay = request_delay
        self.timeout = timeout
        self.session = session or requests.Session()
        self.headers = {
            "User-Agent": resolved_user_agent,
            "Accept-Encoding": "gzip, deflate",
        }

        self._ticker_cache: dict[str, dict[str, Any]] | None = None
        self._company_facts_cache: dict[str, dict[str, Any]] = {}
        self._submissions_cache: dict[str, dict[str, Any]] = {}

    def fetch_company(
        self,
        ticker: str,
        market: str,
    ) -> Company:
        """Retrieve reliable SEC company metadata without persistence."""

        normalized_ticker = normalize_ticker(ticker)
        company_entry = self._get_company_entry(normalized_ticker)
        company_name = str(company_entry.get("title") or "").strip()

        if not company_name:
            submissions = self._fetch_company_submissions(normalized_ticker)
            company_name = str(submissions.get("name") or "").strip()

        if not company_name:
            raise ValueError(
                f"SEC returned no company name for ticker: {normalized_ticker}"
            )

        provider_id = self.provider.id

        if provider_id is None:
            raise RuntimeError("SEC company provider has no persisted id")

        return Company(
            provider_id=provider_id,
            ticker=normalized_ticker,
            market=market,
            name=company_name,
            country=None,
            sector=None,
        )

    def fetch_financial_statements(
        self,
        ticker: str,
        market: str,
        frequency: TimeSeriesFrequency,
        start_date: date,
        end_date: date | None = None,
    ) -> list[FinancialStatement]:
        """
        Retrieve canonical SEC financial statements without persistence.

        Providing only start_date requests observations with that exact end
        date. Providing both dates requests observations whose end dates fall
        inside the inclusive range.
        """

        self._validate_statement_request(
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
        )

        normalized_ticker = normalize_ticker(ticker)
        facts = self._fetch_company_facts(normalized_ticker)
        measure_records = self._extract_measure_records(
            facts=facts,
            frequency=frequency,
        )
        auxiliary_records = self._extract_auxiliary_records(
            facts=facts,
            frequency=frequency,
        )

        measure_records = self._select_canonical_records(measure_records)
        auxiliary_records = self._select_canonical_records(auxiliary_records)
        measure_records = self._filter_records_by_request(
            records=measure_records,
            start_date=start_date,
            end_date=end_date,
        )
        auxiliary_records = self._filter_records_by_request(
            records=auxiliary_records,
            start_date=start_date,
            end_date=end_date,
        )

        reporting_unit = self._select_reporting_unit(measure_records)

        if reporting_unit is not None:
            measure_records = [
                record
                for record in measure_records
                if record["unit"] == reporting_unit
            ]
            auxiliary_records = [
                record
                for record in auxiliary_records
                if record["unit"] == reporting_unit
            ]

        measure_records = self._add_derived_measure_records(
            measure_records=measure_records,
            auxiliary_records=auxiliary_records,
        )

        return self._build_financial_statement_models(
            records=measure_records,
            ticker=normalized_ticker,
            market=market,
            frequency=frequency,
        )

    def _validate_statement_request(
        self,
        frequency: TimeSeriesFrequency,
        start_date: date,
        end_date: date | None,
    ) -> None:
        if frequency not in self.SUPPORTED_FREQUENCIES:
            raise ValueError(
                f"SEC does not support {frequency.value} financial statements"
            )

        configured_frequencies = (
            self.provider.supported_frequencies
        )

        if (
            configured_frequencies is not None
            and frequency not in configured_frequencies
        ):
            raise ValueError(
                f"SEC provider is not configured for {frequency.value} data"
            )

        if end_date is not None and start_date > end_date:
            raise ValueError("start_date cannot be after end_date")

    def _extract_measure_records(
        self,
        facts: dict[str, Any],
        frequency: TimeSeriesFrequency,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        for measure, candidates in self.MEASURE_CANDIDATES.items():
            observation_type = self._get_measure_observation_type(measure)
            records.extend(
                self._extract_candidate_records(
                    facts=facts,
                    record_name=measure,
                    candidates=candidates,
                    observation_type=observation_type,
                    frequency=frequency,
                )
            )

        return records

    def _extract_auxiliary_records(
        self,
        facts: dict[str, Any],
        frequency: TimeSeriesFrequency,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        for auxiliary_name, candidates in self.AUXILIARY_CANDIDATES.items():
            records.extend(
                self._extract_candidate_records(
                    facts=facts,
                    record_name=auxiliary_name,
                    candidates=candidates,
                    observation_type=(
                        self.AUXILIARY_OBSERVATION_TYPES[auxiliary_name]
                    ),
                    frequency=frequency,
                )
            )

        return records

    def _extract_candidate_records(
        self,
        facts: dict[str, Any],
        record_name: FinancialStatementMeasure | str,
        candidates: tuple[tuple[str, str], ...],
        observation_type: ObservationType,
        frequency: TimeSeriesFrequency,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        namespaces = facts.get("facts", {})

        if not isinstance(namespaces, dict):
            return records

        for priority, (namespace, tag) in enumerate(candidates):
            taxonomy = namespaces.get(namespace, {})

            if not isinstance(taxonomy, dict):
                continue

            payload = taxonomy.get(tag, {})
            units = payload.get("units", {}) if isinstance(payload, dict) else {}

            if not isinstance(units, dict):
                continue

            for unit, items in units.items():
                if not isinstance(items, list):
                    continue

                for item in items:
                    record = self._normalize_fact_record(
                        item=item,
                        record_name=record_name,
                        observation_type=observation_type,
                        frequency=frequency,
                        namespace=namespace,
                        tag=tag,
                        unit=str(unit),
                        candidate_priority=priority,
                    )

                    if record is not None:
                        records.append(record)

        return records

    def _normalize_fact_record(
        self,
        item: Any,
        record_name: FinancialStatementMeasure | str,
        observation_type: ObservationType,
        frequency: TimeSeriesFrequency,
        namespace: str,
        tag: str,
        unit: str,
        candidate_priority: int,
    ) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None

        value = self._safe_float(item.get("val"))
        end_date = self._parse_date(item.get("end"))
        start_date = self._parse_date(item.get("start"))

        if value is None or end_date is None:
            return None

        if observation_type is ObservationType.PERIOD and start_date is None:
            return None

        form = str(item.get("form") or "").upper()
        frame = str(item.get("frame") or "")

        if not self._matches_frequency(
            observation_type=observation_type,
            frequency=frequency,
            form=form,
            frame=frame,
            start_date=start_date,
            end_date=end_date,
        ):
            return None

        fiscal_period = self._resolve_fiscal_period(
            item=item,
            frequency=frequency,
            frame=frame,
            form=form,
        )

        if fiscal_period is None:
            return None

        fiscal_year = self._resolve_fiscal_year(
            item=item,
            end_date=end_date,
        )

        return {
            "record_name": record_name,
            "value": value,
            "unit": unit,
            "observation_type": observation_type,
            "start_date": (
                start_date
                if observation_type is ObservationType.PERIOD
                else None
            ),
            "end_date": end_date,
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
            "form": form,
            "filed_date": self._parse_date(item.get("filed")),
            "frame": frame or None,
            "namespace": namespace,
            "source_tag": tag,
            "candidate_priority": candidate_priority,
        }

    def _matches_frequency(
        self,
        observation_type: ObservationType,
        frequency: TimeSeriesFrequency,
        form: str,
        frame: str,
        start_date: date | None,
        end_date: date,
    ) -> bool:
        if frequency is TimeSeriesFrequency.ANNUAL:
            if form not in self.ANNUAL_FORMS:
                return False

            if observation_type is ObservationType.SNAPSHOT:
                return True

            return self._has_duration_between(
                start_date=start_date,
                end_date=end_date,
                minimum_days=300,
                maximum_days=400,
            )

        if frequency is not TimeSeriesFrequency.QUARTERLY:
            return False

        if observation_type is ObservationType.SNAPSHOT:
            if form in self.QUARTERLY_FORMS:
                return True

            return form in self.ANNUAL_FORMS and self._frame_quarter(frame) == "Q4"

        if not self._has_duration_between(
            start_date=start_date,
            end_date=end_date,
            minimum_days=60,
            maximum_days=120,
        ):
            return False

        if form in self.QUARTERLY_FORMS:
            return True

        return form in self.ANNUAL_FORMS and self._frame_quarter(frame) == "Q4"

    @staticmethod
    def _has_duration_between(
        start_date: date | None,
        end_date: date,
        minimum_days: int,
        maximum_days: int,
    ) -> bool:
        if start_date is None:
            return False

        duration_days = (end_date - start_date).days
        return minimum_days <= duration_days <= maximum_days

    def _resolve_fiscal_period(
        self,
        item: dict[str, Any],
        frequency: TimeSeriesFrequency,
        frame: str,
        form: str,
    ) -> str | None:
        if frequency is TimeSeriesFrequency.ANNUAL:
            return "FY"

        fiscal_period = str(item.get("fp") or "").upper()

        if fiscal_period in {"Q1", "Q2", "Q3", "Q4"}:
            return fiscal_period

        frame_quarter = self._frame_quarter(frame)

        if frame_quarter is not None:
            return frame_quarter

        if form in self.ANNUAL_FORMS:
            return "Q4"

        return None

    @staticmethod
    def _resolve_fiscal_year(
        item: dict[str, Any],
        end_date: date,
    ) -> int:
        try:
            fiscal_year = int(item.get("fy"))
        except (TypeError, ValueError):
            return end_date.year

        if abs(fiscal_year - end_date.year) > 1:
            return end_date.year

        return fiscal_year

    @staticmethod
    def _frame_quarter(frame: str) -> str | None:
        match = re.search(r"CY\d{4}Q([1-4])", frame.upper())
        return f"Q{match.group(1)}" if match else None

    def _get_measure_observation_type(
        self,
        measure: FinancialStatementMeasure,
    ) -> ObservationType:
        if measure in self.SNAPSHOT_MEASURES:
            return ObservationType.SNAPSHOT

        if measure in self.PERIOD_MEASURES:
            return ObservationType.PERIOD

        raise ValueError(f"Unclassified financial statement measure: {measure}")

    def _select_canonical_records(
        self,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Select one source fact for each economic observation."""

        observations: dict[tuple[Any, ...], list[dict[str, Any]]] = {}

        for record in records:
            identity = self._record_identity(record)
            observations.setdefault(identity, []).append(record)

        canonical_records: list[dict[str, Any]] = []

        for candidates in observations.values():
            best_priority = min(
                record["candidate_priority"] for record in candidates
            )
            preferred_candidates = [
                record
                for record in candidates
                if record["candidate_priority"] == best_priority
            ]
            latest_revisions = self._select_latest_context_revisions(
                preferred_candidates
            )
            canonical_records.append(
                min(latest_revisions, key=self._canonical_record_rank)
            )

        return canonical_records

    @staticmethod
    def _record_identity(record: dict[str, Any]) -> tuple[Any, ...]:
        return (
            record["record_name"],
            record["observation_type"],
            record["start_date"],
            record["end_date"],
            record["unit"],
        )

    def _select_latest_context_revisions(
        self,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        contexts: dict[tuple[Any, ...], dict[str, Any]] = {}

        for record in records:
            context = (
                record["namespace"],
                record["source_tag"],
                record["fiscal_year"],
                record["fiscal_period"],
                record["form"].removesuffix("/A"),
            )
            current = contexts.get(context)

            if current is None or self._filed_date_rank(
                record
            ) > self._filed_date_rank(current):
                contexts[context] = record

        return list(contexts.values())

    @staticmethod
    def _filed_date_rank(record: dict[str, Any]) -> date:
        return record["filed_date"] or date.min

    @staticmethod
    def _canonical_record_rank(record: dict[str, Any]) -> tuple[int, int]:
        filed_date = record["filed_date"]
        end_date = record["end_date"]

        if filed_date is None:
            return (1, 0)

        filing_delay = (filed_date - end_date).days

        if filing_delay < 0:
            return (1, abs(filing_delay))

        return (0, filing_delay)

    def _select_reporting_unit(
        self,
        records: list[dict[str, Any]],
    ) -> str | None:
        """Choose one reporting unit so calculated measures remain compatible."""

        preferred_measures = {
            FinancialStatementMeasure.REVENUE,
            FinancialStatementMeasure.ASSETS,
        }
        preferred_records = [
            record
            for record in records
            if record["record_name"] in preferred_measures
        ]
        candidates = preferred_records or records

        if not candidates:
            return None

        unit_counts: dict[str, int] = {}

        for record in candidates:
            unit = record["unit"]
            unit_counts[unit] = unit_counts.get(unit, 0) + 1

        return max(unit_counts, key=lambda unit: (unit_counts[unit], unit))

    def _add_derived_measure_records(
        self,
        measure_records: list[dict[str, Any]],
        auxiliary_records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Add measures with direct, deterministic accounting formulas."""

        records = list(measure_records)
        self._derive_from_two_records(
            records=records,
            left_records=records,
            left_name=FinancialStatementMeasure.CURRENT_ASSETS,
            right_records=records,
            right_name=FinancialStatementMeasure.CURRENT_LIABILITIES,
            result_name=FinancialStatementMeasure.WORKING_CAPITAL,
            operation=lambda left, right: left - right,
        )
        self._derive_from_two_records(
            records=records,
            left_records=records,
            left_name=FinancialStatementMeasure.OPERATING_CASH_FLOW,
            right_records=records,
            right_name=FinancialStatementMeasure.CAPITAL_EXPENDITURES,
            result_name=FinancialStatementMeasure.FREE_CASH_FLOW,
            operation=lambda left, right: left - abs(right),
        )
        self._derive_from_two_records(
            records=records,
            left_records=auxiliary_records,
            left_name="current_debt",
            right_records=auxiliary_records,
            right_name="noncurrent_debt",
            result_name=FinancialStatementMeasure.DEBT,
            operation=lambda left, right: left + right,
        )
        self._derive_from_two_records(
            records=records,
            left_records=auxiliary_records,
            left_name="pretax_income",
            right_records=records,
            right_name=FinancialStatementMeasure.INTEREST_EXPENSE,
            result_name=FinancialStatementMeasure.EBIT,
            operation=lambda left, right: left + abs(right),
        )
        self._copy_measure_when_missing(
            records=records,
            source_name=FinancialStatementMeasure.OPERATING_INCOME,
            result_name=FinancialStatementMeasure.EBIT,
        )
        self._derive_from_two_records(
            records=records,
            left_records=records,
            left_name=FinancialStatementMeasure.EBIT,
            right_records=auxiliary_records,
            right_name="depreciation_and_amortization",
            result_name=FinancialStatementMeasure.EBITDA,
            operation=lambda left, right: left + abs(right),
        )

        return records

    def _derive_from_two_records(
        self,
        records: list[dict[str, Any]],
        left_records: list[dict[str, Any]],
        left_name: FinancialStatementMeasure | str,
        right_records: list[dict[str, Any]],
        right_name: FinancialStatementMeasure | str,
        result_name: FinancialStatementMeasure,
        operation: Any,
    ) -> None:
        right_index = {
            self._calculation_period_key(record): record
            for record in right_records
            if record["record_name"] == right_name
        }
        existing_keys = {
            self._calculation_period_key(record)
            for record in records
            if record["record_name"] == result_name
        }

        for left_record in left_records:
            if left_record["record_name"] != left_name:
                continue

            period_key = self._calculation_period_key(left_record)
            right_record = right_index.get(period_key)

            if right_record is None or period_key in existing_keys:
                continue

            derived_record = dict(left_record)
            derived_record.update(
                {
                    "record_name": result_name,
                    "value": operation(
                        left_record["value"],
                        right_record["value"],
                    ),
                    "namespace": "derived",
                    "source_tag": result_name.value,
                    "candidate_priority": -1,
                }
            )
            records.append(derived_record)
            existing_keys.add(period_key)

    def _copy_measure_when_missing(
        self,
        records: list[dict[str, Any]],
        source_name: FinancialStatementMeasure,
        result_name: FinancialStatementMeasure,
    ) -> None:
        existing_keys = {
            self._calculation_period_key(record)
            for record in records
            if record["record_name"] == result_name
        }

        for source_record in list(records):
            if source_record["record_name"] != source_name:
                continue

            period_key = self._calculation_period_key(source_record)

            if period_key in existing_keys:
                continue

            derived_record = dict(source_record)
            derived_record.update(
                {
                    "record_name": result_name,
                    "namespace": "derived",
                    "source_tag": source_name.value,
                    "candidate_priority": -1,
                }
            )
            records.append(derived_record)
            existing_keys.add(period_key)

    @staticmethod
    def _calculation_period_key(record: dict[str, Any]) -> tuple[Any, ...]:
        return (
            record["observation_type"],
            record["start_date"],
            record["end_date"],
            record["unit"],
        )

    @staticmethod
    def _filter_records_by_request(
        records: list[dict[str, Any]],
        start_date: date,
        end_date: date | None,
    ) -> list[dict[str, Any]]:
        if end_date is None:
            return [
                record
                for record in records
                if record["end_date"] == start_date
            ]

        return [
            record
            for record in records
            if start_date <= record["end_date"] <= end_date
        ]

    def _build_financial_statement_models(
        self,
        records: list[dict[str, Any]],
        ticker: str,
        market: str,
        frequency: TimeSeriesFrequency,
    ) -> list[FinancialStatement]:
        provider_id = self.provider.id

        if provider_id is None:
            raise RuntimeError(
                "SEC financial-statement provider has no persisted id"
            )

        statements = [
            FinancialStatement(
                provider_id=provider_id,
                company_id=None,
                ticker=ticker,
                market=market,
                measure=record["record_name"],
                value=record["value"],
                unit=record["unit"],
                observation_type=record["observation_type"],
                frequency=frequency,
                start_date=record["start_date"],
                end_date=record["end_date"],
                fiscal_year=record["fiscal_year"],
                fiscal_period=record["fiscal_period"],
            )
            for record in records
        ]

        return sorted(
            statements,
            key=lambda statement: (
                statement.end_date,
                statement.start_date or date.min,
                statement.measure.value,
            ),
        )

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if value is None:
            return None

        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None

        return numeric_value if math.isfinite(numeric_value) else None

    @staticmethod
    def _validate_provider(provider: DataProvider) -> None:
        if provider.id is None:
            raise ValueError("SEC provider must have a persisted id")

        if provider.name.casefold() != "sec":
            raise ValueError(
                f"Expected SEC provider, received {provider.name!r}"
            )

        required_domains = {
            DataDomain.COMPANY,
            DataDomain.FINANCIAL_STATEMENT,
        }
        missing_domains = required_domains - provider.data_domains

        if missing_domains:
            missing_values = ", ".join(
                sorted(domain.value for domain in missing_domains)
            )
            raise ValueError(
                f"SEC provider does not support required domains: "
                f"{missing_values}"
            )

        if not provider.active:
            raise ValueError("SEC provider must be active")

    def _get_json(self, url: str) -> dict[str, Any]:
        time.sleep(self.request_delay)

        response = self.session.get(
            url,
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError(f"SEC returned an invalid JSON payload for {url}")

        return payload

    def _get_company_tickers(self) -> dict[str, dict[str, Any]]:
        if self._ticker_cache is None:
            url = f"{self.BASE_SEC_URL}/files/company_tickers.json"
            self._ticker_cache = self._get_json(url)

        return self._ticker_cache

    def _get_company_entry(self, ticker: str) -> dict[str, Any]:
        normalized_ticker = normalize_ticker(ticker)

        for company in self._get_company_tickers().values():
            company_ticker = str(company.get("ticker", "")).upper().strip()

            if company_ticker == normalized_ticker:
                return company

        raise ValueError(f"Ticker not found in SEC mapping: {normalized_ticker}")

    def _get_cik(self, ticker: str) -> str:
        company = self._get_company_entry(ticker)
        cik = company.get("cik_str")

        if cik is None:
            raise ValueError(f"SEC mapping has no CIK for ticker: {ticker}")

        return str(cik).zfill(10)

    def _fetch_company_facts(self, ticker: str) -> dict[str, Any]:
        normalized_ticker = normalize_ticker(ticker)

        if normalized_ticker not in self._company_facts_cache:
            cik = self._get_cik(normalized_ticker)
            url = f"{self.BASE_DATA_URL}/api/xbrl/companyfacts/CIK{cik}.json"
            self._company_facts_cache[normalized_ticker] = self._get_json(url)

        return self._company_facts_cache[normalized_ticker]

    def _fetch_company_submissions(self, ticker: str) -> dict[str, Any]:
        normalized_ticker = normalize_ticker(ticker)

        if normalized_ticker not in self._submissions_cache:
            cik = self._get_cik(normalized_ticker)
            url = f"{self.BASE_DATA_URL}/submissions/CIK{cik}.json"
            self._submissions_cache[normalized_ticker] = self._get_json(url)

        return self._submissions_cache[normalized_ticker]
