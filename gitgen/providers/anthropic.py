"""
Anthropic Claude REST API client.
"""

from typing import Optional
from gitgen.providers.base import BaseProvider, AIError


class AnthropicProvider(BaseProvider):
    """REST API client for Anthropic Claude."""

    def __init__(self, api_key: str, default_model: str = "claude-haiku-4", base_url: Optional[str] = None):
        super().__init__(api_key=api_key, default_model=default_model, base_url=base_url)

    @property
    def name(self) -> str:
        return "anthropic"

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        target_model = model or self.default_model

        base = (self.base_url or "https://api.anthropic.com/v1").rstrip("/")
        url = f"{base}/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": max(0.0, min(temperature, 1.0)),
            "max_tokens": max_tokens,
        }

        response = self._execute_http_request(url, headers, payload)

        try:
            contents = response.get("content", [])
            if not contents:
                raise AIError("Anthropic 응답에 content 항목이 비어 있습니다.")

            text_parts = [c.get("text", "") for c in contents if c.get("type") == "text"]
            return "\n".join(text_parts).strip()

        except KeyError as e:
            raise AIError(f"Anthropic 응답 파싱 실패 (누락된 키: {e}): {response}")
