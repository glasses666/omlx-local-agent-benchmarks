from __future__ import annotations

import ast
import base64
import json
import re
from pathlib import Path
from typing import Any


def normalize_text(text: str) -> str:
    return text.strip().replace("\r\n", "\n").strip()


def extract_code(text: str) -> str:
    text = text.strip()
    fence = re.findall(r"```(?:python)?\n(.*?)```", text, flags=re.S)
    if fence:
        return fence[0].strip()
    return text


def json_score(output_text: str, expected_fields: dict[str, Any]) -> tuple[float, dict]:
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as exc:
        return 0.0, {"error": f"invalid_json: {exc}"}

    matched = 0
    for key, value in expected_fields.items():
        if payload.get(key) == value:
            matched += 1
    score = 100.0 * matched / max(len(expected_fields), 1)
    return score, {"parsed": payload, "matched_fields": matched}


def contains_score(output_text: str, needles: list[str], any_match: bool = False) -> tuple[float, dict]:
    lowered = output_text.lower()
    if any_match:
        matched = [item for item in needles if item.lower() in lowered]
        score = 100.0 if matched else 0.0
        return score, {"matched": matched}
    matched = [item for item in needles if item.lower() in lowered]
    score = 100.0 * len(matched) / max(len(needles), 1)
    return score, {"matched": matched}


def exact_score(output_text: str, expected: str) -> tuple[float, dict]:
    actual = normalize_text(output_text)
    return (100.0 if actual == expected else 0.0), {"actual": actual, "expected": expected}


def suffix_score(output_text: str, suffix: str) -> tuple[float, dict]:
    actual = normalize_text(output_text)
    return (100.0 if actual.endswith(suffix) else 0.0), {"actual": actual}


def line_count_prefix_score(output_text: str, prefix: str, count: int) -> tuple[float, dict]:
    lines = [line for line in normalize_text(output_text).split("\n") if line.startswith(prefix)]
    return (100.0 if len(lines) == count else 0.0), {"matching_lines": lines}


def word_count_contains_score(
    output_text: str,
    word_count: int | None = None,
    maximum_words: int | None = None,
    must_contain: list[str] | None = None,
) -> tuple[float, dict]:
    words = [item for item in re.split(r"\s+", normalize_text(output_text)) if item]
    score = 100.0
    if word_count is not None and len(words) != word_count:
        score = 0.0
    if maximum_words is not None and len(words) > maximum_words:
        score = 0.0
    contains = []
    if must_contain:
        lowered = output_text.lower()
        contains = [item for item in must_contain if item.lower() in lowered]
        if len(contains) != len(must_contain):
            score = min(score, 100.0 * len(contains) / max(len(must_contain), 1))
    return score, {"words": len(words), "contains": contains}


def min_length_score(output_text: str, minimum_chars: int) -> tuple[float, dict]:
    length = len(normalize_text(output_text))
    return (100.0 if length >= minimum_chars else 0.0), {"length": length}


def _validate_python_ast(code: str) -> None:
    tree = ast.parse(code)
    banned = (ast.Import, ast.ImportFrom, ast.With, ast.Try, ast.ClassDef, ast.Delete, ast.Global, ast.Nonlocal)
    for node in ast.walk(tree):
        if isinstance(node, banned):
            raise ValueError(f"unsupported_node:{type(node).__name__}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"open", "exec", "eval", "__import__"}:
            raise ValueError(f"unsafe_call:{node.func.id}")


def python_function_score(output_text: str, function_name: str, calls: list[dict]) -> tuple[float, dict]:
    code = extract_code(output_text)
    _validate_python_ast(code)

    namespace: dict[str, Any] = {"__builtins__": {"sorted": sorted, "max": max, "min": min, "sum": sum, "range": range, "len": len, "str": str, "int": int, "float": float, "dict": dict, "list": list}}
    exec(code, namespace, namespace)
    func = namespace.get(function_name)
    if not callable(func):
        return 0.0, {"error": f"missing_function:{function_name}"}

    passed = 0
    results = []
    for item in calls:
        actual = func(*item["args"])
        ok = actual == item["expected"]
        passed += int(ok)
        results.append({"args": item["args"], "expected": item["expected"], "actual": actual, "ok": ok})
    score = 100.0 * passed / max(len(calls), 1)
    return score, {"results": results}


def python_module_score(output_text: str, function_name: str, calls: list[dict]) -> tuple[float, dict]:
    return python_function_score(output_text, function_name, calls)


def score_task_output(task: dict, output_text: str) -> tuple[float, dict]:
    scoring = task["scoring"]
    scoring_type = scoring["type"]

    if scoring_type == "exact_text":
        return exact_score(output_text, scoring["expected"])
    if scoring_type == "suffix":
        return suffix_score(output_text, scoring["expected_suffix"])
    if scoring_type == "contains_all":
        return contains_score(output_text, scoring["must_contain"])
    if scoring_type == "contains_any":
        return contains_score(output_text, scoring["must_contain_any"], any_match=True)
    if scoring_type == "json_fields":
        return json_score(output_text, scoring["fields"])
    if scoring_type == "word_count_contains":
        return word_count_contains_score(
            output_text,
            word_count=scoring.get("word_count"),
            maximum_words=scoring.get("maximum_words"),
            must_contain=scoring.get("must_contain"),
        )
    if scoring_type == "max_words":
        return word_count_contains_score(output_text, maximum_words=scoring["maximum_words"])
    if scoring_type == "min_length":
        return min_length_score(output_text, scoring["minimum_chars"])
    if scoring_type == "line_count_prefix":
        return line_count_prefix_score(output_text, scoring["line_prefix"], scoring["count"])
    if scoring_type == "python_function":
        return python_function_score(output_text, scoring["function_name"], scoring["calls"])
    if scoring_type == "python_module":
        return python_module_score(output_text, scoring["function_name"], scoring["calls"])

    raise ValueError(f"Unsupported scoring type: {scoring_type}")


def image_file_to_data_uri(path: str) -> str:
    suffix = path.rsplit(".", 1)[-1].lower()
    mime = "image/png" if suffix == "png" else "image/jpeg"
    raw = Path(path).read_bytes()
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
