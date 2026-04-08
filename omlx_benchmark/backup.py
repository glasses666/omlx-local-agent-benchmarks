from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_file(source: Path, backup_dir: Path, manifest_path: Path, kind: str) -> dict:
    if not source.exists():
        raise FileNotFoundError(source)

    backup_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_name = f"{timestamp}-{source.name}"
    destination = backup_dir / backup_name
    shutil.copy2(source, destination)

    record = {
        "kind": kind,
        "source_path": str(source),
        "backup_path": str(destination),
        "backup_name": backup_name,
        "sha256": sha256_file(destination),
        "timestamp_utc": timestamp,
    }

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"records": []}
    manifest["records"].append(record)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return record
