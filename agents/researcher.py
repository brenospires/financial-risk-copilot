from datetime import date, datetime

from config.system_defaults import SEC_PROVIDER
from data_models.time_series_frequency import TimeSeriesFrequency
from workflow.state import AgentState
from tools.company_metrics import CompanyMetrics
from tools.data_providers.sec import SECProvider
from tools.financial_statement_trends import FinancialStatementTrends
from utils.dataframe import with_end_date_column


class ResearcherAgent:
    def __init__(self, state: AgentState):
        self.state = state

    def retrieve_data(self) -> AgentState:
        """Retrieve data based on the current state."""

        if self.state["status"] != "ready_for_pipeline":
            raise ValueError("Cannot retrieve data when the state is not ready for pipeline.")

        if self.state["intent"] == "company_risk_analysis":
            self._company_risk_analysis()
        elif self.state["intent"] == "company_overview":
            self._company_overview_analysis()
        
        if self.state["status"] != "done":
            self.state["status"] = "ready_for_response"
        return self.state

    def _company_risk_analysis(self) -> None:
        """Retrieve company risk analysis data based on the current state."""

        self._retrieve_company_financial_context()

    def _company_overview_analysis(self) -> None:
        """Retrieve company overview data based on the current state."""

        self._retrieve_company_financial_context()

    def _retrieve_company_financial_context(self) -> None:
        """Retrieve financial statements and calculate adjusted snapshot metrics."""

        ticker = self.state["tickers"][0]
        sec_tool = SECProvider(provider=SEC_PROVIDER)
        financial_statements = sec_tool.fetch_financial_statements(
            ticker=ticker,
            market="USA",
            frequency=TimeSeriesFrequency.ANNUAL,
            start_date=self._parse_date(self.state["start_date"]),
            end_date=self._parse_date(self.state["end_date"]),
        )

        if financial_statements is None or len(financial_statements) < 1:
            self._set_missing_ticker_data_answer(ticker)
            return

        financial_statements = with_end_date_column(financial_statements)
        financial_statements = financial_statements.sort_values("end_date")

        latest_financial_statement = financial_statements.iloc[[-1]]

        adjustment_tool = FinancialStatementTrends()
        adjusted_statements = adjustment_tool.adjust_financial_statements_by_trend(
            financial_statements
        )

        metrics_tool = CompanyMetrics()
        metrics = metrics_tool.calculate_metrics(adjusted_statements)

        self.state["company_data"] = { ticker: latest_financial_statement.to_dict() }
        self.state["company_metrics"] = { ticker: metrics }

    def _set_missing_ticker_data_answer(self, ticker: str) -> None:
        self.state["company_data"] = {}
        self.state["company_metrics"] = {}
        self.state["answer"] = f"Data for ticker {ticker} not found."
        self.state["status"] = "done"

    @staticmethod
    def _parse_date(value: str | None) -> date:
        if value is None:
            raise ValueError("Date value is required for company data retrieval.")

        return datetime.strptime(value, "%Y-%m-%d").date()
