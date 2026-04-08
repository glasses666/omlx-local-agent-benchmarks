from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .admin_api import OMLXAdminClient
from .backup import backup_file
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

    def vision_smoke_test(self, model_id: str, task: dict, profile: dict) -> dict[str, Any]:
        result = self.execute_chat_task(model_id, task, profile, repeats=1)
        success = result["median_score"] > 0
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
            return {
                "task_id": task["id"],
                "dimension": task["dimension"],
                "mode": task["mode"],
                "deferred": True,
                "reason": "mcp_unhealthy",
                "median_score": 0.0,
                "usage": {},
            }
        if task["mode"] == "responses":
            return self.execute_responses_task(model_id, task, profile)
        return self.execute_chat_task(model_id, task, profile, repeats=repeats)

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

    def run_screening(self) -> dict[str, Any]:
        profiles = json.loads(self.profiles_file.read_text(encoding="utf-8"))
        profile = profiles["screening_baseline"]
        mcp_state = self.mcp_health()
        status = self.client.models_status()
        task_suites = get_suite_tasks(self.task_file, "screening")

        self.apply_baseline_sampling("screening_baseline")
        summaries = []
        finalists = []
        lightest_text = None
        best_vision = None

        for model in status["models"]:
            self.unload_all_models()
            self.log_event("model_start", {"model_id": model["id"], "stage": "screening"})
            vision_capable = False
            stage_results = []

            for task in task_suites["text"] + task_suites["code"] + task_suites["long_context"]:
                stage_results.append(self.execute_task(model["id"], task, profile, profile["repeat_count"], mcp_state["healthy"]))

            stage_results.append(self.execute_task(model["id"], task_suites["tool"][0], profile, 1, mcp_state["healthy"]))

            if self.model_is_vision_candidate(model):
                smoke = self.vision_smoke_test(model["id"], task_suites["vision"][0], profile)
                vision_capable = smoke["success"]
                stage_results.append(smoke["result"])
                stage_results.append(self.execute_task(model["id"], task_suites["vision"][1], profile, 1, mcp_state["healthy"]))

            summary = self.summarize_model(model, stage_results, vision_capable, screening_only=True)
            summaries.append(summary)
            self.unload_all_models()

            if model["model_type"] == "llm":
                if lightest_text is None or model["estimated_size"] < lightest_text["estimated_size"]:
                    lightest_text = model
            if vision_capable and (best_vision is None or summary["overall_score"] > best_vision["overall_score"]):
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
