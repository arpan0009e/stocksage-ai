
import pytest
from pydantic import ValidationError

from stocksage.schemas import ResearchRequest, ResearchReport


def test_research_request_normalizes_symbol():
    request = ResearchRequest(symbol="reliance", period="6mo")
    assert request.symbol == "RELIANCE"


def test_research_request_rejects_invalid_period():
    with pytest.raises(ValidationError):
        ResearchRequest(symbol="RELIANCE", period="10y")


def test_research_request_rejects_invalid_symbol():
    with pytest.raises(ValidationError):
        ResearchRequest(symbol="RELIANCE/INVALID")


def test_research_report_defaults():
    report = ResearchReport(symbol="RELIANCE")
    assert report.status == "partial"
    assert report.warnings == []
    assert report.sources == []
    assert report.generated_at.tzinfo is not None
