
import os

from dotenv import load_dotenv

load_dotenv()


def get_llm_config() -> dict[str, str | None]:
    """Read optional LLM configuration from environment variables."""

    return {
        "provider": os.getenv("LLM_PROVIDER") or None,
        "api_key": os.getenv("LLM_API_KEY") or None,
    }
