import math
import time
from datetime import date
from typing import Any

import pandas as pd
import requests

from config import sec as sec_config
from config.settings import (
    SEC_REQUEST_DELAY_SECONDS,
    SEC_REQUEST_TIMEOUT_SECONDS,
    SEC_USER_AGENT,
)
from data_models.company import Company
from data_models.data_domain import DataDomain
from data_models.data_provider import DataProvider
from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency
from tools.data_domains_retrieval.company import CompanyDataProvider
from tools.data_domains_retrieval.financial_statement import (
    FinancialStatementDataProvider,
)
from utils.identifiers import normalize_ticker
from utils.time_series import pivot_time_series


class SECProvider(CompanyDataProvider, FinancialStatementDataProvider):
    """SEC implementation for company and financial-statement retrieval."""

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
    ) -> pd.DataFrame:
        """
        Retrieve canonical SEC financial statements without persistence.

        Providing only start_date requests observations with that exact end
        date. Providing both dates requests observations whose end dates fall
        inside the inclusive range.
        """

        if frequency not in sec_config.SUPPORTED_FREQUENCIES:
            raise ValueError(
                f"SEC does not support {frequency.value} financial statements"
            )

        configured_frequencies = self.provider.supported_frequencies
        if (
            configured_frequencies is not None
            and frequency not in configured_frequencies
        ):
            raise ValueError(
                f"SEC provider is not configured for {frequency.value} data"
            )

        if end_date is not None and start_date > end_date:
            raise ValueError("start_date cannot be after end_date")

        normalized_ticker = normalize_ticker(ticker)
        facts = self._fetch_company_facts(normalized_ticker)
        measure_records = self._extract_measure_records(
            facts=facts,
        )
        auxiliary_records: list[dict[str, Any]] = []
        for name, candidates in sec_config.AUXILIARY_CANDIDATES.items():
            auxiliary_records.extend(
                self._extract_candidate_records(
                    facts=facts,
                    record_name=name,
                    candidates=candidates,
                    observation_type=(
                        sec_config.AUXILIARY_OBSERVATION_TYPES[name]
                    ),
                )
            )

        measure_records = self._select_canonical_records(measure_records)
        auxiliary_records = self._select_canonical_records(auxiliary_records)
        if end_date is None:
            measure_records = [
                record
                for record in measure_records
                if record["end_date"] == start_date
            ]
            auxiliary_records = [
                record
                for record in auxiliary_records
                if record["end_date"] == start_date
            ]
        else:
            measure_records = [
                record
                for record in measure_records
                if start_date <= record["end_date"] <= end_date
            ]
            auxiliary_records = [
                record
                for record in auxiliary_records
                if start_date <= record["end_date"] <= end_date
            ]

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

        measure_records = self._add_derived_measures(
            measure_records,
            auxiliary_records,
        )

        provider_id = self.provider.id
        if provider_id is None:
            raise RuntimeError(
                "SEC financial-statement provider has no persisted id"
            )

        index_names = (
            "provider_id",
            "ticker",
            "market",
            "unit",
            "frequency",
            "end_date",
        )
        expected_columns = tuple(
            measure.value for measure in FinancialStatementMeasure
        )

        if not measure_records:
            index = pd.MultiIndex.from_tuples([], names=index_names)
            return pd.DataFrame(
                index=index,
                columns=expected_columns,
            ).convert_dtypes()

        records = [
            {
                "provider_id": provider_id,
                "ticker": normalized_ticker,
                "market": market,
                "unit": record["unit"],
                "frequency": TimeSeriesFrequency.ANNUAL.value,
                "end_date": record["end_date"],
                "measure": record["record_name"].value,
                "value": record["value"],
            }
            for record in measure_records
        ]

        return pivot_time_series(
            records,
            values="value",
            columns="measure",
            timestamp="end_date",
            group_columns=index_names[:-1],
            expected_columns=expected_columns,
        )

    def _extract_measure_records(
        self,
        facts: dict[str, Any],
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        for measure, candidates in sec_config.MEASURE_CANDIDATES.items():
            if measure in sec_config.SNAPSHOT_MEASURES:
                observation_type = ObservationType.SNAPSHOT
            elif measure in sec_config.PERIOD_MEASURES:
                observation_type = ObservationType.PERIOD
            else:
                raise ValueError(
                    f"Unclassified financial statement measure: {measure}"
                )

            records.extend(
                self._extract_candidate_records(
                    facts=facts,
                    record_name=measure,
                    candidates=candidates,
                    observation_type=observation_type,
                )
            )

        return records

    def _extract_candidate_records(
        self,
        facts: dict[str, Any],
        record_name: FinancialStatementMeasure | str,
        candidates: tuple[str, ...],
        observation_type: ObservationType,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        namespaces = facts.get("facts", {})

        if not isinstance(namespaces, dict):
            return records

        taxonomy = namespaces.get("us-gaap", {})
        if not isinstance(taxonomy, dict):
            return records

        for priority, tag in enumerate(candidates):
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
        if form not in sec_config.ANNUAL_FORMS:
            return None

        if observation_type is ObservationType.PERIOD:
            duration_days = (end_date - start_date).days
            if not (
                sec_config.MINIMUM_ANNUAL_DURATION_DAYS
                <= duration_days
                <= sec_config.MAXIMUM_ANNUAL_DURATION_DAYS
            ):
                return None

        try:
            fiscal_year = int(item.get("fy"))
        except (TypeError, ValueError):
            fiscal_year = end_date.year

        if abs(fiscal_year - end_date.year) > 1:
            fiscal_year = end_date.year

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
            "filed_date": self._parse_date(item.get("filed")),
            "candidate_priority": candidate_priority,
        }

    def _select_canonical_records(
        self,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Select one source fact for each economic observation."""

        observations: dict[tuple[Any, ...], list[dict[str, Any]]] = {}

        for record in records:
            identity = (
                record["record_name"],
                record["observation_type"],
                record["end_date"],
                record["unit"],
            )
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
            canonical_records.append(
                min(preferred_candidates, key=self._canonical_record_rank)
            )

        return canonical_records

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

    def _add_derived_measures(
        self,
        measure_records: list[dict[str, Any]],
        auxiliary_records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Add deterministic measures missing from observed SEC facts."""

        records = list(measure_records)

        def period_key(record: dict[str, Any]) -> tuple[Any, ...]:
            return (
                record["observation_type"],
                record["end_date"],
                record["unit"],
            )

        def derive(
            left_records: list[dict[str, Any]],
            left_name: FinancialStatementMeasure | str,
            right_records: list[dict[str, Any]],
            right_name: FinancialStatementMeasure | str,
            result_name: FinancialStatementMeasure,
            operation: Any,
        ) -> None:
            right_by_period = {
                period_key(record): record
                for record in right_records
                if record["record_name"] == right_name
            }
            existing_periods = {
                period_key(record)
                for record in records
                if record["record_name"] == result_name
            }

            for left_record in left_records:
                if left_record["record_name"] != left_name:
                    continue

                key = period_key(left_record)
                right_record = right_by_period.get(key)
                if right_record is None or key in existing_periods:
                    continue

                derived_record = dict(left_record)
                derived_record["record_name"] = result_name
                derived_record["value"] = operation(
                    left_record["value"],
                    right_record["value"],
                )
                records.append(derived_record)
                existing_periods.add(key)

        derive(
            records,
            FinancialStatementMeasure.CURRENT_ASSETS,
            records,
            FinancialStatementMeasure.CURRENT_LIABILITIES,
            FinancialStatementMeasure.WORKING_CAPITAL,
            lambda left, right: left - right,
        )
        derive(
            records,
            FinancialStatementMeasure.OPERATING_CASH_FLOW,
            records,
            FinancialStatementMeasure.CAPITAL_EXPENDITURES,
            FinancialStatementMeasure.FREE_CASH_FLOW,
            lambda left, right: left - abs(right),
        )
        derive(
            auxiliary_records,
            "current_debt",
            auxiliary_records,
            "noncurrent_debt",
            FinancialStatementMeasure.DEBT,
            lambda left, right: left + right,
        )
        derive(
            auxiliary_records,
            "pretax_income",
            records,
            FinancialStatementMeasure.INTEREST_EXPENSE,
            FinancialStatementMeasure.EBIT,
            lambda left, right: left + abs(right),
        )

        existing_ebit_periods = {
            period_key(record)
            for record in records
            if record["record_name"] == FinancialStatementMeasure.EBIT
        }
        for record in list(records):
            key = period_key(record)
            if (
                record["record_name"]
                == FinancialStatementMeasure.OPERATING_INCOME
                and key not in existing_ebit_periods
            ):
                ebit_record = dict(record)
                ebit_record["record_name"] = FinancialStatementMeasure.EBIT
                records.append(ebit_record)
                existing_ebit_periods.add(key)

        derive(
            records,
            FinancialStatementMeasure.EBIT,
            auxiliary_records,
            "depreciation_and_amortization",
            FinancialStatementMeasure.EBITDA,
            lambda left, right: left + abs(right),
        )

        return records

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

    def _get_company_entry(self, ticker: str) -> dict[str, Any]:
        if self._ticker_cache is None:
            url = f"{sec_config.BASE_SEC_URL}/files/company_tickers.json"
            self._ticker_cache = self._get_json(url)

        normalized_ticker = normalize_ticker(ticker)

        for company in self._ticker_cache.values():
            company_ticker = str(company.get("ticker", "")).upper().strip()

            if company_ticker == normalized_ticker:
                return company

        raise ValueError(f"Ticker not found in SEC mapping: {normalized_ticker}")

    def _fetch_company_facts(self, ticker: str) -> dict[str, Any]:
        normalized_ticker = normalize_ticker(ticker)

        if normalized_ticker not in self._company_facts_cache:
            company = self._get_company_entry(normalized_ticker)
            cik = company.get("cik_str")
            if cik is None:
                raise ValueError(
                    f"SEC mapping has no CIK for ticker: {normalized_ticker}"
                )

            url = (
                f"{sec_config.BASE_DATA_URL}/api/xbrl/companyfacts/"
                f"CIK{str(cik).zfill(10)}.json"
            )
            self._company_facts_cache[normalized_ticker] = self._get_json(url)

        return self._company_facts_cache[normalized_ticker]
