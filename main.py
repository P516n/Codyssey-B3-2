"""
Main CLI entry point for gitgen.
Commands:
  python main.py commit
  python main.py pr
"""

import argparse
import sys
from typing import Optional

from gitgen.convention import load_convention
from gitgen.git_service import collect_git_context, GitError
from gitgen.prompt_builder import build_commit_prompt, build_pr_prompt
from gitgen.providers.base import AIError, AuthenticationError
from gitgen.providers.factory import get_provider, load_dotenv
from gitgen.safe_mode import apply_safe_mode
from gitgen.validator import validate_and_refine_commit, validate_and_refine_pr


def handle_commit(args: argparse.Namespace) -> int:
    """Handles the 'commit' command."""
    # 1. Collect git context
    try:
        context = collect_git_context()
    except GitError as e:
        print(f"[ERROR] {e}", file=sys.stderr, flush=True)
        return 1

    # 2. Check for changes
    if not context.has_changes:
        print("[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.", flush=True)
        return 0

    # 3. Verify provider and API key
    try:
        provider = get_provider(
            provider_name=args.provider,
            model=args.model,
            base_url=args.base_url,
        )
    except AuthenticationError as e:
        print(f"[ERROR] {e}", file=sys.stderr, flush=True)
        return 1

    # 4. Print collection status
    print(f"[INFO] Git status 수집 완료: {context.status_summary}", flush=True)
    print(f"[INFO] Git diff 수집 완료: {context.diff_line_count}줄", flush=True)

    # 5. Apply safe-mode if requested
    if args.safe_mode:
        context, audit = apply_safe_mode(context, max_files=10, max_lines=200)
        masked_cnt = audit["sensitive_replacements"]
        trunc_msg = " (diff/파일 제한 적용됨)" if (audit["lines_truncated"] or audit["files_truncated"]) else ""
        print(f"[INFO] Safe-mode 활성화: 민감정보 {masked_cnt}건 마스킹{trunc_msg}", flush=True)

    # 6. Load convention if specified
    convention = load_convention(args.convention)

    # 7. Build prompt & call AI
    prompt = build_commit_prompt(context, convention)
    print(f"[INFO] AI API 요청 중... (Provider: {provider.name}, Model: {provider.default_model})", flush=True)

    try:
        raw_output = provider.generate(
            prompt=prompt,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    except AIError as e:
        print(f"[ERROR] AI API 호출 실패: {e}", file=sys.stderr, flush=True)
        return 1

    # 8. Validate and refine output
    commit_msg, warnings = validate_and_refine_commit(raw_output)

    print("[DONE] 커밋 메시지 생성 완료", flush=True)
    print(f"[INFO] AI API 호출 횟수: {provider.call_count}회", flush=True)
    if warnings:
        for w in warnings:
            print(f"[WARN] {w}", flush=True)

    print("\n--- Commit Message ---")
    print(commit_msg)
    print("----------------------\n", flush=True)
    return 0


def handle_pr(args: argparse.Namespace) -> int:
    """Handles the 'pr' command."""
    # 1. Collect git context
    try:
        context = collect_git_context()
    except GitError as e:
        print(f"[ERROR] {e}", file=sys.stderr, flush=True)
        return 1

    # 2. Check for changes
    if not context.has_changes:
        print("[INFO] 변경 사항이 없습니다. PR 초안을 생성하지 않고 종료합니다.", flush=True)
        return 0

    # 3. Verify provider and API key
    try:
        provider = get_provider(
            provider_name=args.provider,
            model=args.model,
            base_url=args.base_url,
        )
    except AuthenticationError as e:
        print(f"[ERROR] {e}", file=sys.stderr, flush=True)
        return 1

    # 4. Print collection status
    print(f"[INFO] 현재 브랜치: {context.branch}", flush=True)
    print(f"[INFO] Git status 수집 완료: {context.status_summary}", flush=True)
    print(f"[INFO] Git diff 수집 완료: {context.diff_line_count}줄", flush=True)

    # 5. Apply safe-mode if requested
    if args.safe_mode:
        context, audit = apply_safe_mode(context, max_files=10, max_lines=200)
        masked_cnt = audit["sensitive_replacements"]
        trunc_msg = " (diff/파일 제한 적용됨)" if (audit["lines_truncated"] or audit["files_truncated"]) else ""
        print(f"[INFO] Safe-mode 활성화: 민감정보 {masked_cnt}건 마스킹{trunc_msg}", flush=True)

    # 6. Load convention if specified
    convention = load_convention(args.convention)

    # 7. Build prompt & call AI
    prompt = build_pr_prompt(context, convention)
    print(f"[INFO] AI API 요청 중... (Provider: {provider.name}, Model: {provider.default_model})", flush=True)

    try:
        raw_output = provider.generate(
            prompt=prompt,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    except AIError as e:
        print(f"[ERROR] AI API 호출 실패: {e}", file=sys.stderr, flush=True)
        return 1

    # 8. Validate and refine output
    title, body, warnings = validate_and_refine_pr(raw_output)

    print("[DONE] PR 초안 생성 완료", flush=True)
    print(f"[INFO] AI API 호출 횟수: {provider.call_count}회", flush=True)
    if warnings:
        for w in warnings:
            print(f"[WARN] {w}", flush=True)

    print("\n--- PR Title ---")
    print(title)
    print("\n--- PR Body ---")
    print(body)
    print("----------------\n", flush=True)
    return 0


def create_parser() -> argparse.ArgumentParser:
    """Creates the CLI argument parser with subcommands and custom aliases."""
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="AI 기반 Git 커밋 메시지 및 PR 설명 자동 생성 도구",
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 작업 (commit 또는 pr)")

    # Shared argument configuration helper
    def add_common_args(sub: argparse.ArgumentParser, default_max_tokens: int, default_temp: float):
        sub.add_argument(
            "-m", "--model", "-model",
            dest="model",
            type=str,
            default=None,
            help="사용할 AI 모델명 (기본값: Provider별 최적 모델, 예: gpt-5-mini, gemini-1.5-flash, gpt-4o-mini)",
        )
        sub.add_argument(
            "-p", "--provider", "-provider",
            dest="provider",
            type=str,
            default=None,
            choices=["codyssey", "copa", "gemini", "openai", "anthropic", "custom", "openai-compatible"],
            help="AI 제공자 선택 (지정하지 않으면 키 또는 모델명으로 자동 감지, 기본: codyssey)",
        )
        sub.add_argument(
            "-t", "--temperature", "-temperature",
            dest="temperature",
            type=float,
            default=default_temp,
            help=f"생성 다양성 조절 파라미터 (기본값: {default_temp})",
        )
        sub.add_argument(
            "-k", "--max-tokens", "-max-tokens",
            dest="max_tokens",
            type=int,
            default=default_max_tokens,
            help=f"최대 생성 토큰 수 (기본값: {default_max_tokens})",
        )
        sub.add_argument(
            "-s", "--safe-mode", "-safe-mode",
            dest="safe_mode",
            action="store_true",
            help="안전 모드 활성화 (민감정보 마스킹 및 diff 길이 제한)",
        )
        sub.add_argument(
            "--base-url", "-base-url",
            dest="base_url",
            type=str,
            default=None,
            help="사용자 정의 REST API Base URL (OpenAI 호환 서버, Ollama, Groq 등)",
        )
        sub.add_argument(
            "-c", "--convention", "-convention",
            dest="convention",
            type=str,
            default=None,
            help="컨벤션 설정 파일 경로 (.ai-gitgen.yml)",
        )

    # 1. commit command
    commit_parser = subparsers.add_parser("commit", help="커밋 메시지 자동 생성")
    add_common_args(commit_parser, default_max_tokens=300, default_temp=0.2)

    # 2. pr command
    pr_parser = subparsers.add_parser("pr", help="PR 제목 및 본문 초안 자동 생성")
    add_common_args(pr_parser, default_max_tokens=800, default_temp=0.3)

    return parser


def main() -> int:
    load_dotenv()
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "commit":
        return handle_commit(args)
    elif args.command == "pr":
        return handle_pr(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
