from tanren.ai.providers.base import BaseProvider, UsageInfo


class ClaudeProvider(BaseProvider):
    id = "claude"
    display_name = "Anthropic Claude"
    models = [
        ("claude-opus-4-7",          "Claude Opus 4.7    — 最高精度"),
        ("claude-sonnet-4-6",        "Claude Sonnet 4.6  — バランス型（推奨）"),
        ("claude-haiku-4-5-20251001","Claude Haiku 4.5   — 軽量・高速"),
    ]
    default_model = "claude-sonnet-4-6"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def chat_stream(self, question: str, system: str, max_output_tokens: int = 1024):
        anthropic = self._import_sdk()
        client = anthropic.Anthropic(api_key=self._api_key)
        try:
            with client.messages.stream(
                model=self._model,
                max_tokens=max_output_tokens,
                system=system,
                messages=[{"role": "user", "content": question}],
            ) as stream:
                for text in stream.text_stream:
                    yield text
                final = stream.get_final_message()
            return self._normalize(final.usage)
        except anthropic.AuthenticationError as e:
            raise RuntimeError(
                "Claude APIキーが無効です。tanren config api-key で再設定してください。"
            ) from e
        except anthropic.RateLimitError as e:
            raise RuntimeError("Claude APIのレート制限に達しました。") from e

    def generate(self, prompt: str, system: str, max_output_tokens: int = 1024) -> tuple[str, UsageInfo]:
        anthropic = self._import_sdk()
        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self._model,
            max_tokens=max_output_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text, self._normalize(response.usage)

    def _normalize(self, raw) -> UsageInfo:
        if raw is None:
            return UsageInfo()
        return UsageInfo(
            input_tokens=getattr(raw, "input_tokens", 0) or 0,
            output_tokens=getattr(raw, "output_tokens", 0) or 0,
            cached_tokens=getattr(raw, "cache_read_input_tokens", 0) or 0,
        )

    def _import_sdk(self):
        try:
            import anthropic
            return anthropic
        except ImportError:
            raise RuntimeError(
                "Claude を使うには anthropic パッケージが必要です:\n"
                "  pip install anthropic"
            )
