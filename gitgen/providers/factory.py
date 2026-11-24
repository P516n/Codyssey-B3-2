"""
Provider factory and key/provider resolution.
"""

import os
from typing import Optional

from gitgen.providers.base import BaseProvider, AuthenticationError
from gitgen.providers.gemini import GeminiProvider
from gitgen.providers.openai import OpenAIProvider
from gitgen.providers.anthropic import AnthropicProvider
from gitgen.providers.codyssey import CodysseyProvider


def load_dotenv(dotenv_path: str = ".env", override: bool = False) -> bool:
    """
    Zero-dependency .env file loader.
    Reads KEY=VALUE lines and populates os.environ without requiring external packages.
    Returns True if .env was found and loaded.
    """
    if not os.path.exists(dotenv_path):
        return False
    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("\"'")
                    if key and (override or key not in os.environ):
                        os.environ[key] = val
        return True
    except Exception:
        return False


def resolve_api_key(preferred_provider: Optional[str] = None, auto_load_env: bool = True) -> tuple[str, str]:
    """
    Resolves the API key and provider name.
    1. Loads .env file if present.
    2. Checks AI_API_KEY environment variable.
    3. Fallback to provider-specific env vars (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY).
    Returns (api_key, resolved_provider_hint).
    Raises AuthenticationError if no key is found.
    """
    if auto_load_env:
        load_dotenv()

    key = os.getenv("AI_API_KEY", "").strip()
    if key:
        return key, detect_provider_from_key(key)

    # Provider specific fallbacks
    if preferred_provider == "gemini" and os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_API_KEY", "").strip(), "gemini"
    if preferred_provider == "openai" and os.getenv("OPENAI_API_KEY"):
        return os.getenv("OPENAI_API_KEY", "").strip(), "openai"
    if preferred_provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        return os.getenv("ANTHROPIC_API_KEY", "").strip(), "anthropic"

    # Check any available provider key
    if os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_API_KEY", "").strip(), "gemini"
    if os.getenv("OPENAI_API_KEY"):
        return os.getenv("OPENAI_API_KEY", "").strip(), "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return os.getenv("ANTHROPIC_API_KEY", "").strip(), "anthropic"

    raise AuthenticationError(
        "AI_API_KEY 환경변수가 설정되지 않았습니다.\n"
        "## 예) export AI_API_KEY=\"YOUR_KEY\"\n"
        "## (Windows PowerShell: $env:AI_API_KEY=\"YOUR_KEY\")\n"
        "## 또는 프로젝트 루트의 .env 파일에 AI_API_KEY=YOUR_KEY 추가"
    )


def detect_provider_from_key(key: str) -> str:
    """Detects provider by common API key prefixes."""
    if key.startswith("sk-cody-") or key.startswith("cody-"):
        return "codyssey"
    if key.startswith("AIza"):
        return "gemini"
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("sk-proj-"):
        return "openai"
    # Default to codyssey in Codyssey environment
    return "codyssey"


def detect_provider_from_model(model: str) -> Optional[str]:
    """Infers provider name from model name."""
    m = model.lower()
    if m.startswith("gpt-5"):
        return "codyssey"
    if m.startswith("gemini"):
        return "gemini"
    if any(m.startswith(prefix) for prefix in ["gpt", "o1", "o3", "chatgpt", "text-embedding"]):
        return "openai"
    if m.startswith("claude"):
        return "anthropic"
    if any(m.startswith(prefix) for prefix in ["deepseek", "llama", "mistral", "qwen", "phi"]):
        return "openai"  # Typically served via OpenAI-compatible API
    return None


def get_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseProvider:
    """
    Creates and returns an appropriate AIProvider instance based on configuration.
    """
    # 1. Determine key and initial hint
    if not api_key:
        resolved_key, key_hint = resolve_api_key(preferred_provider=provider_name)
    else:
        resolved_key = api_key
        key_hint = detect_provider_from_key(resolved_key)

    # 2. Determine target provider
    target_provider = provider_name
    if not target_provider and model:
        target_provider = detect_provider_from_model(model)

    if not target_provider:
        target_provider = key_hint or "codyssey"

    target_provider = target_provider.lower().strip()

    # 3. Instantiate provider
    if target_provider in ("codyssey", "copa"):
        default_model = model or "gpt-5-mini"
        return CodysseyProvider(api_key=resolved_key, default_model=default_model, base_url=base_url)

    elif target_provider == "gemini":
        default_model = model or "gemini-1.5-flash"
        return GeminiProvider(api_key=resolved_key, default_model=default_model, base_url=base_url)

    elif target_provider in ("openai", "custom", "openai-compatible"):
        default_model = model or "gpt-4o-mini"
        return OpenAIProvider(api_key=resolved_key, default_model=default_model, base_url=base_url)

    elif target_provider == "anthropic":
        default_model = model or "claude-3-5-haiku-20241022"
        return AnthropicProvider(api_key=resolved_key, default_model=default_model, base_url=base_url)

    else:
        # Default to Codyssey provider
        default_model = model or "gpt-5-mini"
        return CodysseyProvider(api_key=resolved_key, default_model=default_model, base_url=base_url)
