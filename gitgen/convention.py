"""
Convention configuration loader for customizing commit and PR templates.
Supports `.ai-gitgen.yml`, `.ai-gitgen.json`, or CLI overrides.
Zero-dependency YAML/JSON reader.
"""

from dataclasses import dataclass, field
import json
import os
from typing import List, Optional


@dataclass
class ConventionConfig:
    """Team convention configuration."""
    commit_types: List[str] = field(default_factory=lambda: [
        "feat", "fix", "docs", "style", "refactor", "test", "chore"
    ])
    language: str = "ko"  # ko, en
    max_commit_title_length: int = 50
    max_pr_title_length: int = 80
    include_commit_body: bool = True
    pr_sections: List[str] = field(default_factory=lambda: ["Why", "What", "How to Test"])
    custom_instructions: str = ""


def _parse_simple_yaml(text: str) -> dict:
    """
    Lightweight zero-dependency parser for simple YAML configurations.
    Handles basic key-value pairs and string lists.
    """
    result = {}
    current_key = None
    current_list = []

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("- ") and current_key:
            current_list.append(line[2:].strip().strip("\"'"))
            result[current_key] = current_list
            continue

        if ":" in line:
            parts = line.split(":", 1)
            k = parts[0].strip()
            v = parts[1].strip()

            if v:
                # Value is on same line
                v_clean = v.strip("\"'")
                if v_clean.lower() == "true":
                    result[k] = True
                elif v_clean.lower() == "false":
                    result[k] = False
                elif v_clean.isdigit():
                    result[k] = int(v_clean)
                else:
                    result[k] = v_clean
                current_key = None
            else:
                current_key = k
                current_list = []
                result[current_key] = current_list

    return result


def load_convention(config_path: Optional[str] = None) -> ConventionConfig:
    """
    Loads convention from specified path or looks for .ai-gitgen.yml / .ai-gitgen.json.
    Falls back to default convention if not found.
    """
    paths_to_check = []
    if config_path:
        paths_to_check.append(config_path)
    else:
        paths_to_check.extend([
            ".ai-gitgen.yml",
            ".ai-gitgen.yaml",
            ".ai-gitgen.json",
        ])

    data = {}
    for p in paths_to_check:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read()
                if p.endswith(".json"):
                    data = json.loads(content)
                else:
                    data = _parse_simple_yaml(content)
                break
            except Exception:
                pass

    if not data:
        return ConventionConfig()

    return ConventionConfig(
        commit_types=data.get("commit_types", ["feat", "fix", "docs", "style", "refactor", "test", "chore"]),
        language=data.get("language", "ko"),
        max_commit_title_length=int(data.get("max_commit_title_length", 50)),
        max_pr_title_length=int(data.get("max_pr_title_length", 80)),
        include_commit_body=bool(data.get("include_commit_body", True)),
        pr_sections=data.get("pr_sections", ["Why", "What", "How to Test"]),
        custom_instructions=str(data.get("custom_instructions", "")),
    )
