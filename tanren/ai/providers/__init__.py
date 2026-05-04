from tanren.ai.providers.base import BaseProvider, UsageInfo
from tanren.ai.providers.gemini import GeminiProvider
from tanren.ai.providers.claude import ClaudeProvider

REGISTRY: dict[str, type[BaseProvider]] = {
    "gemini": GeminiProvider,
    "claude": ClaudeProvider,
}

PROVIDER_LIST: list[tuple[str, str]] = [
    ("gemini", "Google Gemini  — 無料枠あり（推奨）"),
    ("claude", "Anthropic Claude — 有料 API が必要"),
]
