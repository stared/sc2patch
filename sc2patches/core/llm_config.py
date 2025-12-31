"""LLM configuration for the SC2Patches project.

Only these models may be used via OpenRouter API.
"""

ALLOWED_MODELS = [
    "openai/gpt-5.2",
    "google/gemini-3-pro-preview",
    "anthropic/claude-opus-4.5",
    "google/gemini-3-flash-preview",
]

# Default model for most operations
DEFAULT_MODEL = "google/gemini-3-pro-preview"
