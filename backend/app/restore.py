"""Constrained restore runner: approved fixture file -> isolated output directory."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any

from .config import get_settings
from .data import backup_by_id, backup_file_path, load_data, scenario_by_id
from .engine import assess


class RestoreDenied(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fixture_health(path: Path) -> dict[str, Any]:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "failed", "detail": f"restored fixture is not valid JSON: {exc}"}
    records = content.get("records")
    valid = (
        content.get("fixture") is True
        and isinstance(records, list)
        and content.get("record_count") == len(records)
        and all(isinstance(row, dict) and row.get("synthetic") is True for row in records)
    )
    return {
        "status": "passed" if valid else "failed",
        "check": "synthetic_snapshot_shape_and_record_count",
        "record_count": len(records) if isinstance(records, list) else None,
        "database_engine_tested": False,
        "detail": "Validated the synthetic JSON snapshot structure; no PostgreSQL application restore was performed." if valid else "Synthetic snapshot schema validation failed.",
    }


def run_approved_restore(action: Any) -> dict[str, Any]:
    if getattr(action, "status", None) != "approved":
        raise RestoreDenied("A human-approved action is required before a sandbox restore")

    scenario = scenario_by_id(action.scenario_id)
    if scenario is None:
        raise RestoreDenied("Unknown scenario")
    backup = backup_by_id(action.backup_id)
    if backup is None or backup["service_id"] != action.service_id:
        raise RestoreDenied("Backup is not registered for the requested service")
    assessment = assess(action.scenario_id)
    service = next((row for row in assessment["services"] if row["id"] == action.service_id), None)
    candidate = next((row for row in service["backups"] if row["id"] == action.backup_id), None) if service else None
    if not candidate or not candidate["usable"]:
        raise RestoreDenied("Backup is missing, inaccessible, corrupted, or untrusted for this scenario")

    source = backup_file_path(backup["relative_path"])
    if not source.is_file() or _sha256(source) != backup["manifest_sha256"]:
        raise RestoreDenied("Source backup failed SHA-256 verification")

    settings = get_settings()
    root = settings.restore_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    action_dir = (root / action.id).resolve()
    if not action_dir.is_relative_to(root) or action_dir.exists():
        raise RestoreDenied("Unsafe or already-used restore target")
    action_dir.mkdir(mode=0o700)
    destination = action_dir / f"restored-{action.service_id}.json"
    start = time.perf_counter()
    shutil.copyfile(source, destination)
    source_digest = _sha256(source)
    restored_digest = _sha256(destination)
    health = _fixture_health(destination)
    elapsed = max(0.0, time.perf_counter() - start)
    success = source_digest == restored_digest == backup["manifest_sha256"] and health["status"] == "passed"
    return {
        "status": "passed" if success else "failed",
        "backup_id": backup["id"],
        "evidence_id": backup["evidence_id"],
        "restored_file": destination.name,
        "bytes_copied": destination.stat().st_size,
        "source_sha256": source_digest,
        "restored_sha256": restored_digest,
        "checksum_match": source_digest == restored_digest == backup["manifest_sha256"],
        "fixture_health": health,
        "malware_status": "unknown",
        "duration_seconds": elapsed,
        "sandbox_only": True,
        "production_modified": False,
        "output_relpath": str(destination.relative_to(root)),
    }
