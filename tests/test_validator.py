"""Tests for validator module."""

import unittest
from gitgen.validator import validate_and_refine_commit, validate_and_refine_pr


class TestValidator(unittest.TestCase):
    def test_validate_commit_success(self):
        raw = "feat: add user authentication\n\n- Add auth service\n- Mention models/user.py"
        msg, warnings = validate_and_refine_commit(raw)
        self.assertEqual(len(warnings), 0)
        self.assertTrue(msg.startswith("feat: add user authentication"))
        self.assertIn("- Add auth service", msg)

    def test_validate_commit_markdown_fence_and_trim(self):
        long_title = "feat: " + ("a" * 80)
        raw = f"```\n{long_title}\n\nsome body\n```"
        msg, warnings = validate_and_refine_commit(raw, max_title_len=72)
        self.assertGreater(len(warnings), 0)
        lines = msg.splitlines()
        self.assertLessEqual(len(lines[0]), 72)
        self.assertIn("...", lines[0])

    def test_validate_pr_success(self):
        raw = (
            "feat: implement git diff collector\n\n"
            "## Why\n"
            "- Automate manual commit processes\n\n"
            "## What\n"
            "- Add git status and diff parser\n"
            "- Add safe mode\n\n"
            "## How to Test\n"
            "- Run python main.py commit"
        )
        title, body, warnings = validate_and_refine_pr(raw)
        self.assertEqual(title, "feat: implement git diff collector")
        self.assertIn("## Why", body)
        self.assertIn("## What", body)
        self.assertIn("## How to Test", body)
        self.assertEqual(len(warnings), 0)

    def test_validate_pr_missing_sections_recovery(self):
        raw = "PR Title: fix: resolve null pointer\n\nFixed a critical bug in parser."
        title, body, warnings = validate_and_refine_pr(raw)
        self.assertEqual(title, "fix: resolve null pointer")
        self.assertIn("## Why", body)
        self.assertIn("## What", body)
        self.assertIn("## How to Test", body)
        self.assertGreater(len(warnings), 0)


if __name__ == "__main__":
    unittest.main()
