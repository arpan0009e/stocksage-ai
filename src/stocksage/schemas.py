
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchRequest(BaseModel):
    """Validated input for a company research run."""

    model_config = ConfigDict(str_strip_whitespace=True)

    symbol: str = Field(min_length=1, max_length=30)
    period: Literal["1mo", "3mo", "6mo", "1y", "2y"] = "6mo"

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        value = value.upper()

        if not all(c.isalnum() or c in ".&-" for c in value):
            raise ValueError("Symbol contains unsupported characters")

        return value


class ResearchReport(BaseModel):
    """Structured result for a company research run."""

    symbol: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: Literal["complete", "partial", "failed"] = "partial"
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
