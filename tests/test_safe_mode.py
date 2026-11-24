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
        sample = (
            "openai = sk-1234567890abcdef1234567890\n"
            "gemini = AIzaSyD1234567890abcdefghijklmnopqrstuv\n"
            "anthropic = sk-ant-api03-1234567890abcdef1234567890\n"
            "github = ghp_1234567890abcdefghijklmnopqrstuvwxyz12\n"
            "email: dev@example.com\n"
            "password: mySuperSecret123!\n"
            "Authorization: Bearer mySecretToken1234567890"
        )
        masked, count = mask_sensitive_text(sample)
        self.assertGreater(count, 0)
        self.assertNotIn("sk-1234567890", masked)
        self.assertNotIn("AIzaSyD", masked)
        self.assertNotIn("dev@example.com", masked)
        self.assertNotIn("mySuperSecret123!", masked)
        self.assertIn("[REDACTED_OPENAI_KEY]", masked)
        self.assertIn("[REDACTED_GEMINI_KEY]", masked)
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
