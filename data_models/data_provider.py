from pydantic import BaseModel, ConfigDict, Field

from data_models.data_domain import DataDomain
from data_models.time_series_frequency import TimeSeriesFrequency


class DataProvider(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1)
    data_domains: set[DataDomain] = Field(min_length=1)
    supported_frequencies: set[TimeSeriesFrequency] | None = Field(
        default=None,
        min_length=1,
    )
    active: bool = True
