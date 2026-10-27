"""Deterministic backup and dependency assessment. No model controls these results."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx

from .config import get_settings
from .data import backup_file_path, load_data, scenario_by_id


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_dependency_graph(data: dict[str, Any] | None = None) -> nx.DiGraph:
    data = data or load_data()
    graph = nx.DiGraph()
    for service in data["services"]:
        graph.add_node(service["id"], kind="service", name=service["name"])
    for item in data["infrastructure"]:
        graph.add_node(item["id"], kind=item["kind"], name=item["name"])
    for service in data["services"]:
        for dependency in service["dependencies"]:
            if dependency not in graph:
                raise ValueError(f"Unknown dependency {dependency!r} for {service['id']}")
            graph.add_edge(service["id"], dependency)
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("Dependency inventory must be a directed acyclic graph")
    return graph


def assess(scenario_id: str, successful_restores: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    data = load_data()
    scenario = scenario_by_id(scenario_id)
    if scenario is None:
        raise KeyError(f"Unknown scenario: {scenario_id}")
    graph = build_dependency_graph(data)
    as_of = _parse_time(scenario["as_of"])
    unavailable = set(scenario["unavailable_nodes"])
    inaccessible_locations = set(scenario["unavailable_locations"])
    untrusted_ids = set(scenario["untrusted_backup_ids"])
    infrastructure = {item["id"]: item for item in data["infrastructure"]}
    service_by_id = {service["id"]: service for service in data["services"]}
    backups_by_service: dict[str, list[dict[str, Any]]] = {service["id"]: [] for service in data["services"]}
    backup_results: dict[str, dict[str, Any]] = {}

    for backup in data["backups"]:
        try:
            path = backup_file_path(backup["relative_path"])
            exists = path.is_file()
            integrity = "not_checked" if not exists else ("verified" if _hash(path) == backup["manifest_sha256"] else "failed")
        except (OSError, ValueError):
            path = None
            exists = False
            integrity = "failed"
        age_seconds = max(0, int((as_of - _parse_time(backup["created_at"])).total_seconds()))
        service = service_by_id[backup["service_id"]]
        fresh = age_seconds <= service["rpo_seconds"]
        location_accessible = backup["location_id"] not in inaccessible_locations and backup["location_id"] not in unavailable
        scenario_untrusted = backup["id"] in untrusted_ids or scenario_id in backup.get("scenario_untrusted", [])
        result = {
            **backup,
            "exists": exists,
            "age_seconds": age_seconds,
            "freshness": "fresh" if fresh else "stale",
            "integrity_status": integrity,
            "location_accessible": location_accessible,
            "malware_status": "unknown",
            "restore_status": "not_tested",
            "scenario_trust": "untrusted" if scenario_untrusted else "not_assessed",
            "usable": bool(exists and integrity == "verified" and location_accessible and not scenario_untrusted),
            "path": str(path) if path else None,
        }
        backup_results[backup["id"]] = result
        backups_by_service[backup["service_id"]].append(result)

    for service_backups in backups_by_service.values():
        service_backups.sort(key=lambda row: row["created_at"], reverse=True)

    memo: dict[str, tuple[bool, list[dict[str, str]]]] = {}

    def recovery_ready(node_id: str) -> tuple[bool, list[dict[str, str]]]:
        if node_id in infrastructure:
            if node_id in unavailable:
                return False, [{"id": node_id, "reason": "required recovery infrastructure is unavailable"}]
            return True, []
        if node_id in memo:
            return memo[node_id]
        if node_id not in unavailable:
            memo[node_id] = (True, [])
            return memo[node_id]

        candidates = [row for row in backups_by_service[node_id] if row["usable"]]
        blockers: list[dict[str, str]] = []
        if not candidates:
            service_backups = backups_by_service[node_id]
            if not service_backups:
                blockers.append({"id": f"backup:{node_id}", "reason": "no backup record exists"})
            elif not any(row["exists"] for row in service_backups):
                blockers.append({"id": f"backup:{node_id}", "reason": "backup files are missing"})
            elif not any(row["integrity_status"] == "verified" for row in service_backups):
                blockers.append({"id": f"backup:{node_id}", "reason": "no backup passes SHA-256 integrity verification"})
            elif not any(row["location_accessible"] for row in service_backups):
                blockers.append({"id": f"backup:{node_id}", "reason": "no verified backup location is reachable in this scenario"})
            else:
                blockers.append({"id": f"backup:{node_id}", "reason": "remaining candidate is marked untrusted by this scenario"})
        for dependency in sorted(graph.successors(node_id)):
            ready, child_blockers = recovery_ready(dependency)
            if not ready:
                blockers.extend(child_blockers)
        ready = bool(candidates) and not blockers
        memo[node_id] = (ready, blockers)
        return memo[node_id]

    current_unavailable_by_service: dict[str, list[str]] = {}
    service_rows = []
    for service in data["services"]:
        service_id = service["id"]
        dependent_failures = sorted(
            node_id for node_id in nx.descendants(graph, service_id)
            if node_id in unavailable and node_id != service_id
        )
        current_unavailable_by_service[service_id] = dependent_failures
        ready, recovery_blockers = recovery_ready(service_id)
        candidates = [row for row in backups_by_service[service_id] if row["usable"]]
        selected = candidates[0] if candidates else None
        newest = backups_by_service[service_id][0] if backups_by_service[service_id] else None
        rpo_gap = max(0, selected["age_seconds"] - service["rpo_seconds"]) if selected else None
        successful = (successful_restores or {}).get(service_id)
        for backup in backups_by_service[service_id]:
            if successful and successful.get("backup_id") == backup["id"] and successful.get("status") == "completed":
                backup["restore_status"] = "passed"
        service_rows.append({
            "id": service_id,
            "name": service["name"],
            "critical": service["critical"],
            "tier": service["tier"],
            "status": "unavailable" if service_id in unavailable else "available",
            "dependencies": service["dependencies"],
            "current_blockers": dependent_failures,
            "backup_existence": "present" if backups_by_service[service_id] else "missing",
            "backup_count": len(backups_by_service[service_id]),
            "latest_backup_age_seconds": newest["age_seconds"] if newest else None,
            "latest_backup_freshness": newest["freshness"] if newest else "missing",
            "selected_backup_id": selected["id"] if selected else None,
            "selected_backup_evidence_id": selected["evidence_id"] if selected else None,
            "selected_backup_freshness": selected["freshness"] if selected else "unavailable",
            "selected_backup_integrity": selected["integrity_status"] if selected else "unavailable",
            "selected_backup_location": selected["location_id"] if selected else None,
            "selected_backup_malware_status": selected["malware_status"] if selected else "unknown",
            "rpo_target_seconds": service["rpo_seconds"],
            "rpo_gap_seconds": rpo_gap,
            "rto_target_seconds": service["rto_seconds"],
            "estimated_restore_seconds": service["estimated_restore_seconds"],
            "estimated_rto_gap_seconds": max(0, service["estimated_restore_seconds"] - service["rto_seconds"]),
            "recovery_status": "ready" if ready else "blocked",
            "recovery_blockers": recovery_blockers,
            "restore_test": successful or {"status": "not_tested"},
            "backups": [dict(row, path=None) for row in backups_by_service[service_id]],
        })

    service_graph = nx.DiGraph()
    service_graph.add_nodes_from(service_by_id)
    for service in data["services"]:
        for dependency in service["dependencies"]:
            if dependency in service_by_id:
                service_graph.add_edge(service["id"], dependency)
    sequence = list(nx.topological_sort(service_graph.reverse()))
    service_order = {service_id: index + 1 for index, service_id in enumerate(sequence)}
    plan = [
        {"order": service_order[service["id"]], "service_id": service["id"], "service": service["name"], "status": service["recovery_status"], "backup_id": service["selected_backup_id"], "evidence_id": service["selected_backup_evidence_id"]}
        for service in sorted(service_rows, key=lambda item: service_order[item["id"]])
        if service["id"] in unavailable
    ]
    evidence = []
    for service in service_rows:
        if service["backup_count"]:
            for backup in service["backups"]:
                evidence.append({"id": backup["evidence_id"], "type": "backup", "subject": service["name"], "detail": f"{backup['id']} at {backup['location_id']}; integrity {backup['integrity_status']}; freshness {backup['freshness']}; malware status unknown"})
        else:
            evidence.append({"id": f"MISS-{service['id']}", "type": "missing_backup", "subject": service["name"], "detail": "No backup record was supplied in the synthetic inventory."})
    for infrastructure_item in data["infrastructure"]:
        evidence.append({"id": f"INF-{infrastructure_item['id']}", "type": "infrastructure", "subject": infrastructure_item["name"], "detail": "Unavailable in scenario" if infrastructure_item["id"] in unavailable else "Available in scenario"})

    metrics = {
        "service_count": len(service_rows),
        "unavailable_services": sum(row["status"] == "unavailable" for row in service_rows),
        "ready_to_recover": sum(row["recovery_status"] == "ready" for row in service_rows if row["status"] == "unavailable"),
        "blocked_services": sum(row["recovery_status"] == "blocked" for row in service_rows if row["status"] == "unavailable"),
        "backup_count": len(data["backups"]),
        "missing_backup_services": sum(row["backup_existence"] == "missing" for row in service_rows),
        "stale_usable_backups": sum(row["usable"] and row["freshness"] == "stale" for row in backup_results.values()),
        "integrity_failures": sum(row["integrity_status"] == "failed" for row in backup_results.values()),
        "malware_scans_performed": 0,
    }
    return {
        "scenario": scenario,
        "observed_at": scenario["as_of"],
        "data_classification": "synthetic demo data",
        "metrics": metrics,
        "services": service_rows,
        "recovery_plan": plan,
        "evidence": evidence,
        "assurance_notes": [
            "File existence, freshness, SHA-256 integrity, malware status, and restore-test status are separate observations.",
            "A matching SHA-256 digest does not establish that data is malware-free or trustworthy.",
            "Malware scanning is not performed; malware status remains unknown.",
            "Restore observations apply only to the synthetic fixture file and isolated output directory.",
        ],
    }
