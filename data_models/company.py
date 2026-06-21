from pydantic import BaseModel, ConfigDict, Field, field_validator

from utils.identifiers import normalize_ticker


class Company(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int | None = Field(default=None, gt=0)
    provider_id: int = Field(gt=0)
    ticker: str = Field(min_length=1)
    market: str = Field(min_length=1)
    name: str = Field(min_length=1)
    country: str | None = None
    sector: str | None = None
    active: bool = True

    @field_validator("ticker")
    @classmethod
    def uppercase_ticker(cls, value: str) -> str:
        return normalize_ticker(value)
