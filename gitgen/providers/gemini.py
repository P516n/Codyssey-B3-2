"""
Google Gemini REST API client.
"""

from typing import Optional
from gitgen.providers.base import BaseProvider, AIError


class GeminiProvider(BaseProvider):
    """REST API client for Google Gemini (Generative Language API)."""

    def __init__(self, api_key: str, default_model: str = "gemini-3-flash", base_url: Optional[str] = None):
        super().__init__(api_key=api_key, default_model=default_model, base_url=base_url)

    @property
    def name(self) -> str:
        return "gemini"

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        target_model = model or self.default_model
        
        # Standard endpoint for Gemini REST v1beta
        base = (self.base_url or "https://generativelanguage.googleapis.com").rstrip("/")
        url = f"{base}/v1beta/models/{target_model}:generateContent"

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": max(0.0, min(temperature, 2.0)),
                "maxOutputTokens": max_tokens,
            },
        }

        response = self._execute_http_request(url, headers, payload)

        try:
            candidates = response.get("candidates", [])
            if not candidates:
                # Check for promptFeedback block
                feedback = response.get("promptFeedback", {})
                block_reason = feedback.get("blockReason")
                if block_reason:
                    raise AIError(f"Gemini 안전 정책에 의해 생성이 차단되었습니다: {block_reason}")
                raise AIError("Gemini 응답에 생성 결과(candidates)가 없습니다.")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise AIError("Gemini 응답 내용(parts)이 비어 있습니다.")

            return parts[0].get("text", "").strip()

        except KeyError as e:
            raise AIError(f"Gemini 응답 파싱 실패 (누락된 키: {e}): {response}")
