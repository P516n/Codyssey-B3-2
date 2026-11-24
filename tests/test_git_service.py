"""Tests for git_service module."""

import unittest
from unittest.mock import patch, MagicMock
from gitgen.git_service import (
    GitContext,
    check_is_git_repo,
    collect_git_context,
    GitError,
    run_git_command,
)


class TestGitService(unittest.TestCase):
    def test_git_context_has_changes(self):
        ctx_empty = GitContext(file_count=0, diff_text="")
        self.assertFalse(ctx_empty.has_changes)

        ctx_files = GitContext(file_count=1, diff_text="")
        self.assertTrue(ctx_files.has_changes)

        ctx_diff = GitContext(file_count=0, diff_text="some diff content")
        self.assertTrue(ctx_diff.has_changes)

    def test_check_is_git_repo_true(self):
        # We are inside a git repository
        self.assertTrue(check_is_git_repo())

    @patch("gitgen.git_service.run_git_command")
    def test_collect_git_context_mocked(self, mock_run):
        def side_effect(args, cwd=None):
            cmd = " ".join(args)
            if "rev-parse --is-inside-work-tree" in cmd:
                return "true"
            if "rev-parse --abbrev-ref HEAD" in cmd:
                return "feature/test-branch"
            if "status --porcelain" in cmd:
                return " M src/main.py\n?? new_file.txt"
            if "diff HEAD" in cmd:
                return "diff --git a/src/main.py b/src/main.py\n+print('hello')"
            return ""

        mock_run.side_effect = side_effect

        ctx = collect_git_context()
        self.assertEqual(ctx.branch, "feature/test-branch")
        self.assertEqual(len(ctx.changed_files), 2)
        self.assertIn("src/main.py", ctx.changed_files)
        self.assertIn("new_file.txt", ctx.changed_files)
        self.assertTrue(ctx.has_changes)
        self.assertGreater(ctx.diff_line_count, 0)


if __name__ == "__main__":
    unittest.main()
