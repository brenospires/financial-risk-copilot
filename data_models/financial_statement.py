from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from data_models.financial_statement_measure import FinancialStatementMeasure
from data_models.observation_type import ObservationType
from data_models.time_series_frequency import TimeSeriesFrequency
from utils.identifiers import normalize_ticker


class FinancialStatement(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int | None = Field(default=None, gt=0)
    provider_id: int = Field(gt=0)
    company_id: int | None = Field(default=None, gt=0)
    ticker: str = Field(min_length=1)
    market: str = Field(min_length=1)
    measure: FinancialStatementMeasure
    value: float
    unit: str = Field(min_length=1)
    observation_type: ObservationType
    frequency: TimeSeriesFrequency
    start_date: date | None = None
    end_date: date
    fiscal_year: int = Field(gt=0)
    fiscal_period: str = Field(min_length=1)

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, value: str) -> str:
        return normalize_ticker(value)

    @model_validator(mode="after")
    def validate_dates(self) -> "FinancialStatement":
        if self.observation_type is ObservationType.PERIOD:
            if self.start_date is None:
                raise ValueError("Period observations require start_date")
            if self.start_date > self.end_date:
                raise ValueError("start_date cannot be after end_date")

        if (
            self.observation_type is ObservationType.SNAPSHOT
            and self.start_date is not None
        ):
            raise ValueError("Snapshot observations cannot have start_date")

        return self
