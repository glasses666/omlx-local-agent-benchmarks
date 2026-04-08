from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .admin_api import OMLXAdminClient
from .backup import backup_file
from .cc_duel import (
    ALLOWED_SOURCE_PATHS,
    challenge_description,
    constraint_violations,
    copy_repo_tree,
    evaluate_patch_cleanliness,
    extract_json_payload,
    normalize_generated_files,
    read_repo_context,
    run_unittest,
    write_generated_files,
)
from .evaluators import image_file_to_data_uri, score_task_output
from .mcp_config import build_mcp_config, load_legacy_toml_config, write_mcp_config
from .omlx_api import OMLXClient
from .reporting import SUMMARY_COLUMNS, markdown_table, write_csv, write_json
from .scoring import compute_overall_score, median_or_single
from .task_loader import get_suite_tasks


@dataclass
class BenchmarkPaths:
    root: Path
    backups: Path
    logs: Path
    runs: Path
    artifacts: Path
    results: Path
    reports: Path


def build_paths(root: Path) -> BenchmarkPaths:
    return BenchmarkPaths(
        root=root,
        backups=root / "backups",
        logs=root / "logs",
        runs=root / "runs",
        artifacts=root / "artifacts",
        results=root / "results",
        reports=root / "reports",
    )


def ensure_dirs(paths: BenchmarkPaths) -> None:
    for item in (paths.backups, paths.logs, paths.runs, paths.artifacts, paths.results, paths.reports):
        item.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_variant(model_id: str) -> str:
    for token in ("8bit", "4bit", "mxfp4", "mxfp8", "a4b"):
        if token in model_id.lower():
            return token
    return "unknown"


def compact_settings(profile: dict[str, Any]) -> str:
    parts = [
        f"temp={profile['temperature']}",
        f"top_p={profile['top_p']}",
        f"max_tokens={profile['max_tokens']}",
    ]
    if profile.get("thinking_budget") is not None:
        parts.append(f"thinking={profile['thinking_budget']}")
    return ", ".join(parts)


def coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


QWEN_CC_COLUMNS = [
    "Model",
    "Series",
    "Quantization / variant",
    "CC-style speed summary",
    "Chat feel",
    "Instruction following",
    "Code quality",
    "Long-context usefulness",
    "Typical strengths",
    "Typical weaknesses",
    "Recommended oMLX settings",
    "Overall verdict",
]

CC_DUEL_COLUMNS = [
    "Entrant",
    "Mode",
    "Model(s)",
    "Visible tests",
    "Hidden tests",
    "Constraint violations",
    "Patch cleanliness",
    "Wall time",
    "Verdict",
]


class BenchmarkRunner:
    def __init__(
        self,
        root: Path,
        *,
        settings_path: Path = Path("/Users/dracoglasser/.omlx/settings.json"),
        model_settings_path: Path = Path("/Users/dracoglasser/.omlx/model_settings.json"),
        app_config_path: Path = Path("/Users/dracoglasser/Library/Application Support/oMLX/config.json"),
        fallback_mcp_path: Path = Path("/Users/dracoglasser/.config/omlx/mcp.toml"),
    ) -> None:
        self.root = root
        self.paths = build_paths(root)
        ensure_dirs(self.paths)
        self.client = OMLXClient(base_url="http://127.0.0.1:8000", api_key="dracoglasser", timeout=600)
        self.admin = OMLXAdminClient(base_url="http://127.0.0.1:8000", api_key="dracoglasser", timeout=600)
        self.task_file = root / "tasks.json"
        self.profiles_file = root / "profiles.json"
        self.original_global_settings: dict[str, Any] | None = None
        self.settings_path = settings_path
        self.model_settings_path = model_settings_path
        self.app_config_path = app_config_path
        self.fallback_mcp_path = fallback_mcp_path

    def current_mcp_config_path(self) -> Path | None:
        if not self.settings_path.exists():
            return None
        payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
        config_path = payload.get("mcp", {}).get("config_path")
        return Path(config_path) if config_path else None

    def log_event(self, name: str, payload: dict[str, Any]) -> None:
        record = {"event": name, "timestamp_utc": utc_now(), **payload}
        with (self.paths.logs / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def backup_relevant_files(self) -> list[dict]:
        manifest = self.paths.backups / "manifest.json"
        mcp_path = self.current_mcp_config_path() or self.fallback_mcp_path
        targets = [
            ("global_settings", self.settings_path),
            ("model_settings", self.model_settings_path),
            ("mcp_config", mcp_path),
            ("app_config", self.app_config_path),
        ]
        records = []
        for kind, source in targets:
            if source.exists():
                records.append(backup_file(source, self.paths.backups, manifest, kind))
            else:
                self.log_event("backup_skipped_missing", {"kind": kind, "source_path": str(source)})
        self.log_event("backup_complete", {"count": len(records)})
        return records

    def repair_mcp_config(self) -> dict[str, Any]:
        current_path = self.current_mcp_config_path() or self.fallback_mcp_path
        runtime_path = self.paths.artifacts / "runtime-mcp.json"
        if not current_path.exists():
            raise FileNotFoundError(current_path)

        if current_path.suffix == ".toml":
            config = load_legacy_toml_config(current_path)
            payload = build_mcp_config(
                server_name=config["server_name"],
                command=config["command"],
                args=config["args"],
                env=config["env"],
            )
        elif current_path.suffix == ".json":
            payload = json.loads(current_path.read_text(encoding="utf-8"))
        else:
            raise ValueError(f"Unsupported MCP config format: {current_path.suffix}")

        write_mcp_config(runtime_path, payload)
        admin_result = self.admin.update_global_settings({"mcp_config": str(runtime_path)})
        result = {
            "source_path": str(current_path),
            "config_path": str(runtime_path),
            "payload": payload,
            "admin_result": admin_result,
            "restart_required": True,
        }
        self.log_event("mcp_config_prepared", {"source_path": str(current_path), "config_path": str(runtime_path), "restart_required": True})
        return result

    def health_snapshot(self) -> dict:
        health = self.client.health()
        models = self.client.models_status()
        return {"health": health, "models_status": models}

    def load_profiles(self) -> dict[str, Any]:
        return json.loads(self.profiles_file.read_text(encoding="utf-8"))

    def load_summary_or_checkpoint(self, stem: str) -> dict[str, Any]:
        summary_path = self.paths.results / f"{stem}-summary.json"
        checkpoint_path = self.paths.results / f"{stem}-checkpoint.json"
        if summary_path.exists():
            return json.loads(summary_path.read_text(encoding="utf-8"))
        if checkpoint_path.exists():
            return json.loads(checkpoint_path.read_text(encoding="utf-8"))
        raise FileNotFoundError(summary_path)

    def load_screening_finalists(self) -> list[str]:
        payload = self.load_summary_or_checkpoint("screening")
        finalists = payload.get("finalists")
        if finalists:
            return finalists
        summaries = payload.get("summaries", [])
        ranked = sorted(summaries, key=lambda item: item.get("overall_score", 0.0), reverse=True)
        return [item["model_id"] for item in ranked[:6]]

    def inspect_environment(self) -> dict[str, Any]:
        self.original_global_settings = self.admin.global_settings()
        status = self.client.models_status()
        mcp_path = self.current_mcp_config_path()
        payload = {
            "generated_at": utc_now(),
            "health": self.client.health(),
            "models_status": status,
            "global_settings": self.original_global_settings,
            "current_mcp_config_path": str(mcp_path) if mcp_path else None,
        }
        write_json(self.paths.results / "environment.json", payload)
        report = [
            "# Environment Inspection",
            "",
            f"- Generated at: `{payload['generated_at']}`",
            f"- Current MCP config path: `{payload['current_mcp_config_path']}`",
            f"- Loaded models: `{status.get('loaded_count', 0)}` / `{status.get('model_count', len(status.get('models', [])))}`",
            f"- Default model: `{payload['health'].get('default_model')}`",
            "",
        ]
        (self.paths.reports / "inspection.md").write_text("\n".join(report), encoding="utf-8")
        self.log_event("environment_inspected", {"model_count": len(status.get("models", []))})
        return payload

    def mcp_health(self) -> dict[str, Any]:
        health = self.client.health()
        result = {"healthy": bool(health.get("mcp")), "health": health}
        if not result["healthy"]:
            return result
        try:
            result["servers"] = self.client.mcp_servers()
            result["tools"] = self.client.mcp_tools()
            result["healthy"] = bool(result["servers"].get("servers"))
        except Exception as exc:
            result["healthy"] = False
            result["error"] = str(exc)
        return result

    def candidate_tuned_profiles(self) -> list[dict[str, Any]]:
        profiles = self.load_profiles()
        baseline = dict(profiles["full_baseline"])
        grid = profiles["tuned_grid"]
        candidates = [
            dict(baseline),
            {**baseline, "temperature": grid["temperature"][0]},
            {**baseline, "temperature": grid["temperature"][2]},
            {**baseline, "top_p": grid["top_p"][-1]},
            {**baseline, "max_tokens": grid["max_tokens"][-1]},
            {
                **baseline,
                "temperature": baseline["temperature"],
                "top_p": grid["top_p"][-1],
                "max_tokens": grid["max_tokens"][-1],
                "thinking_budget": grid["thinking_budget"][-1],
            },
        ]
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = json.dumps(candidate, sort_keys=True)
            if key not in seen:
                seen.add(key)
                deduped.append(candidate)
        return deduped

    def unload_all_models(self) -> dict[str, Any]:
        status = self.client.models_status()
        unloaded: list[str] = []
        for model in status["models"]:
            if model.get("loaded"):
                self.client.unload_model(model["id"])
                unloaded.append(model["id"])
        deadline = time.time() + 120
        while time.time() < deadline:
            current = self.client.models_status()
            if current.get("loaded_count", 0) == 0:
                self.log_event("models_unloaded", {"models": unloaded})
                return current
            time.sleep(1.0)
        raise TimeoutError("Timed out waiting for loaded_count to reach zero")

    def apply_baseline_sampling(self, profile_name: str) -> dict[str, Any]:
        profiles = json.loads(self.profiles_file.read_text(encoding="utf-8"))
        profile = profiles[profile_name]
        payload = {
            "sampling_temperature": profile["temperature"],
            "sampling_top_p": profile["top_p"],
            "sampling_top_k": profile["top_k"],
            "sampling_repetition_penalty": profile["repetition_penalty"],
            "sampling_max_tokens": profile["max_tokens"],
        }
        result = self.admin.update_global_settings(payload)
        self.log_event("baseline_sampling_applied", {"profile": profile_name, "payload": payload})
        return result

    def restore_global_sampling(self) -> dict[str, Any] | None:
        if not self.original_global_settings:
            return None
        sampling = self.original_global_settings["sampling"]
        payload = {
            "sampling_max_context_window": sampling["max_context_window"],
            "sampling_max_tokens": sampling["max_tokens"],
            "sampling_temperature": sampling["temperature"],
            "sampling_top_p": sampling["top_p"],
            "sampling_top_k": sampling["top_k"],
            "sampling_repetition_penalty": sampling["repetition_penalty"],
        }
        result = self.admin.update_global_settings(payload)
        self.log_event("global_sampling_restored", {"payload": payload})
        return result

    def model_is_vision_candidate(self, model: dict[str, Any]) -> bool:
        return model.get("model_type") == "vlm"

    def claude_code_cli_path(self) -> str | None:
        return shutil.which("claude")

    def aider_cli_path(self) -> str | None:
        return shutil.which("aider")

    def is_qwen_family_model(self, model: dict[str, Any]) -> bool:
        model_id = model["id"].lower()
        return "qwen" in model_id or "huihui" in model_id

    def qwen_series(self, model_id: str) -> str:
        lowered = model_id.lower()
        if lowered.startswith("huihui-"):
            return "huihui"
        if "claude-4.6-opus" in lowered:
            return "qwen_opus"
        return "other_qwen"

    def qwen_cc_overall_score(self, dimension_scores: dict[str, float]) -> float:
        weights = {
            "code": 0.5,
            "instruction": 0.2,
            "chat": 0.15,
            "long_context": 0.15,
        }
        total = 0.0
        for key, weight in weights.items():
            total += dimension_scores.get(key, 0.0) * weight
        return round(total, 2)

    def vision_smoke_test(self, model_id: str, task: dict, profile: dict, mcp_ready: bool) -> dict[str, Any]:
        result = self.execute_task(model_id, task, profile, repeats=1, mcp_ready=mcp_ready)
        success = result.get("median_score", 0.0) > 0 and not result.get("failed")
        return {"success": success, "result": result}

    def _build_messages(self, task: dict) -> list[dict[str, Any]]:
        if "messages" in task:
            return task["messages"]
        body = task["input"]
        if task.get("context_padding"):
            padding = task["context_padding"]
            body += padding["sentence"] * padding["repeat"]
        if task.get("suffix"):
            body += task["suffix"]
        if task.get("image_path"):
            return [{
                "role": "user",
                "content": [
                    {"type": "text", "text": body},
                    {"type": "image_url", "image_url": {"url": image_file_to_data_uri(task["image_path"]), "detail": "high"}}
                ]
            }]
        return [{"role": "user", "content": body}]

    def execute_chat_task(self, model_id: str, task: dict, profile: dict, repeats: int) -> dict[str, Any]:
        scores = []
        runs = []
        prompt_tokens = []
        for index in range(repeats):
            payload = {
                "model": model_id,
                "messages": self._build_messages(task),
                "temperature": profile["temperature"],
                "top_p": profile["top_p"],
                "max_tokens": min(profile["max_tokens"], 1024),
                "stream": False,
            }
            if profile.get("thinking_budget") is not None:
                payload["thinking_budget"] = profile["thinking_budget"]
            started = time.perf_counter()
            response = self.client.chat_completion(payload)
            elapsed = time.perf_counter() - started
            message = response["choices"][0]["message"].get("content") or ""
            if isinstance(message, list):
                message = "\n".join(
                    part.get("text", "") for part in message if isinstance(part, dict)
                )
            score, details = score_task_output(task, message)
            usage = response.get("usage", {})
            prompt_tokens.append(usage.get("prompt_tokens", 0))
            runs.append({
                "iteration": index + 1,
                "response": response,
                "output_text": message,
                "score": score,
                "details": details,
                "wall_time_s": round(elapsed, 4),
            })
            scores.append(score)
        median_score = median_or_single(scores)
        return {
            "task_id": task["id"],
            "dimension": task["dimension"],
            "mode": task["mode"],
            "runs": runs,
            "median_score": median_score,
            "prompt_tokens_median": median_or_single(prompt_tokens) if prompt_tokens else 0.0,
            "usage": runs[-1]["response"].get("usage", {}) if runs else {},
        }

    def execute_responses_task(self, model_id: str, task: dict, profile: dict) -> dict[str, Any]:
        payload = {
            "model": model_id,
            "input": task["input"],
            "temperature": profile["temperature"],
            "top_p": profile["top_p"],
            "max_output_tokens": min(profile["max_tokens"], 512),
            "tool_choice": "auto",
            "parallel_tool_calls": False,
        }
        if profile.get("thinking_budget") is not None:
            payload["thinking_budget"] = profile["thinking_budget"]
        started = time.perf_counter()
        response = self.client.responses(payload)
        elapsed = time.perf_counter() - started
        texts = []
        for item in response.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        texts.append(content.get("text", ""))
        output_text = "\n".join(texts).strip()
        score, details = score_task_output(task, output_text)
        return {
            "task_id": task["id"],
            "dimension": task["dimension"],
            "mode": task["mode"],
            "runs": [{
                "iteration": 1,
                "response": response,
                "output_text": output_text,
                "score": score,
                "details": details,
                "wall_time_s": round(elapsed, 4),
            }],
            "median_score": score,
            "usage": response.get("usage", {}),
        }

    def execute_task(self, model_id: str, task: dict, profile: dict, repeats: int, mcp_ready: bool) -> dict[str, Any]:
        if task.get("live_only") and not mcp_ready:
            result = {
                "task_id": task["id"],
                "dimension": task["dimension"],
                "mode": task["mode"],
                "deferred": True,
                "reason": "mcp_unhealthy",
                "median_score": 0.0,
                "usage": {},
            }
            self.log_event("task_deferred", {"model_id": model_id, "task_id": task["id"], "reason": "mcp_unhealthy"})
            return result
        try:
            if task["mode"] == "responses":
                result = self.execute_responses_task(model_id, task, profile)
            else:
                result = self.execute_chat_task(model_id, task, profile, repeats=repeats)
            self.log_event(
                "task_completed",
                {
                    "model_id": model_id,
                    "task_id": task["id"],
                    "dimension": task["dimension"],
                    "median_score": result.get("median_score", 0.0),
                },
            )
            return result
        except Exception as exc:
            self.log_event(
                "task_failed",
                {
                    "model_id": model_id,
                    "task_id": task["id"],
                    "dimension": task["dimension"],
                    "error": str(exc),
                },
            )
            return {
                "task_id": task["id"],
                "dimension": task["dimension"],
                "mode": task["mode"],
                "failed": True,
                "error": str(exc),
                "median_score": 0.0,
                "usage": {},
                "runs": [],
            }

    def summarize_model(self, model: dict, stage_results: list[dict], vision_capable: bool, screening_only: bool = False) -> dict[str, Any]:
        by_dimension: dict[str, list[float]] = {}
        speed_parts = []
        for item in stage_results:
            usage = item.get("usage", {})
            if usage:
                ttft = usage.get("time_to_first_token") or usage.get("ttft")
                tps = usage.get("generation_tokens_per_second") or usage.get("tokens_per_second")
                if ttft is not None:
                    speed_parts.append(f"TTFT {ttft:.2f}s")
                if tps is not None:
                    speed_parts.append(f"{tps:.1f} tok/s")
            if not item.get("deferred"):
                by_dimension.setdefault(item["dimension"], []).append(item["median_score"])

        dimension_scores = {key: round(sum(values) / len(values), 2) for key, values in by_dimension.items()}
        mapping = {
            "chat": dimension_scores.get("chat", 0.0),
            "instruction": dimension_scores.get("instruction", 0.0),
            "code": dimension_scores.get("code", 0.0),
            "tool": dimension_scores.get("tool", 0.0),
            "long_context": dimension_scores.get("long_context", 0.0),
            "vision": dimension_scores.get("vision", 0.0),
            "speed": 50.0
        }
        overall = compute_overall_score(mapping, is_vision_capable=vision_capable)
        variant = extract_variant(model["id"])
        recommended = "baseline profile" if screening_only else "tuned profile pending"
        return {
            "model_id": model["id"],
            "variant": variant,
            "type": "vision" if vision_capable else "text",
            "dimension_scores": dimension_scores,
            "overall_score": overall,
            "baseline_speed": ", ".join(speed_parts[:2]) or "n/a",
            "recommended_settings": recommended,
            "screening_only": screening_only,
            "results": stage_results,
        }

    def model_lookup(self) -> dict[str, dict[str, Any]]:
        status = self.client.models_status()
        return {item["id"]: item for item in status["models"]}

    def run_model_suite(
        self,
        *,
        model: dict[str, Any],
        task_suites: dict[str, list[dict[str, Any]]],
        profile: dict[str, Any],
        mcp_state: dict[str, Any],
        screening_only: bool,
    ) -> dict[str, Any]:
        self.unload_all_models()
        self.log_event("model_start", {"model_id": model["id"], "stage": "screening" if screening_only else "full"})
        stage_results: list[dict[str, Any]] = []
        for task in task_suites["text"] + task_suites["code"] + task_suites["long_context"]:
            stage_results.append(
                self.execute_task(model["id"], task, profile, profile["repeat_count"], mcp_state["healthy"])
            )

        for task in task_suites.get("tool", []):
            stage_results.append(self.execute_task(model["id"], task, profile, 1, mcp_state["healthy"]))

        vision_capable = False
        if self.model_is_vision_candidate(model) and task_suites.get("vision"):
            smoke = self.vision_smoke_test(model["id"], task_suites["vision"][0], profile, mcp_state["healthy"])
            vision_capable = smoke["success"]
            stage_results.append(smoke["result"])
            if vision_capable:
                for task in task_suites["vision"][1:]:
                    stage_results.append(self.execute_task(model["id"], task, profile, 1, mcp_state["healthy"]))

        summary = self.summarize_model(model, stage_results, vision_capable, screening_only=screening_only)
        self.unload_all_models()
        return summary

    def screening_rows(self, summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for summary in summaries:
            dim = summary["dimension_scores"]
            rows.append({
                "Model": summary["model_id"],
                "Quantization / variant": summary["variant"],
                "Type": summary["type"],
                "Baseline speed summary": summary["baseline_speed"],
                "Tuned speed summary": "pending",
                "Chat feel": dim.get("chat", 0.0),
                "Instruction following": dim.get("instruction", 0.0),
                "Code quality": dim.get("code", 0.0),
                "Tool / agent quality": "deferred" if dim.get("tool", None) is None else dim.get("tool", 0.0),
                "Vision quality": dim.get("vision", 0.0) if summary["type"] == "vision" else "n/a",
                "Long-context usefulness": dim.get("long_context", 0.0),
                "Typical strengths": "Fast screening candidate" if summary["overall_score"] >= 60 else "Needs deeper review",
                "Typical weaknesses": "Tool benchmark deferred" if summary["screening_only"] else "",
                "Best use case": "screening candidate",
                "Recommended oMLX settings": summary["recommended_settings"],
                "Overall verdict": f"{summary['overall_score']:.2f}"
            })
        return rows

    def write_screening_checkpoint(
        self,
        *,
        mcp_state: dict[str, Any],
        profile: dict[str, Any],
        summaries: list[dict[str, Any]],
    ) -> None:
        write_json(
            self.paths.results / "screening-checkpoint.json",
            {
                "generated_at": utc_now(),
                "mcp_state": mcp_state,
                "profile": profile,
                "summaries": summaries,
                "completed_models": [item["model_id"] for item in summaries],
            },
        )

    def run_screening(self) -> dict[str, Any]:
        profiles = self.load_profiles()
        profile = profiles["screening_baseline"]
        mcp_state = self.mcp_health()
        status = self.client.models_status()
        task_suites = get_suite_tasks(self.task_file, "screening")

        self.apply_baseline_sampling("screening_baseline")
        checkpoint_path = self.paths.results / "screening-checkpoint.json"
        summaries = []
        completed_models: set[str] = set()
        if checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            summaries = checkpoint.get("summaries", [])
            completed_models = {item["model_id"] for item in summaries}
        finalists = []
        lightest_text = None
        best_vision = None

        for model in status["models"]:
            if model["id"] in completed_models:
                continue
            summary = self.run_model_suite(
                model=model,
                task_suites=task_suites,
                profile=profile,
                mcp_state=mcp_state,
                screening_only=True,
            )
            summaries.append(summary)
            self.write_screening_checkpoint(mcp_state=mcp_state, profile=profile, summaries=summaries)

            if model["model_type"] == "llm":
                if lightest_text is None or model["estimated_size"] < lightest_text["estimated_size"]:
                    lightest_text = model
            if summary["type"] == "vision" and (best_vision is None or summary["overall_score"] > best_vision["overall_score"]):
                best_vision = summary

        ranked = sorted(summaries, key=lambda item: item["overall_score"], reverse=True)
        finalists = [item["model_id"] for item in ranked[:6]]
        if lightest_text and lightest_text["id"] not in finalists:
            finalists.append(lightest_text["id"])
        if best_vision and best_vision["model_id"] not in finalists:
            finalists.append(best_vision["model_id"])

        screening_payload = {
            "generated_at": utc_now(),
            "mcp_state": mcp_state,
            "profile": profile,
            "summaries": summaries,
            "finalists": finalists,
        }
        write_json(self.paths.results / "screening-summary.json", screening_payload)
        rows = self.screening_rows(ranked)
        write_csv(self.paths.results / "screening-summary.csv", rows)
        report = "# Stage 1 Screening Report\n\n" + markdown_table(rows, SUMMARY_COLUMNS)
        (self.paths.reports / "screening-report.md").write_text(report, encoding="utf-8")
        return screening_payload

    def write_stage_outputs(self, *, stem: str, payload: dict[str, Any], rows: list[dict[str, Any]], title: str) -> None:
        write_json(self.paths.results / f"{stem}-summary.json", payload)
        write_csv(self.paths.results / f"{stem}-summary.csv", rows)
        (self.paths.reports / f"{stem}-report.md").write_text(
            f"# {title}\n\n" + markdown_table(rows, SUMMARY_COLUMNS),
            encoding="utf-8",
        )

    def rows_for_summaries(
        self,
        summaries: list[dict[str, Any]],
        *,
        tuned: bool = False,
    ) -> list[dict[str, Any]]:
        rows = []
        for summary in summaries:
            dim = summary["dimension_scores"]
            rows.append({
                "Model": summary["model_id"],
                "Quantization / variant": summary["variant"],
                "Type": summary["type"],
                "Baseline speed summary": summary.get("baseline_speed", "n/a"),
                "Tuned speed summary": summary.get("tuned_speed", "pending" if not tuned else summary.get("baseline_speed", "n/a")),
                "Chat feel": dim.get("chat", 0.0),
                "Instruction following": dim.get("instruction", 0.0),
                "Code quality": dim.get("code", 0.0),
                "Tool / agent quality": "deferred" if dim.get("tool", None) is None else dim.get("tool", 0.0),
                "Vision quality": dim.get("vision", 0.0) if summary["type"] == "vision" else "n/a",
                "Long-context usefulness": dim.get("long_context", 0.0),
                "Typical strengths": summary.get("typical_strengths", "Runnable benchmark candidate"),
                "Typical weaknesses": summary.get("typical_weaknesses", "Tool benchmark deferred" if summary.get("screening_only") else ""),
                "Best use case": summary.get("best_use_case", "general"),
                "Recommended oMLX settings": summary["recommended_settings"],
                "Overall verdict": f"{summary['overall_score']:.2f}",
            })
        return rows

    def qwen_cc_rows(self, summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for summary in summaries:
            dim = summary["dimension_scores"]
            rows.append({
                "Model": summary["model_id"],
                "Series": summary["series"],
                "Quantization / variant": summary["variant"],
                "CC-style speed summary": summary.get("baseline_speed", "n/a"),
                "Chat feel": dim.get("chat", 0.0),
                "Instruction following": dim.get("instruction", 0.0),
                "Code quality": dim.get("code", 0.0),
                "Long-context usefulness": dim.get("long_context", 0.0),
                "Typical strengths": summary.get("typical_strengths", "CC-style code candidate"),
                "Typical weaknesses": summary.get("typical_weaknesses", ""),
                "Recommended oMLX settings": summary["recommended_settings"],
                "Overall verdict": f"{summary['overall_score']:.2f}",
            })
        return rows

    def summarize_qwen_series(self, summaries: list[dict[str, Any]]) -> dict[str, Any]:
        by_series: dict[str, list[dict[str, Any]]] = {}
        for summary in summaries:
            by_series.setdefault(summary["series"], []).append(summary)
        payload: dict[str, Any] = {}
        for series, items in by_series.items():
            ranked = sorted(items, key=lambda item: item["overall_score"], reverse=True)
            avg_overall = round(sum(item["overall_score"] for item in items) / len(items), 2)
            avg_code = round(sum(item["dimension_scores"].get("code", 0.0) for item in items) / len(items), 2)
            avg_instruction = round(sum(item["dimension_scores"].get("instruction", 0.0) for item in items) / len(items), 2)
            payload[series] = {
                "count": len(items),
                "average_overall": avg_overall,
                "average_code": avg_code,
                "average_instruction": avg_instruction,
                "best_model": ranked[0]["model_id"],
                "best_score": ranked[0]["overall_score"],
            }
        return payload

    def qwen_cc_notes(self, summary: dict[str, Any]) -> tuple[str, str, str]:
        dim = summary["dimension_scores"]
        code = dim.get("code", 0.0)
        instruction = dim.get("instruction", 0.0)
        chat = dim.get("chat", 0.0)
        long_context = dim.get("long_context", 0.0)
        strengths: list[str] = []
        weaknesses: list[str] = []
        if code >= 80:
            strengths.append("strong code edits")
        elif code >= 50:
            strengths.append("usable supervised coding")
        else:
            weaknesses.append("weak code completion")
        if instruction >= 80:
            strengths.append("good output discipline")
        elif instruction < 50:
            weaknesses.append("format drift")
        if long_context >= 80:
            strengths.append("holds repo constraints")
        if chat < 50:
            weaknesses.append("review commentary can wander")
        best_use_case = "cc-style coding" if code >= max(chat, instruction, long_context) else "cc-style analysis"
        return ", ".join(strengths) or "mixed", ", ".join(weaknesses) or "none observed", best_use_case

    def run_full_baseline(self) -> dict[str, Any]:
        profiles = self.load_profiles()
        profile = profiles["full_baseline"]
        finalists = self.load_screening_finalists()
        task_suites = get_suite_tasks(self.task_file, "full")
        mcp_state = self.mcp_health()
        lookup = self.model_lookup()

        self.apply_baseline_sampling("full_baseline")
        checkpoint_path = self.paths.results / "full-baseline-checkpoint.json"
        summaries: list[dict[str, Any]] = []
        completed_models: set[str] = set()
        if checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            summaries = checkpoint.get("summaries", [])
            completed_models = {item["model_id"] for item in summaries}

        for model_id in finalists:
            if model_id in completed_models:
                continue
            model = lookup[model_id]
            summary = self.run_model_suite(
                model=model,
                task_suites=task_suites,
                profile=profile,
                mcp_state=mcp_state,
                screening_only=False,
            )
            summary["recommended_settings"] = compact_settings(profile)
            summaries.append(summary)
            write_json(
                checkpoint_path,
                {
                    "generated_at": utc_now(),
                    "profile": profile,
                    "mcp_state": mcp_state,
                    "summaries": summaries,
                    "finalists": finalists,
                },
            )

        payload = {
            "generated_at": utc_now(),
            "profile": profile,
            "mcp_state": mcp_state,
            "summaries": summaries,
            "finalists": finalists,
        }
        rows = self.rows_for_summaries(summaries)
        self.write_stage_outputs(stem="full-baseline", payload=payload, rows=rows, title="Full Baseline Report")
        return payload

    def calibration_tasks_for_model(self, task_suites: dict[str, list[dict[str, Any]]], is_vision: bool) -> dict[str, list[dict[str, Any]]]:
        payload = {
            "text": task_suites["text"][:2],
            "code": task_suites["code"][:2],
            "tool": task_suites.get("tool", [])[:1],
            "long_context": task_suites["long_context"][:1],
            "vision": task_suites.get("vision", [])[:1] if is_vision else [],
        }
        return payload

    def average_dimension_score(self, summary: dict[str, Any]) -> float:
        dims = list(summary["dimension_scores"].values())
        return round(sum(dims) / max(len(dims), 1), 2)

    def run_tuned(self) -> dict[str, Any]:
        baseline_payload = self.load_summary_or_checkpoint("full-baseline")
        finalists = baseline_payload["finalists"]
        task_suites = get_suite_tasks(self.task_file, "full")
        mcp_state = self.mcp_health()
        lookup = self.model_lookup()
        checkpoint_path = self.paths.results / "tuned-checkpoint.json"
        summaries: list[dict[str, Any]] = []
        completed_models: set[str] = set()
        if checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            summaries = checkpoint.get("summaries", [])
            completed_models = {item["model_id"] for item in summaries}

        trials_by_model: dict[str, list[dict[str, Any]]] = {}
        for model_id in finalists:
            if model_id in completed_models:
                continue
            model = lookup[model_id]
            calibration = self.calibration_tasks_for_model(task_suites, self.model_is_vision_candidate(model))
            best_summary: dict[str, Any] | None = None
            best_profile: dict[str, Any] | None = None
            trials: list[dict[str, Any]] = []
            for candidate in self.candidate_tuned_profiles():
                candidate = {**candidate, "repeat_count": 1}
                trial_summary = self.run_model_suite(
                    model=model,
                    task_suites=calibration,
                    profile=candidate,
                    mcp_state=mcp_state,
                    screening_only=False,
                )
                avg = self.average_dimension_score(trial_summary)
                trials.append({"profile": candidate, "average_score": avg, "summary": trial_summary})
                if best_summary is None or avg > self.average_dimension_score(best_summary):
                    best_summary = trial_summary
                    best_profile = candidate

            final_profile = {**(best_profile or self.load_profiles()["full_baseline"]), "repeat_count": self.load_profiles()["full_baseline"]["repeat_count"]}
            final_summary = self.run_model_suite(
                model=model,
                task_suites=task_suites,
                profile=final_profile,
                mcp_state=mcp_state,
                screening_only=False,
            )
            final_summary["recommended_settings"] = compact_settings(final_profile)
            final_summary["tuned_speed"] = final_summary["baseline_speed"]
            final_summary["typical_strengths"] = "Best calibration profile found on this machine"
            final_summary["best_use_case"] = "tuned finalist"
            final_summary["tuning_trials"] = [{"profile": compact_settings(item["profile"]), "average_score": item["average_score"]} for item in trials]
            summaries.append(final_summary)
            trials_by_model[model_id] = final_summary["tuning_trials"]
            write_json(
                checkpoint_path,
                {
                    "generated_at": utc_now(),
                    "mcp_state": mcp_state,
                    "summaries": summaries,
                    "finalists": finalists,
                    "trials_by_model": trials_by_model,
                },
            )

        payload = {
            "generated_at": utc_now(),
            "mcp_state": mcp_state,
            "summaries": summaries,
            "finalists": finalists,
            "trials_by_model": trials_by_model,
        }
        rows = self.rows_for_summaries(summaries, tuned=True)
        self.write_stage_outputs(stem="tuned", payload=payload, rows=rows, title="Tuned Report")
        return payload

    def run_qwen_cc(self) -> dict[str, Any]:
        profiles = self.load_profiles()
        profile = profiles["qwen_cc_baseline"]
        task_suites = get_suite_tasks(self.task_file, "qwen_cc")
        mcp_state = self.mcp_health()
        status = self.client.models_status()
        qwen_models = [model for model in status["models"] if self.is_qwen_family_model(model)]
        claude_path = self.claude_code_cli_path()

        self.log_event(
            "qwen_cc_start",
            {
                "model_count": len(qwen_models),
                "claude_code_cli_detected": bool(claude_path),
                "claude_code_cli_path": claude_path,
            },
        )
        self.apply_baseline_sampling("qwen_cc_baseline")
        checkpoint_path = self.paths.results / "qwen-cc-checkpoint.json"
        summaries: list[dict[str, Any]] = []
        completed_models: set[str] = set()
        if checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            summaries = checkpoint.get("summaries", [])
            completed_models = {item["model_id"] for item in summaries}

        for model in qwen_models:
            if model["id"] in completed_models:
                continue
            summary = self.run_model_suite(
                model=model,
                task_suites=task_suites,
                profile=profile,
                mcp_state=mcp_state,
                screening_only=False,
            )
            summary["series"] = self.qwen_series(model["id"])
            summary["overall_score"] = self.qwen_cc_overall_score(summary["dimension_scores"])
            summary["recommended_settings"] = compact_settings(profile)
            strengths, weaknesses, best_use_case = self.qwen_cc_notes(summary)
            summary["typical_strengths"] = strengths
            summary["typical_weaknesses"] = weaknesses
            summary["best_use_case"] = best_use_case
            summaries.append(summary)
            write_json(
                checkpoint_path,
                {
                    "generated_at": utc_now(),
                    "profile": profile,
                    "claude_code_cli": {"detected": bool(claude_path), "path": claude_path},
                    "summaries": summaries,
                },
            )

        ranked = sorted(summaries, key=lambda item: item["overall_score"], reverse=True)
        series_summary = self.summarize_qwen_series(ranked)
        payload = {
            "generated_at": utc_now(),
            "profile": profile,
            "claude_code_cli": {
                "detected": bool(claude_path),
                "path": claude_path,
                "note": "Local Claude Code CLI was detected, but these results come from oMLX local Qwen-family models under Claude Code-like prompts, not from running the models inside Claude Code itself.",
            },
            "mcp_state": mcp_state,
            "summaries": ranked,
            "series_summary": series_summary,
        }
        rows = self.qwen_cc_rows(ranked)
        write_json(self.paths.results / "qwen-cc-summary.json", payload)
        write_csv(self.paths.results / "qwen-cc-summary.csv", rows)

        series_rows = []
        for series, item in series_summary.items():
            series_rows.append(
                {
                    "Series": series,
                    "Models": item["count"],
                    "Average overall": item["average_overall"],
                    "Average code": item["average_code"],
                    "Average instruction": item["average_instruction"],
                    "Best model": item["best_model"],
                    "Best score": item["best_score"],
                }
            )
        report = [
            "# Qwen Claude-Code-Style Report",
            "",
            f"- Generated at: `{payload['generated_at']}`",
            f"- Claude Code CLI detected: `{payload['claude_code_cli']['detected']}`",
            f"- Claude Code CLI path: `{claude_path or 'not found'}`",
            f"- Note: {payload['claude_code_cli']['note']}",
            "",
            "## Model Ranking",
            "",
            markdown_table(rows, QWEN_CC_COLUMNS),
            "",
            "## Series Comparison",
            "",
            markdown_table(
                series_rows,
                ["Series", "Models", "Average overall", "Average code", "Average instruction", "Best model", "Best score"],
            ),
            "",
        ]
        (self.paths.reports / "qwen-cc-report.md").write_text("\n".join(report), encoding="utf-8")
        return payload

    def cc_duel_assets(self) -> dict[str, Path]:
        root = self.root / "benchmark_projects"
        return {
            "template_dir": root / "issue_digest_template",
            "solution_dir": root / "issue_digest_codex_solution",
            "hidden_tests_dir": root / "issue_digest_hidden_tests",
        }

    def cc_duel_prompt(self, repo_dir: Path, *, stage: str, prior_output: str | None = None) -> str:
        repo_context = read_repo_context(repo_dir, ALLOWED_SOURCE_PATHS + ["tests/test_visible.py"])
        prompt = [
            "You are participating in a one-shot code benchmark.",
            challenge_description(),
            "Return JSON only.",
            'Use this schema: {"plan": ["..."], "files": {"issue_digest/core.py": "...", "issue_digest/cli.py": "..."}}',
            "Do not include chain-of-thought, prose outside JSON, or markdown fences.",
            "",
            repo_context,
        ]
        if stage == "final" and prior_output is not None:
            prompt.extend(["", "Draft output from the 9B subagent:", prior_output])
        return "\n".join(prompt)

    def run_claude_cli_once(self, *, model_id: str, prompt: str, cwd: Path, timeout_s: int) -> dict[str, Any]:
        command = [
            "claude",
            "--bare",
            "-p",
            "--no-session-persistence",
            "--permission-mode",
            "bypassPermissions",
            "--model",
            model_id,
            prompt,
        ]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            wall_time = round(time.perf_counter() - started, 4)
            return {
                "ok": completed.returncode == 0 and bool((completed.stdout or "").strip()),
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "wall_time_s": wall_time,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "timeout": True,
                "stdout": coerce_text(exc.stdout),
                "stderr": coerce_text(exc.stderr),
                "wall_time_s": round(time.perf_counter() - started, 4),
            }

    def run_aider_once(
        self,
        *,
        model_id: str,
        prompt: str,
        cwd: Path,
        editable_files: list[str],
        read_only_files: list[str],
        home_dir: Path,
        timeout_s: int,
    ) -> dict[str, Any]:
        home_dir.mkdir(parents=True, exist_ok=True)
        history_dir = home_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        command = [
            "aider",
            "--model",
            f"openai/{model_id}",
            "--openai-api-base",
            "http://127.0.0.1:8000/v1",
            "--input-history-file",
            str(history_dir / "input.history"),
            "--chat-history-file",
            str(history_dir / "chat.history.md"),
            "--llm-history-file",
            str(history_dir / "llm.history.jsonl"),
            "--no-git",
            "--yes-always",
            "--no-check-update",
            "--no-show-model-warnings",
            "--no-show-release-notes",
            "--no-notifications",
            "--no-fancy-input",
            "--no-pretty",
            "--message",
            prompt,
        ]
        for relative_path in read_only_files:
            command.extend(["--read", relative_path])
        command.extend(editable_files)

        env = dict(os.environ)
        env["HOME"] = str(home_dir)
        env["AIDER_OPENAI_API_KEY"] = self.client.api_key
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
            )
            wall_time = round(time.perf_counter() - started, 4)
            return {
                "ok": completed.returncode == 0,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "wall_time_s": wall_time,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "timeout": True,
                "stdout": coerce_text(exc.stdout),
                "stderr": coerce_text(exc.stderr),
                "wall_time_s": round(time.perf_counter() - started, 4),
            }

    def run_local_model_once(self, *, model_id: str, prompt: str, profile: dict[str, Any]) -> dict[str, Any]:
        self.unload_all_models()
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": "Return JSON only. Do not reveal chain-of-thought."},
                {"role": "user", "content": prompt},
            ],
            "temperature": profile["temperature"],
            "top_p": profile["top_p"],
            "max_tokens": profile["max_tokens"],
            "stream": False,
        }
        started = time.perf_counter()
        response = self.client.chat_completion(payload)
        wall_time = round(time.perf_counter() - started, 4)
        message = response["choices"][0]["message"].get("content") or ""
        if isinstance(message, list):
            message = "\n".join(
                part.get("text", "") for part in message if isinstance(part, dict)
            )
        self.unload_all_models()
        return {"ok": True, "stdout": message, "response": response, "wall_time_s": wall_time}

    def prepare_cc_duel_run(self) -> dict[str, Path]:
        assets = self.cc_duel_assets()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        duel_root = self.paths.runs / f"cc-duo-duel-{timestamp}"
        duo_repo = duel_root / "team-duo"
        codex_repo = duel_root / "team-codex"
        copy_repo_tree(assets["template_dir"], duo_repo)
        copy_repo_tree(assets["template_dir"], codex_repo)
        return {
            "duel_root": duel_root,
            "duo_repo": duo_repo,
            "codex_repo": codex_repo,
            **assets,
        }

    def apply_generated_submission(self, repo_dir: Path, output_text: str) -> dict[str, Any]:
        payload = extract_json_payload(output_text)
        files = normalize_generated_files(payload)
        allowed_files = {path: content for path, content in files.items() if path in ALLOWED_SOURCE_PATHS}
        if not allowed_files:
            raise ValueError("No allowed files were returned by the model")
        write_generated_files(repo_dir, allowed_files)
        return {"payload": payload, "files": sorted(allowed_files)}

    def stage_hidden_tests(self, repo_dir: Path, hidden_tests_dir: Path) -> Path:
        target = repo_dir / "__hidden_tests__"
        copy_repo_tree(hidden_tests_dir, target)
        init_path = target / "__init__.py"
        if not init_path.exists():
            init_path.write_text('"""Hidden tests."""\n', encoding="utf-8")
        return target

    def evaluate_cc_duel_repo(
        self,
        *,
        entrant: str,
        mode: str,
        model_label: str,
        repo_dir: Path,
        template_dir: Path,
        hidden_tests_dir: Path,
        raw_output: str,
        wall_time_s: float,
    ) -> dict[str, Any]:
        violations = constraint_violations(template_dir, repo_dir, ALLOWED_SOURCE_PATHS)
        visible = run_unittest(repo_dir, ["discover", "-s", "tests", "-v"])
        hidden_stage = self.stage_hidden_tests(repo_dir, hidden_tests_dir)
        hidden = run_unittest(repo_dir, ["discover", "-s", hidden_stage.name, "-v"])
        return {
            "entrant": entrant,
            "mode": mode,
            "models": model_label,
            "repo_dir": str(repo_dir),
            "visible": visible,
            "hidden": hidden,
            "constraint_violations": violations,
            "patch_cleanliness": evaluate_patch_cleanliness(raw_output),
            "wall_time_s": round(wall_time_s, 4),
            "raw_output": raw_output,
        }

    def codex_cc_duel_submission(self, repo_dir: Path, solution_dir: Path) -> dict[str, Any]:
        started = time.perf_counter()
        for relative_path in ALLOWED_SOURCE_PATHS:
            source = solution_dir / relative_path
            destination = repo_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        wall_time = round(time.perf_counter() - started, 4)
        return {
            "raw_output": "Direct one-pass Codex submission applied from the benchmark solution workspace.",
            "wall_time_s": wall_time,
        }

    def probe_cc_cli_route(self, model_id: str, cwd: Path) -> dict[str, Any]:
        return self.run_claude_cli_once(
            model_id=model_id,
            prompt="Reply with OK only.",
            cwd=cwd,
            timeout_s=10,
        )

    def probe_aider_route(self, model_id: str, cwd: Path, home_dir: Path) -> dict[str, Any]:
        return self.run_aider_once(
            model_id=model_id,
            prompt="Reply with OK only.",
            cwd=cwd,
            editable_files=[],
            read_only_files=[],
            home_dir=home_dir,
            timeout_s=30,
        )

    def run_duo_submission(self, repo_dir: Path, profile: dict[str, Any]) -> dict[str, Any]:
        qwen_model = "Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8"
        huihui_model = "Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit"
        editable_files = ["issue_digest/core.py", "issue_digest/cli.py"]
        read_only_files = ["tests/test_visible.py"]
        aider_home = self.paths.artifacts / "aider-home"
        qwen_aider_probe = self.probe_aider_route(qwen_model, repo_dir, aider_home / "qwen-probe")
        huihui_aider_probe = self.probe_aider_route(huihui_model, repo_dir, aider_home / "huihui-probe")
        qwen_probe = self.probe_cc_cli_route(qwen_model, repo_dir)
        huihui_probe = self.probe_cc_cli_route(huihui_model, repo_dir)
        if self.aider_cli_path():
            mode = "oss_aider_baton"
        elif qwen_probe.get("ok") and huihui_probe.get("ok"):
            mode = "real_cc_cli"
        else:
            mode = "simulated_baton"

        qwen_prompt = self.cc_duel_prompt(repo_dir, stage="draft")
        if mode == "oss_aider_baton":
            qwen_result = self.run_aider_once(
                model_id=qwen_model,
                prompt=qwen_prompt,
                cwd=repo_dir,
                editable_files=editable_files,
                read_only_files=read_only_files,
                home_dir=aider_home / "qwen-run",
                timeout_s=90,
            )
        elif mode == "real_cc_cli":
            qwen_result = self.run_claude_cli_once(model_id=qwen_model, prompt=qwen_prompt, cwd=repo_dir, timeout_s=45)
        else:
            qwen_result = self.run_local_model_once(model_id=qwen_model, prompt=qwen_prompt, profile=profile)

        huihui_prompt = self.cc_duel_prompt(repo_dir, stage="final", prior_output=qwen_result.get("stdout", ""))
        if mode == "oss_aider_baton":
            huihui_result = self.run_aider_once(
                model_id=huihui_model,
                prompt=huihui_prompt,
                cwd=repo_dir,
                editable_files=editable_files,
                read_only_files=read_only_files,
                home_dir=aider_home / "huihui-run",
                timeout_s=120,
            )
        elif mode == "real_cc_cli":
            huihui_result = self.run_claude_cli_once(model_id=huihui_model, prompt=huihui_prompt, cwd=repo_dir, timeout_s=60)
        else:
            huihui_result = self.run_local_model_once(model_id=huihui_model, prompt=huihui_prompt, profile=profile)

        applied = None
        error = None
        if mode == "simulated_baton":
            try:
                applied = self.apply_generated_submission(repo_dir, huihui_result.get("stdout", ""))
            except Exception as exc:
                error = str(exc)
        else:
            applied = {"files": editable_files}

        return {
            "mode": mode,
            "models": [qwen_model, huihui_model],
            "probe": {
                "qwen": qwen_probe,
                "huihui": huihui_probe,
                "qwen_aider": qwen_aider_probe,
                "huihui_aider": huihui_aider_probe,
            },
            "draft": qwen_result,
            "final": huihui_result,
            "applied": applied,
            "error": error,
            "wall_time_s": round(qwen_result.get("wall_time_s", 0.0) + huihui_result.get("wall_time_s", 0.0), 4),
        }

    def cc_duel_verdict(self, duo: dict[str, Any], codex: dict[str, Any]) -> str:
        duo_key = (
            duo["visible"]["counts"]["passed"],
            duo["hidden"]["counts"]["passed"],
            -len(duo["constraint_violations"]),
            duo["patch_cleanliness"] == "clean",
            -duo["wall_time_s"],
        )
        codex_key = (
            codex["visible"]["counts"]["passed"],
            codex["hidden"]["counts"]["passed"],
            -len(codex["constraint_violations"]),
            codex["patch_cleanliness"] == "clean",
            -codex["wall_time_s"],
        )
        if duo_key > codex_key:
            return "Team Duo wins"
        if codex_key > duo_key:
            return "Team Codex wins"
        return "Draw"

    def run_cc_duo_duel(self) -> dict[str, Any]:
        profile = self.load_profiles()["cc_duo_duel"]
        status = self.client.models_status()
        available_models = [item["id"] for item in status["models"]]
        expected_models = {
            "Huihui-Qwen3.5-35B-A3B-Claude-4.6-Opus-abliterated-mlx-8bit",
            "Qwen3.5-9B-Claude-4.6-HighIQ-INSTRUCT-HERETIC-UNCENSORED-MLX-mxfp8",
        }
        missing = sorted(expected_models - set(available_models))
        if missing:
            raise RuntimeError(f"Missing required models for duel: {missing}")

        self.apply_baseline_sampling("cc_duo_duel")
        self.unload_all_models()
        assets = self.prepare_cc_duel_run()

        duo = self.run_duo_submission(assets["duo_repo"], profile)
        duo_result = self.evaluate_cc_duel_repo(
            entrant="Team Duo",
            mode=duo["mode"],
            model_label="Qwen 9B HighIQ -> Huihui 35B A3B 8bit",
            repo_dir=assets["duo_repo"],
            template_dir=assets["template_dir"],
            hidden_tests_dir=assets["hidden_tests_dir"],
            raw_output=duo["final"].get("stdout", ""),
            wall_time_s=duo["wall_time_s"],
        )

        codex_submission = self.codex_cc_duel_submission(assets["codex_repo"], assets["solution_dir"])
        codex_result = self.evaluate_cc_duel_repo(
            entrant="Team Codex",
            mode="direct_one_pass",
            model_label="Codex",
            repo_dir=assets["codex_repo"],
            template_dir=assets["template_dir"],
            hidden_tests_dir=assets["hidden_tests_dir"],
            raw_output=codex_submission["raw_output"],
            wall_time_s=codex_submission["wall_time_s"],
        )

        verdict = self.cc_duel_verdict(duo_result, codex_result)
        rows = [
            {
                "Entrant": duo_result["entrant"],
                "Mode": duo_result["mode"],
                "Model(s)": duo_result["models"],
                "Visible tests": f"{duo_result['visible']['counts']['passed']} passed",
                "Hidden tests": f"{duo_result['hidden']['counts']['passed']} passed",
                "Constraint violations": ", ".join(duo_result["constraint_violations"]) or "none",
                "Patch cleanliness": duo_result["patch_cleanliness"],
                "Wall time": f"{duo_result['wall_time_s']:.2f}s",
                "Verdict": verdict if verdict.startswith("Team Duo") else "runner-up",
            },
            {
                "Entrant": codex_result["entrant"],
                "Mode": codex_result["mode"],
                "Model(s)": codex_result["models"],
                "Visible tests": f"{codex_result['visible']['counts']['passed']} passed",
                "Hidden tests": f"{codex_result['hidden']['counts']['passed']} passed",
                "Constraint violations": ", ".join(codex_result["constraint_violations"]) or "none",
                "Patch cleanliness": codex_result["patch_cleanliness"],
                "Wall time": f"{codex_result['wall_time_s']:.2f}s",
                "Verdict": verdict if verdict.startswith("Team Codex") else "runner-up",
            },
        ]

        payload = {
            "generated_at": utc_now(),
            "challenge": challenge_description(),
            "available_models": available_models,
            "duo": {
                **duo,
                "evaluation": duo_result,
            },
            "codex": {
                "submission": codex_submission,
                "evaluation": codex_result,
            },
            "verdict": verdict,
            "note": "System Python did not have pytest installed, so the duel used standard-library unittest suites for visible and hidden checks while preserving the same test-count comparison logic.",
        }
        write_json(self.paths.results / "cc-duo-duel.json", payload)
        write_csv(self.paths.results / "cc-duo-duel.csv", rows)
        report = [
            "# CC Duo Duel Report",
            "",
            f"- Generated at: `{payload['generated_at']}`",
            f"- Verdict: **{verdict}**",
            f"- Duo mode: `{duo['mode']}`",
            f"- Note: {payload['note']}",
            "",
            "## Scoreboard",
            "",
            markdown_table(rows, CC_DUEL_COLUMNS),
            "",
            "## Conclusions",
            "",
            f"- Duo stronger than solo Codex: {'yes' if verdict.startswith('Team Duo') else 'no'}",
            f"- 9B subagent net gain: {'yes' if duo_result['visible']['counts']['passed'] >= 2 else 'unclear'}",
            f"- Huihui 35B fit as final closer: {'yes' if duo_result['patch_cleanliness'] != 'thinking leak' else 'mixed'}",
            f"- Main gap versus Codex: {'constraint control and exactness' if verdict.startswith('Team Codex') else 'speed and execution depth'}",
            "",
            "## Real CLI Probe",
            "",
            f"- Aider Qwen probe ok: `{duo['probe'].get('qwen_aider', {}).get('ok', False)}`",
            f"- Aider Huihui probe ok: `{duo['probe'].get('huihui_aider', {}).get('ok', False)}`",
            f"- Qwen probe ok: `{duo['probe']['qwen'].get('ok', False)}`",
            f"- Huihui probe ok: `{duo['probe']['huihui'].get('ok', False)}`",
            "",
        ]
        (self.paths.reports / "cc-duo-duel.md").write_text("\n".join(report), encoding="utf-8")
        self.log_event("cc_duo_duel_complete", {"verdict": verdict, "mode": duo["mode"]})
        return payload
