from data_models.data_domain import DataDomain
from data_models.data_provider import DataProvider
from data_models.time_series_frequency import TimeSeriesFrequency


SEC_PROVIDER = DataProvider(
    id=1,
    name="SEC",
    data_domains={
        DataDomain.COMPANY,
        DataDomain.FINANCIAL_STATEMENT,
    },
    supported_frequencies={
        TimeSeriesFrequency.ANNUAL,
    },
)

FRED_PROVIDER = DataProvider(
    id=2,
    name="FRED",
    data_domains={DataDomain.MACROECONOMICS},
    supported_frequencies=set(TimeSeriesFrequency),
)

DEFAULT_DATA_PROVIDERS = (
    SEC_PROVIDER,
    FRED_PROVIDER,
)
