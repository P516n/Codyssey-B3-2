"""
OpenAI & OpenAI-compatible REST API client.
Supports official OpenAI endpoints, DeepSeek, Groq, Ollama, vLLM, etc.
"""

from typing import Optional
from gitgen.providers.base import BaseProvider, AIError


class OpenAIProvider(BaseProvider):
    """REST API client for OpenAI and OpenAI-compatible services."""

    def __init__(self, api_key: str, default_model: str = "gpt-5-mini", base_url: Optional[str] = None):
        super().__init__(api_key=api_key, default_model=default_model, base_url=base_url)

    @property
    def name(self) -> str:
        return "openai"

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        target_model = model or self.default_model

        base = (self.base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base}/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": max(0.0, min(temperature, 2.0)),
            "max_tokens": max_tokens,
        }

        response = self._execute_http_request(url, headers, payload)

        try:
            choices = response.get("choices", [])
            if not choices:
                raise AIError("OpenAI 응답에 choices 항목이 비어 있습니다.")

            message = choices[0].get("message", {})
            content = message.get("content", "")
            return content.strip()

        except KeyError as e:
            raise AIError(f"OpenAI 응답 파싱 실패 (누락된 키: {e}): {response}")
