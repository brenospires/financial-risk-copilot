from pydantic import BaseModel, ConfigDict, Field, field_validator


class CompanySource(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int | None = Field(default=None, gt=0)
    company_id: int = Field(gt=0)
    provider_id: int = Field(gt=0)
    provider_company_id: str = Field(min_length=1)
    ticker: str = Field(min_length=1)
    market: str = Field(min_length=1)
    exchange: str | None = None
    currency: str | None = None
    active: bool = True

    @field_validator("ticker", "currency")
    @classmethod
    def uppercase_codes(cls, value: str | None) -> str | None:
        return value.upper() if value else value
