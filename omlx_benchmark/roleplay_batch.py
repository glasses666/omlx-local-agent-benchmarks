from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def hermes_roleplay_script() -> Path:
    return Path.home() / '.hermes' / 'hermes-agent' / 'environments' / 'roleplay_persona_env' / 'run_local_roleplay_batch.py'


def hermes_venv_python() -> Path:
    return Path.home() / '.hermes' / 'hermes-agent' / 'venv' / 'bin' / 'python'


def run_roleplay_full_batch(
    *,
    root: Path,
    model_filter: str | None = None,
    persona_filter: str | None = None,
    scenario_filter: str | None = None,
    max_cases: int | None = None,
) -> dict[str, Any]:
    script = hermes_roleplay_script()
    python_bin = hermes_venv_python()
    if not script.exists():
        raise FileNotFoundError(script)
    if not python_bin.exists():
        raise FileNotFoundError(python_bin)

    cmd = [str(python_bin), str(script)]
    if model_filter:
        cmd += ['--model-filter', model_filter]
    if persona_filter:
        cmd += ['--persona-filter', persona_filter]
    if scenario_filter:
        cmd += ['--scenario-filter', scenario_filter]
    if max_cases is not None:
        cmd += ['--max-cases', str(max_cases)]

    subprocess.run(cmd, cwd=str(Path.home() / '.hermes' / 'hermes-agent'), check=True)
    summary_path = root / 'results' / 'roleplay-full-summary.json'
    if not summary_path.exists():
        raise FileNotFoundError(summary_path)
    payload = json.loads(summary_path.read_text(encoding='utf-8'))
    return {'summary_path': str(summary_path), 'payload': payload}
