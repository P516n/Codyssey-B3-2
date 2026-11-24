"""Integration tests for main CLI commands."""

import io
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import main
from gitgen.git_service import GitContext


class TestCLI(unittest.TestCase):
    @patch("main.collect_git_context")
    def test_no_changes_exits_cleanly(self, mock_git):
        mock_git.return_value = GitContext(file_count=0, diff_text="")

        captured_stdout = io.StringIO()
        with patch("sys.stdout", captured_stdout):
            with patch("sys.argv", ["main.py", "commit"]):
                exit_code = main.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("변경 사항이 없습니다", captured_stdout.getvalue())

    @patch("main.collect_git_context")
    @patch("main.load_dotenv")
    @patch("gitgen.providers.factory.load_dotenv")
    def test_missing_api_key(self, mock_factory_dotenv, mock_main_dotenv, mock_git):
        mock_git.return_value = GitContext(
            file_count=1,
            changed_files=["app.py"],
            diff_text="+print('hello')",
            diff_line_count=1,
        )

        captured_stderr = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with patch("sys.stderr", captured_stderr):
                with patch("sys.argv", ["main.py", "commit"]):
                    exit_code = main.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("AI_API_KEY 환경변수가 설정되지 않았습니다", captured_stderr.getvalue())

    @patch("main.collect_git_context")
    @patch("main.get_provider")
    def test_commit_flow_success(self, mock_get_provider, mock_git):
        mock_git.return_value = GitContext(
            branch="main",
            changed_files=["main.py", "utils.py"],
            diff_text="+code changes",
            file_count=2,
            diff_line_count=10,
            status_summary="2개 파일 변경 감지",
        )

        mock_provider = MagicMock()
        mock_provider.name = "gemini"
        mock_provider.default_model = "gemini-3-flash"
        mock_provider.call_count = 1
        mock_provider.generate.return_value = (
            "feat: Git diff 기반 커밋 메시지 자동 생성 기능 추가\n\n"
            "- main.py 및 utils.py 모듈 변경 사항 반영\n"
            "- 프롬프트 구성 및 검증 로직 적용"
        )
        mock_get_provider.return_value = mock_provider

        captured_stdout = io.StringIO()
        with patch.dict(os.environ, {"AI_API_KEY": "AIzaSyD_dummy"}, clear=True):
            with patch("sys.stdout", captured_stdout):
                with patch("sys.argv", ["main.py", "commit"]):
                    exit_code = main.main()

        self.assertEqual(exit_code, 0)
        out = captured_stdout.getvalue()
        self.assertIn("[INFO] Git status 수집 완료: 2개 파일 변경 감지", out)
        self.assertIn("[DONE] 커밋 메시지 생성 완료", out)
        self.assertIn("[INFO] AI API 호출 횟수: 1회", out)
        self.assertIn("--- Commit Message ---", out)
        self.assertIn("feat: Git diff 기반 커밋 메시지 자동 생성 기능 추가", out)
        self.assertIn("----------------------", out)

    @patch("main.collect_git_context")
    @patch("main.get_provider")
    def test_pr_flow_success(self, mock_get_provider, mock_git):
        mock_git.return_value = GitContext(
            branch="feature/ai-generator",
            changed_files=["main.py"],
            diff_text="+pr changes",
            file_count=1,
            diff_line_count=25,
            status_summary="1개 파일 변경 감지",
        )

        mock_provider = MagicMock()
        mock_provider.name = "openai"
        mock_provider.default_model = "gpt-5-mini"
        mock_provider.call_count = 1
        mock_provider.generate.return_value = (
            "feat: 커밋/PR 자동 생성 기능 추가\n\n"
            "## Why\n"
            "- 커밋 및 PR 작성 시간을 단축하기 위해 개발했습니다.\n\n"
            "## What\n"
            "- Git status 및 diff 수집 기능 구현\n"
            "- AI API 연동 및 템플릿 적용\n\n"
            "## How to Test\n"
            "- python main.py commit 및 python main.py pr 실행"
        )
        mock_get_provider.return_value = mock_provider

        captured_stdout = io.StringIO()
        with patch.dict(os.environ, {"AI_API_KEY": "sk-dummy"}, clear=True):
            with patch("sys.stdout", captured_stdout):
                with patch("sys.argv", ["main.py", "pr", "--safe-mode"]):
                    exit_code = main.main()

        self.assertEqual(exit_code, 0)
        out = captured_stdout.getvalue()
        self.assertIn("[INFO] 현재 브랜치: feature/ai-generator", out)
        self.assertIn("[INFO] Safe-mode 활성화", out)
        self.assertIn("[DONE] PR 초안 생성 완료", out)
        self.assertIn("[INFO] AI API 호출 횟수: 1회", out)
        self.assertIn("--- PR Title ---", out)
        self.assertIn("--- PR Body ---", out)
        self.assertIn("## Why", out)
        self.assertIn("## What", out)
        self.assertIn("## How to Test", out)


if __name__ == "__main__":
    unittest.main()
