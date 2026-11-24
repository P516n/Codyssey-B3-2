"""
Safe mode security module.
Provides sensitive data masking (API keys, secrets, tokens, emails)
and diff length truncation for safe prompt construction.
"""

from dataclasses import replace
import re
from typing import List, Tuple

from gitgen.git_service import GitContext

# Regex patterns for sensitive information
SENSITIVE_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    # 1. API Keys and Tokens
    ("OpenAI API Key", re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE), "[REDACTED_OPENAI_KEY]"),
    ("Google API Key", re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "[REDACTED_GEMINI_KEY]"),
    ("Anthropic API Key", re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE), "[REDACTED_ANTHROPIC_KEY]"),
    ("GitHub Token", re.compile(r"gh[pousr]_[0-9a-zA-Z]{36}"), "[REDACTED_GITHUB_TOKEN]"),
    ("Generic Bearer Token", re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{16,}", re.IGNORECASE), "Bearer [REDACTED_BEARER_TOKEN]"),
    
    # 2. Private Keys
    ("Private Key Block", re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    
    # 3. Passwords, secrets, tokens in assignments (key=val or key: val)
    ("Secret Assignment", re.compile(r"((?:password|passwd|secret|api_key|apikey|auth_token|access_token)\s*[:=]\s*['\"]?)([^'\"\s\r\n]{4,})(['\"]?)", re.IGNORECASE), r"\1[REDACTED_SECRET]\3"),
    
    # 4. Email addresses
    ("Email Address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    
    # 5. JWT tokens
    ("JWT Token", re.compile(r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}"), "[REDACTED_JWT_TOKEN]"),
]


def mask_sensitive_text(text: str) -> Tuple[str, int]:
    """
    Masks sensitive data in the input text using predefined regular expressions.
    Returns (masked_text, total_replacements_count).
    """
    if not text:
        return text, 0

    masked = text
    total_replacements = 0

    for name, pattern, replacement in SENSITIVE_PATTERNS:
        matches = pattern.findall(masked)
        if matches:
            total_replacements += len(matches)
            masked = pattern.sub(replacement, masked)

    return masked, total_replacements


def truncate_diff(diff_text: str, max_lines: int = 200) -> Tuple[str, bool]:
    """
    Truncates diff text if it exceeds max_lines.
    Returns (truncated_text, is_truncated).
    """
    if not diff_text:
        return diff_text, False

    lines = diff_text.splitlines()
    if len(lines) <= max_lines:
        return diff_text, False

    kept_lines = lines[:max_lines]
    omitted = len(lines) - max_lines
    notice = f"\n\n... [diff truncated by safe-mode: {omitted} lines omitted (max {max_lines} lines)]"
    return "\n".join(kept_lines) + notice, True


def apply_safe_mode(
    context: GitContext,
    max_files: int = 10,
    max_lines: int = 200,
) -> Tuple[GitContext, dict]:
    """
    Applies safe-mode policies to GitContext:
    1. Masks sensitive patterns in diff and file names.
    2. Limits number of files (max_files) and diff lines (max_lines).
    
    Returns a new modified GitContext and an audit dictionary of applied actions.
    """
    # 1. Limit files
    original_files = list(context.changed_files)
    files_truncated = len(original_files) > max_files
    limited_files = original_files[:max_files]
    if files_truncated:
        limited_files.append(f"...외 {len(original_files) - max_files}개 파일 생략")

    # 2. Mask diff text
    masked_diff, replacements = mask_sensitive_text(context.diff_text)

    # 3. Truncate diff lines
    final_diff, lines_truncated = truncate_diff(masked_diff, max_lines=max_lines)

    diff_lines = [l for l in final_diff.splitlines() if l.strip()]

    new_context = replace(
        context,
        changed_files=limited_files,
        diff_text=final_diff,
        diff_line_count=len(diff_lines),
    )

    audit_info = {
        "sensitive_replacements": replacements,
        "files_truncated": files_truncated,
        "lines_truncated": lines_truncated,
        "max_files": max_files,
        "max_lines": max_lines,
    }

    return new_context, audit_info
