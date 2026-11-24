"""
Git service module for inspecting repository status, branch, and diffs.
"""

from dataclasses import dataclass, field
import subprocess
from typing import List, Optional


class GitError(Exception):
    """Raised when git command fails or is not executed in a git repository."""
    pass


@dataclass
class GitContext:
    """Holds collected git context information."""
    branch: str = "main"
    changed_files: List[str] = field(default_factory=list)
    diff_text: str = ""
    status_summary: str = ""
    file_count: int = 0
    diff_line_count: int = 0

    @property
    def has_changes(self) -> bool:
        """Returns True if there are any changes detected."""
        return self.file_count > 0 or bool(self.diff_text.strip())


def run_git_command(args: List[str], cwd: Optional[str] = None) -> str:
    """Executes a git command and returns stdout as a stripped string."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip()
    except FileNotFoundError:
        raise GitError("git 명령어를 찾을 수 없습니다. Git이 설치되어 있고 PATH에 등록되어 있는지 확인해주세요.")
    except subprocess.CalledProcessError as e:
        err = e.stderr.strip() if e.stderr else str(e)
        raise GitError(f"Git 명령어 실행 실패 ('git {' '.join(args)}'): {err}")


def check_is_git_repo(cwd: Optional[str] = None) -> bool:
    """Checks if the given directory is inside a Git working tree."""
    try:
        out = run_git_command(["rev-parse", "--is-inside-work-tree"], cwd=cwd)
        return out.lower() == "true"
    except GitError:
        return False


def get_current_branch(cwd: Optional[str] = None) -> str:
    """Gets the current git branch name."""
    try:
        branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
        if branch and branch != "HEAD":
            return branch
        # If in detached HEAD or no commits yet, try symbolic-ref or default
        out = run_git_command(["branch", "--show-current"], cwd=cwd)
        return out or "main"
    except GitError:
        return "main"


def collect_git_context(cwd: Optional[str] = None) -> GitContext:
    """
    Collects git branch, status (changed files), and diffs (staged and unstaged).
    Raises GitError if not in a git repository.
    """
    if not check_is_git_repo(cwd=cwd):
        raise GitError("Git 저장소 내부가 아닙니다. Git 프로젝트 루트에서 실행해주세요.")

    branch = get_current_branch(cwd=cwd)

    # 1. Collect status using porcelain
    status_raw = run_git_command(["status", "--porcelain"], cwd=cwd)
    changed_files: List[str] = []
    untracked_files: List[str] = []

    if status_raw:
        for line in status_raw.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            # status code is first 2 chars
            code = line[:2]
            filename = line[3:].strip()
            # If renamed, take the target name: "orig -> dest"
            if " -> " in filename:
                filename = filename.split(" -> ")[-1].strip()

            if code == "??":
                untracked_files.append(filename)
            else:
                changed_files.append(filename)

    # 2. Collect diff
    # First try `git diff HEAD` to capture all staged + unstaged changes
    diff_text = ""
    try:
        diff_text = run_git_command(["diff", "HEAD"], cwd=cwd)
    except GitError:
        # Might fail if repository has no commits yet (initial commit)
        try:
            staged = run_git_command(["diff", "--cached"], cwd=cwd)
            unstaged = run_git_command(["diff"], cwd=cwd)
            diff_text = f"{staged}\n{unstaged}".strip()
        except GitError:
            diff_text = ""

    # If diff is empty but there are untracked files, gather preview of untracked files
    all_changed_files = list(dict.fromkeys(changed_files + untracked_files))
    if not diff_text and untracked_files:
        diff_parts = []
        for uf in untracked_files[:10]:
            try:
                # Include a diff-like pseudo patch for newly added files
                diff_parts.append(f"diff --git a/{uf} b/{uf}\nnew file mode 100644\n--- /dev/null\n+++ b/{uf}")
            except Exception:
                pass
        diff_text = "\n".join(diff_parts)

    diff_lines = [l for l in diff_text.splitlines() if l.strip()]
    diff_line_count = len(diff_lines)
    file_count = len(all_changed_files)

    status_summary = f"{file_count}개 파일 변경 감지" if file_count > 0 else "변경 사항 없음"

    return GitContext(
        branch=branch,
        changed_files=all_changed_files,
        diff_text=diff_text,
        status_summary=status_summary,
        file_count=file_count,
        diff_line_count=diff_line_count,
    )
