from pydantic import BaseModel, ConfigDict, Field


class Company(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1)
    country: str | None = None
    industry: str | None = None
    sector: str | None = None
