"""LLM configuration for the SC2Patches project.

Only these models may be used via OpenRouter API.
"""

import os
import sys

ALLOWED_MODELS = [
    "openai/gpt-5.2",
    "google/gemini-3-pro-preview",
    "anthropic/claude-opus-4.5",
    "google/gemini-3-flash-preview",
]

# Default model for most operations
DEFAULT_MODEL = "google/gemini-3-pro-preview"


def get_openrouter_api_key() -> str:
    """Get OpenRouter API key from environment. Exit if not found."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set in environment")
        print("Set it in .env file or export OPENROUTER_API_KEY=...")
        sys.exit(1)
    return api_key  # type: ignore[return-value]  # sys.exit never returns
