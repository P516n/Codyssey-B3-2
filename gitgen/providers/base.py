"""
Base classes and exceptions for AI API providers.
"""

from abc import ABC, abstractmethod
import json
from typing import Optional
import urllib.error
import urllib.request


class AIError(Exception):
    """Base exception for all AI API errors."""
    pass


class AuthenticationError(AIError):
    """Raised when authentication fails (missing or invalid API Key)."""
    pass


class RateLimitError(AIError):
    """Raised when rate limit or quota is exceeded."""
    pass


class InvalidRequestError(AIError):
    """Raised when the request parameters or payload are invalid."""
    pass


class NetworkError(AIError):
    """Raised when network connection fails or request times out."""
    pass


class BaseProvider(ABC):
    """Abstract base class for REST API AI providers."""

    def __init__(self, api_key: str, default_model: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.default_model = default_model
        self.base_url = base_url
        self.call_count = 0

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the provider (e.g., gemini, openai, anthropic)."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        """Sends prompt to the AI model and returns generated text."""
        pass

    def _execute_http_request(
        self,
        url: str,
        headers: dict,
        payload: dict,
        timeout: int = 45,
    ) -> dict:
        """
        Executes a REST HTTP POST request using Python's standard urllib.
        Parses JSON response and maps HTTP status codes to custom exceptions.
        """
        self.call_count += 1
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.getcode()
                raw_body = response.read().decode("utf-8", errors="replace")
                try:
                    return json.loads(raw_body)
                except json.JSONDecodeError:
                    return {"raw_text": raw_body}

        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8", errors="replace")
            err_msg = self._extract_error_message(raw_err, default=e.reason)
            status = e.code

            if status in (401, 403):
                raise AuthenticationError(
                    f"[{self.name}] 인증 실패 (HTTP {status}): API 키가 유효하지 않거나 권한이 없습니다. ({err_msg})"
                )
            elif status == 429:
                raise RateLimitError(
                    f"[{self.name}] 요청 한도 초과 (HTTP 429): Quota 또는 Rate limit을 초과했습니다. ({err_msg})"
                )
            elif status == 400:
                raise InvalidRequestError(
                    f"[{self.name}] 잘못된 요청 (HTTP 400): 파라미터 또는 모델 설정 확인 필요 ({err_msg})"
                )
            elif status >= 500:
                raise NetworkError(
                    f"[{self.name}] 서버 오류 (HTTP {status}): AI 제공자 측 일시적 장애 ({err_msg})"
                )
            else:
                raise AIError(f"[{self.name}] API 오류 (HTTP {status}): {err_msg}")

        except urllib.error.URLError as e:
            raise NetworkError(f"[{self.name}] 네트워크 연결 실패: {e.reason}")
        except TimeoutError:
            raise NetworkError(f"[{self.name}] 요청 시간 초과 (Timeout): 응답이 지연되고 있습니다.")
        except Exception as e:
            raise AIError(f"[{self.name}] 예상치 못한 오류 발생: {e}")

    def _extract_error_message(self, raw_err: str, default: str) -> str:
        """Attempts to parse error message from JSON error response."""
        try:
            data = json.loads(raw_err)
            # Common patterns: {"error": {"message": "..."}} or {"error": "..."}
            if isinstance(data, dict):
                if "error" in data:
                    err = data["error"]
                    if isinstance(err, dict) and "message" in err:
                        return err["message"]
                    return str(err)
                if "message" in data:
                    return str(data["message"])
        except Exception:
            pass
        return default or raw_err[:200]
