from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


ALLOWED_SOURCE_PATHS = [
    "issue_digest/core.py",
    "issue_digest/cli.py",
]

IGNORE_DIFF_PREFIXES = (
    ".pytest_cache/",
    "__pycache__/",
    ".ruff_cache/",
    "__hidden_tests__/",
)


def challenge_description() -> str:
    return (
        "Update this Python CLI project so it supports '--status open|closed|all' "
        "filtering and '--format text|json'. Keep default text output behavior "
        "compatible, sort results by priority descending then title ascending, "
        "do not add dependencies, do not rename the CLI module, and modify only "
        "issue_digest/core.py and issue_digest/cli.py."
    )


def read_repo_context(repo_dir: Path, relative_paths: list[str]) -> str:
    blocks = []
    for relative_path in relative_paths:
        source = repo_dir / relative_path
        blocks.append(
            f"FILE: {relative_path}\n```python\n{source.read_text(encoding='utf-8')}\n```"
        )
    return "\n\n".join(blocks)


def extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return json.loads(cleaned)

    start = cleaned.find("{")
    if start < 0:
        raise ValueError("No JSON object found in model output")

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(cleaned[start : index + 1])
    raise ValueError("Unterminated JSON object in model output")


def normalize_generated_files(payload: dict[str, Any]) -> dict[str, str]:
    files = payload.get("files")
    if isinstance(files, dict):
        return {str(path): str(content) for path, content in files.items()}
    if isinstance(files, list):
        normalized: dict[str, str] = {}
        for item in files:
            if not isinstance(item, dict) or "path" not in item or "content" not in item:
                raise ValueError("Each file item must include path and content")
            normalized[str(item["path"])] = str(item["content"])
        return normalized
    raise ValueError("files must be a dict or list of {path, content}")


def copy_repo_tree(source_dir: Path, target_dir: Path) -> None:
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)


def write_generated_files(repo_dir: Path, generated_files: dict[str, str]) -> None:
    for relative_path, content in generated_files.items():
        destination = repo_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


def changed_paths(template_dir: Path, repo_dir: Path) -> list[str]:
    paths: set[str] = set()
    for source in template_dir.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(template_dir).as_posix()
        if relative.startswith(IGNORE_DIFF_PREFIXES):
            continue
        candidate = repo_dir / relative
        if not candidate.exists():
            paths.add(relative)
            continue
        if source.read_bytes() != candidate.read_bytes():
            paths.add(relative)
    for candidate in repo_dir.rglob("*"):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(repo_dir).as_posix()
        if relative.startswith(IGNORE_DIFF_PREFIXES):
            continue
        if not (template_dir / relative).exists():
            paths.add(relative)
    return sorted(paths)


def constraint_violations(template_dir: Path, repo_dir: Path, allowed_paths: list[str]) -> list[str]:
    allowed = set(allowed_paths)
    violations = []
    for relative in changed_paths(template_dir, repo_dir):
        if relative not in allowed:
            violations.append(relative)
    return violations


def evaluate_patch_cleanliness(text: str) -> str:
    lowered = text.lower()
    if "<think>" in lowered or "thinking process" in lowered:
        return "thinking leak"
    if "```" in text or "here is" in lowered or "updated file" in lowered:
        return "prose mixed"
    return "clean"


def parse_test_counts(output: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "errors": 0}
    matches = re.findall(r"(\d+)\s+(passed|failed|error|errors)", output)
    if matches:
        for value, label in matches:
            number = int(value)
            if label == "passed":
                counts["passed"] = max(counts["passed"], number)
            elif label == "failed":
                counts["failed"] = max(counts["failed"], number)
            else:
                counts["errors"] = max(counts["errors"], number)
        return counts

    ran_match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    if not ran_match:
        return counts
    ran = int(ran_match.group(1))
    failed_match = re.search(r"FAILED\s+\((.*?)\)", output)
    if failed_match:
        details = failed_match.group(1)
        failure_count = re.search(r"failures=(\d+)", details)
        error_count = re.search(r"errors=(\d+)", details)
        counts["failed"] = int(failure_count.group(1)) if failure_count else 0
        counts["errors"] = int(error_count.group(1)) if error_count else 0
        counts["passed"] = max(ran - counts["failed"] - counts["errors"], 0)
        return counts
    if "\nOK" in output or output.strip().endswith("OK"):
        counts["passed"] = ran
    return counts


def run_unittest(repo_dir: Path, args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        ["python3", "-m", "unittest", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    combined = (completed.stdout or "") + (completed.stderr or "")
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "combined_output": combined,
        "counts": parse_test_counts(combined),
    }
