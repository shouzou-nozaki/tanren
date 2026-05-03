from google import genai
from google.genai import types, errors as genai_errors
from tanren.ai.providers.base import BaseProvider, UsageInfo


class GeminiProvider(BaseProvider):
    id = "gemini"
    display_name = "Google Gemini"
    models = [
        ("gemini-2.5-flash",      "Gemini 2.5 Flash      — 推奨・バランス型（無料枠あり）"),
        ("gemini-2.5-pro",        "Gemini 2.5 Pro         — 高精度（無料枠あり）"),
        ("gemini-2.0-flash",      "Gemini 2.0 Flash       — 軽量・高速（無料枠あり）"),
        ("gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite  — 最軽量（無料枠あり）"),
    ]
    default_model = "gemini-2.5-flash"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def chat_stream(self, question: str, system: str, max_output_tokens: int = 1024):
        client = genai.Client(api_key=self._api_key)
        try:
            response = client.models.generate_content_stream(
                model=self._model,
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_output_tokens,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            raw_usage = None
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                if chunk.usage_metadata:
                    raw_usage = chunk.usage_metadata
            return self._normalize(raw_usage)
        except genai_errors.ClientError as e:
            if e.code == 429:
                raise RuntimeError(
                    "APIのレート制限に達しました。しばらく待ってから再試行してください。\n"
                    "APIキーが aistudio.google.com で取得したものか確認してください。"
                ) from e
            if e.code in (401, 403):
                raise RuntimeError(
                    "APIキーが無効です。tanren config api-key で再設定してください。"
                ) from e
            raise

    def generate(self, prompt: str, system: str, max_output_tokens: int = 1024) -> tuple[str, UsageInfo]:
        client = genai.Client(api_key=self._api_key)
        response = client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_output_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        return response.text, self._normalize(response.usage_metadata)

    def _normalize(self, raw) -> UsageInfo:
        if raw is None:
            return UsageInfo()
        return UsageInfo(
            input_tokens=getattr(raw, "prompt_token_count", 0) or 0,
            output_tokens=getattr(raw, "candidates_token_count", 0) or 0,
            cached_tokens=getattr(raw, "cached_content_token_count", 0) or 0,
        )
