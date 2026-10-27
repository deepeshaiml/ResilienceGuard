import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import get_settings


@lru_cache
def load_data() -> dict[str, Any]:
    root = get_settings().data_root
    with (root / "service_catalog.json").open(encoding="utf-8") as f:
        services = json.load(f)
    with (root / "backup_records.json").open(encoding="utf-8") as f:
        backups = json.load(f)
    with (root / "scenarios.json").open(encoding="utf-8") as f:
        scenarios = json.load(f)
    with (root / "infrastructure.json").open(encoding="utf-8") as f:
        infrastructure = json.load(f)
    return {"services": services, "backups": backups, "scenarios": scenarios, "infrastructure": infrastructure}


def reset_data_cache() -> None:
    load_data.cache_clear()


def scenario_by_id(scenario_id: str) -> dict[str, Any] | None:
    return next((s for s in load_data()["scenarios"] if s["id"] == scenario_id), None)


def backup_by_id(backup_id: str) -> dict[str, Any] | None:
    return next((b for b in load_data()["backups"] if b["id"] == backup_id), None)


def service_by_id(service_id: str) -> dict[str, Any] | None:
    return next((s for s in load_data()["services"] if s["id"] == service_id), None)


def backup_file_path(relative_path: str) -> Path:
    backup_root = (get_settings().data_root / "backups").resolve()
    path = (backup_root / relative_path).resolve()
    if not path.is_relative_to(backup_root):
        raise ValueError("Backup path escapes the synthetic fixture directory")
    return path
