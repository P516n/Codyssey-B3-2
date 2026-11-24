"""Tests for safe_mode module."""

import unittest
from gitgen.git_service import GitContext
from gitgen.safe_mode import (
    mask_sensitive_text,
    truncate_diff,
    apply_safe_mode,
)


class TestSafeMode(unittest.TestCase):
    def test_mask_api_keys(self):
        # GitHub Secret Scanner 오탐(False Positive) 방지를 위해 문자열 결합으로 더미 키 생성
        dummy_openai = "sk-" + "fake_openai_test_key_1234567890"
        dummy_gemini = "AIza" + "SyDummyGoogleApiKeyForTesting123456"  # 4 + 35 = 39자
        dummy_anthropic = "sk-ant-api03-" + "fake_anthropic_key_1234567890"
        dummy_github = "ghp_" + "dummyGitHubTokenForTesting1234567890"  # 4 + 36 = 40자

        sample = (
            f"openai = {dummy_openai}\n"
            f"gemini = {dummy_gemini}\n"
            f"anthropic = {dummy_anthropic}\n"
            f"github = {dummy_github}\n"
            "email: dev@example.com\n"
            "password: mySuperSecret123!\n"
            "Authorization: Bearer mySecretToken1234567890"
        )
        masked, count = mask_sensitive_text(sample)
        self.assertGreater(count, 0)
        self.assertNotIn(dummy_openai, masked)
        self.assertNotIn(dummy_gemini, masked)
        self.assertNotIn(dummy_anthropic, masked)
        self.assertNotIn(dummy_github, masked)
        self.assertNotIn("dev@example.com", masked)
        self.assertNotIn("mySuperSecret123!", masked)
        self.assertIn("[REDACTED_OPENAI_KEY]", masked)
        self.assertIn("[REDACTED_GEMINI_KEY]", masked)
        self.assertIn("[REDACTED_ANTHROPIC_KEY]", masked)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", masked)
        self.assertIn("[REDACTED_EMAIL]", masked)
        self.assertIn("[REDACTED_SECRET]", masked)

    def test_truncate_diff(self):
        long_diff = "\n".join([f"line {i}" for i in range(300)])
        truncated, is_trunc = truncate_diff(long_diff, max_lines=50)
        self.assertTrue(is_trunc)
        self.assertIn("diff truncated by safe-mode", truncated)
        lines = truncated.splitlines()
        # 50 lines + notice
        self.assertLessEqual(len(lines), 55)

    def test_apply_safe_mode_limits_files(self):
        files = [f"file_{i}.py" for i in range(25)]
        ctx = GitContext(
            changed_files=files,
            diff_text="password = 'secretPassword123'",
            file_count=25,
            diff_line_count=1,
        )

        safe_ctx, audit = apply_safe_mode(ctx, max_files=10, max_lines=100)
        self.assertEqual(len(safe_ctx.changed_files), 11)  # 10 + notice string
        self.assertTrue(audit["files_truncated"])
        self.assertNotIn("secretPassword123", safe_ctx.diff_text)


if __name__ == "__main__":
    unittest.main()
