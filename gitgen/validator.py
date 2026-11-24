"""
Validator and post-processing module for commit and PR outputs.
Ensures outputs satisfy strict length and formatting rules without extra API calls.
"""

import re
from typing import List, Tuple


def _clean_markdown_fences(text: str) -> str:
    """Removes outer markdown code block fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove opening fence
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def validate_and_refine_commit(raw_text: str, max_title_len: int = 72) -> Tuple[str, List[str]]:
    """
    Validates and refines commit message output.
    Rules:
    - Title: exactly 1 line, <= max_title_len (72 chars max, 50 chars recommended).
    - Blank line after title.
    - Body: 1~3 bullets if body exists.
    Returns (refined_commit_message, warnings).
    """
    warnings: List[str] = []
    text = _clean_markdown_fences(raw_text)
    lines = [l.strip() for l in text.splitlines()]

    # Filter leading empty lines or meta intro
    filtered_lines: List[str] = []
    for line in lines:
        if not filtered_lines and (
            line.lower().startswith("commit message") or
            line.lower().startswith("커밋 메시지") or
            line.startswith("---")
        ):
            continue
        filtered_lines.append(line)

    if not filtered_lines:
        title = "chore: 변경 사항 적용"
        body_lines = ["- 작업 내역 업데이트"]
        warnings.append("AI 응답이 비어 있어 기본 커밋 메시지로 대체되었습니다.")
        return f"{title}\n\n" + "\n".join(body_lines), warnings

    # Title is the first line
    title = filtered_lines[0]
    # Remove leading '# ' or prefixes if present
    title = re.sub(r"^#+\s*", "", title).strip()

    # Title length check
    if len(title) > max_title_len:
        warnings.append(f"커밋 제목이 최대 길이({max_title_len}자)를 초과하여 자릅니다: {len(title)}자")
        title = title[:max_title_len - 3].rstrip() + "..."

    # Process body
    body_raw = filtered_lines[1:]
    # Remove leading blank lines from body
    while body_raw and not body_raw[0]:
        body_raw.pop(0)

    formatted_bullets: List[str] = []
    for line in body_raw:
        if not line:
            continue
        # If line starts with bullet marker, standardize to "- "
        if line.startswith(("- ", "* ", "• ")):
            clean_item = line[2:].strip()
            formatted_bullets.append(f"- {clean_item}")
        elif re.match(r"^\d+\.\s+", line):
            clean_item = re.sub(r"^\d+\.\s+", "", line).strip()
            formatted_bullets.append(f"- {clean_item}")
        else:
            formatted_bullets.append(f"- {line}")

    # Minimum quality check: if body exists, ensure at least 1 bullet point
    if not formatted_bullets:
        final_message = title
    else:
        final_message = f"{title}\n\n" + "\n".join(formatted_bullets)

    return final_message, warnings


def validate_and_refine_pr(raw_text: str, max_title_len: int = 80) -> Tuple[str, str, List[str]]:
    """
    Validates and refines Pull Request title and body.
    Rules:
    - Title: 1 line, <= max_title_len (80 chars max).
    - Body: must contain headers `## Why`, `## What`, `## How to Test`.
    - Each section must have at least 1 bullet point.
    Returns (refined_title, refined_body, warnings).
    """
    warnings: List[str] = []
    text = _clean_markdown_fences(raw_text)
    lines = text.splitlines()

    # Find the title (first non-empty line)
    title = ""
    body_start_idx = 0
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue
        # Check if line is title
        if line_clean.lower().startswith("pr title") or line_clean.lower().startswith("제목:"):
            title = re.sub(r"^(?:pr title|제목)\s*[:\-]\s*", "", line_clean, flags=re.IGNORECASE).strip()
            body_start_idx = idx + 1
            break
        elif not line_clean.startswith("#"):
            title = line_clean
            body_start_idx = idx + 1
            break
        elif line_clean.startswith("#") and not any(h in line_clean for h in ["Why", "What", "How to Test"]):
            title = re.sub(r"^#+\s*", "", line_clean).strip()
            body_start_idx = idx + 1
            break

    if not title:
        title = "feat: 변경 사항 업데이트"
        warnings.append("PR 제목을 찾을 수 없어 기본 제목으로 대체되었습니다.")

    # Clean title
    title = re.sub(r"^#+\s*", "", title).strip()
    if len(title) > max_title_len:
        warnings.append(f"PR 제목이 {max_title_len}자를 초과하여 자릅니다: {len(title)}자")
        title = title[:max_title_len - 3].rstrip() + "..."

    # Parse body into sections
    body_raw = "\n".join(lines[body_start_idx:]).strip()

    sections = {
        "Why": [],
        "What": [],
        "How to Test": [],
    }

    current_section = None
    for line in body_raw.splitlines():
        line_s = line.strip()
        # Check section header
        matched_header = None
        for sec in ["Why", "What", "How to Test"]:
            if re.search(rf"^#+\s*{re.escape(sec)}", line_s, re.IGNORECASE):
                matched_header = sec
                break

        if matched_header:
            current_section = matched_header
            continue

        if current_section:
            if line_s.startswith(("- ", "* ", "• ")):
                sections[current_section].append(f"- {line_s[2:].strip()}")
            elif re.match(r"^\d+\.\s+", line_s):
                clean_bullet = re.sub(r"^\d+\.\s+", "", line_s).strip()
                sections[current_section].append(f"- {clean_bullet}")
            elif line_s:
                sections[current_section].append(f"- {line_s}")

    # Fallbacks for missing sections or empty bullets
    if not sections["Why"]:
        sections["Why"] = ["- 변경 사항 반영 및 기능 개선"]
        warnings.append("## Why 섹션이 누락되었거나 불릿이 없어 기본 항목을 보완했습니다.")

    if not sections["What"]:
        sections["What"] = ["- 주요 로직 수정 및 파일 변경 사항 반영"]
        warnings.append("## What 섹션이 누락되었거나 불릿이 없어 기본 항목을 보완했습니다.")

    if not sections["How to Test"]:
        sections["How to Test"] = ["- CLI 실행 및 변경 기능 동작 확인"]
        warnings.append("## How to Test 섹션이 누락되었거나 불릿이 없어 기본 항목을 보완했습니다.")

    # Assemble formatted body
    body_parts = [
        "## Why",
        "\n".join(sections["Why"]),
        "",
        "## What",
        "\n".join(sections["What"]),
        "",
        "## How to Test",
        "\n".join(sections["How to Test"]),
    ]

    refined_body = "\n".join(body_parts).strip()
    return title, refined_body, warnings
