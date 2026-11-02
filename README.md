# StockSage AI

A multi-agent financial research assistant for companies listed on the National Stock Exchange of India (NSE).

## Project objectives

- Retrieve and analyze historical market data.
- Summarize available company fundamentals and relevant news.
- Identify potential financial and market risks.
- Verify calculations, source evidence, and missing-data conditions.
- Produce structured research reports through a LangGraph workflow.

## Technology stack

- Python
- LangGraph
- Pydantic
- Pandas and NumPy
- Streamlit
- pytest
- Docker

## Setup

1. Install Python 3.11 or later.
2. Create and activate a virtual environment.
3. Install the project:

   `python -m pip install -e ".[dev]"`

4. Configure environment variables in `.env` when an LLM provider is selected.
5. Run the tests:

   `python -m pytest -v`

## Development status

Phase 1: Project setup and initial schema validation.

## Data and research disclaimer

This project is an educational financial research tool. Data availability and accuracy depend on the configured sources. Outputs are not guaranteed investment advice.
