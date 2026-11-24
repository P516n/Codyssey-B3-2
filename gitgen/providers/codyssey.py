"""
Codyssey (copa.codyssey.kr) REST API client.
Uses OpenAI-compatible /v1/chat/completions endpoint.
Designed specifically for Codyssey course environment and virtual keys.
"""

import os
from typing import Optional
from gitgen.providers.openai import OpenAIProvider


class CodysseyProvider(OpenAIProvider):
    """
    REST API client for Codyssey third-party proxy provider.
    Endpoint: https://copa.codyssey.kr/v1/chat/completions
    Default model: gpt-5-mini
    """

    DEFAULT_BASE_URL = "https://copa.codyssey.kr/v1"
    DEFAULT_MODEL = "gpt-5-mini"

    def __init__(
        self,
        api_key: str,
        default_model: str = DEFAULT_MODEL,
        base_url: Optional[str] = None,
    ):
        chosen_base = base_url or os.getenv("AI_BASE_URL", self.DEFAULT_BASE_URL)
        super().__init__(
            api_key=api_key,
            default_model=default_model or self.DEFAULT_MODEL,
            base_url=chosen_base,
        )

    @property
    def name(self) -> str:
        return "codyssey"

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        target_model = model or self.default_model

        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            url = base
        else:
            url = f"{base}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Codyssey-GitGen/1.0",
        }

        # Request payload matching user's third-party provider specification
        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        # Reasoning models like gpt-5-mini reject the 'temperature' parameter with 502 error
        is_reasoning_model = any(
            target_model.startswith(prefix) for prefix in ["gpt-5", "o1", "o3"]
        )

        if not is_reasoning_model and temperature is not None:
            payload["temperature"] = max(0.0, min(temperature, 2.0))

        # Reasoning models consume internal tokens during thought process;
        # ensure sufficient buffer so content is not truncated with empty finish_reason=length
        if max_tokens:
            if is_reasoning_model and max_tokens < 1500:
                payload["max_tokens"] = 1500
            else:
                payload["max_tokens"] = max_tokens

        response = self._execute_http_request(url, headers, payload)

        try:
            choices = response.get("choices", [])
            if not choices:
                raise Exception("Codyssey 응답에 choices 항목이 비어 있습니다.")

            message = choices[0].get("message", {})
            content = message.get("content", "")
            return content.strip()

        except KeyError as e:
            raise Exception(f"Codyssey 응답 파싱 실패 (누락된 키: {e}): {response}")
