"""Tests for providers and factory."""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from gitgen.providers.base import AuthenticationError
from gitgen.providers.factory import (
    detect_provider_from_key,
    detect_provider_from_model,
    resolve_api_key,
    get_provider,
    load_dotenv,
)
from gitgen.providers.gemini import GeminiProvider
from gitgen.providers.openai import OpenAIProvider
from gitgen.providers.anthropic import AnthropicProvider
from gitgen.providers.codyssey import CodysseyProvider


class TestProviders(unittest.TestCase):
    def test_load_dotenv(self):
        with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tmp:
            tmp.write(
                "# Comment line\n"
                "AI_API_KEY=AIzaSyTestFromDotenv\n"
                "OPENAI_MODEL='gpt-4o'\n"
                "EMPTY_LINE=\n"
            )
            tmp_path = tmp.name

        try:
            with patch.dict(os.environ, {}, clear=True):
                self.assertNotIn("AI_API_KEY", os.environ)
                loaded = load_dotenv(tmp_path)
                self.assertTrue(loaded)
                self.assertEqual(os.environ.get("AI_API_KEY"), "AIzaSyTestFromDotenv")
                self.assertEqual(os.environ.get("OPENAI_MODEL"), "gpt-4o")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_detect_provider_from_key(self):
        self.assertEqual(detect_provider_from_key("sk-cody-live-12345"), "codyssey")
        self.assertEqual(detect_provider_from_key("cody-key"), "codyssey")
        self.assertEqual(detect_provider_from_key("AIzaSyD12345"), "gemini")
        self.assertEqual(detect_provider_from_key("sk-ant-12345"), "anthropic")
        self.assertEqual(detect_provider_from_key("sk-proj-12345"), "openai")

    def test_detect_provider_from_model(self):
        self.assertEqual(detect_provider_from_model("gpt-5-mini"), "codyssey")
        self.assertEqual(detect_provider_from_model("gemini-1.5-flash"), "gemini")
        self.assertEqual(detect_provider_from_model("gpt-4o-mini"), "openai")
        self.assertEqual(detect_provider_from_model("claude-3-5-haiku-20241022"), "anthropic")
        self.assertEqual(detect_provider_from_model("deepseek-chat"), "openai")

    @patch("gitgen.providers.factory.load_dotenv")
    def test_resolve_api_key_missing(self, mock_load):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AuthenticationError):
                resolve_api_key(auto_load_env=False)

    def test_resolve_api_key_general(self):
        with patch.dict(os.environ, {"AI_API_KEY": "AIzaSyD_test_key"}, clear=True):
            key, provider = resolve_api_key()
            self.assertEqual(key, "AIzaSyD_test_key")
            self.assertEqual(provider, "gemini")

    def test_get_provider_factory(self):
        with patch.dict(os.environ, {"AI_API_KEY": "sk-cody-key"}, clear=True):
            provider = get_provider()
            self.assertIsInstance(provider, CodysseyProvider)
            self.assertEqual(provider.default_model, "gpt-5-mini")
            self.assertIn("copa.codyssey.kr", provider.base_url)

        with patch.dict(os.environ, {"AI_API_KEY": "sk-openai-key"}, clear=True):
            provider = get_provider(provider_name="openai")
            self.assertIsInstance(provider, OpenAIProvider)

        with patch.dict(os.environ, {"AI_API_KEY": "AIzaSyD-gemini-key"}, clear=True):
            provider = get_provider(provider_name="gemini")
            self.assertIsInstance(provider, GeminiProvider)

        with patch.dict(os.environ, {"AI_API_KEY": "sk-ant-claude-key"}, clear=True):
            provider = get_provider(provider_name="anthropic")
            self.assertIsInstance(provider, AnthropicProvider)

    @patch("gitgen.providers.base.urllib.request.urlopen")
    def test_codyssey_generate_payload(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"choices": [{"message": {"content": "feat: test message"}}]}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        provider = CodysseyProvider(api_key="sk-cody-virtual-key")
        result = provider.generate(prompt="hello prompt")

        self.assertEqual(result, "feat: test message")
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://copa.codyssey.kr/v1/chat/completions")
        self.assertEqual(req.headers.get("Authorization"), "Bearer sk-cody-virtual-key")


if __name__ == "__main__":
    unittest.main()
