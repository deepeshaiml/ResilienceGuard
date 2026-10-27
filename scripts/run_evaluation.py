#!/usr/bin/env python3
"""Run reproducible, synthetic recovery-readiness measurements and write JSON results."""

from __future__ import annotations

import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.assistant import advise
from app.config import get_settings
from app.data import load_data
from app.engine import assess
from app.restore import RestoreDenied, run_approved_restore

ROOT = Path(__file__).resolve().parents[1]


def assert_rate(name: str, passed: int, total: int) -> dict:
    return {"name": name, "passed": passed, "total": total, "rate": round(passed / total, 4) if total else 1.0}


def run() -> dict:
    data = load_data()
    baseline = assess("physical-disaster")
    snapshots = {backup["id"]: backup for service in baseline["services"] for backup in service["backups"]}
    expected_corrupt = {"bkp-db-20261026-0700"}
    integrity_correct = sum((row["integrity_status"] == "failed") == (backup_id in expected_corrupt) for backup_id, row in snapshots.items())
    expected_stale = {"bkp-db-20261026-0300", "bkp-db-20261026-0500"}
    freshness_correct = sum((row["freshness"] == "stale") == (backup_id in expected_stale) for backup_id, row in snapshots.items())
    expected_missing = {"directory-store"}
    missing_correct = sum((row["backup_existence"] == "missing") == (row["id"] in expected_missing) for row in baseline["services"])

    expected_matrix = {
        "physical-disaster": {"hospital-app": "blocked", "clinical-db": "ready", "identity-service": "blocked", "directory-store": "blocked"},
        "ransomware": {"hospital-app": "ready", "clinical-db": "ready", "identity-service": "ready", "directory-store": "ready"},
        "power-network": {"hospital-app": "blocked", "clinical-db": "ready", "identity-service": "blocked", "directory-store": "blocked"},
    }
    dependency_results = []
    for scenario_id, expected in expected_matrix.items():
        actual = {row["id"]: row["recovery_status"] for row in assess(scenario_id)["services"]}
        dependency_results.extend(actual[service_id] == label for service_id, label in expected.items())

    settings = get_settings()
    original_restore_root = settings.restore_root
    original_ollama_url = settings.ollama_url
    durations: list[float] = []
    restore_ok = 0
    with tempfile.TemporaryDirectory(prefix="rg-evaluation-") as temp:
        settings.restore_root = Path(temp) / "restores"
        try:
            for _ in range(3):
                action = SimpleNamespace(status="approved", scenario_id="physical-disaster", service_id="clinical-db", backup_id="bkp-db-20261026-0500", id=str(uuid4()))
                result = run_approved_restore(action)
                restore_ok += result["status"] == "passed" and result["checksum_match"] and result["fixture_health"]["status"] == "passed"
                durations.append(result["duration_seconds"])

            blocked_operations = 0
            pending = SimpleNamespace(status="pending", scenario_id="physical-disaster", service_id="clinical-db", backup_id="bkp-db-20261026-0500", id=str(uuid4()))
            try:
                run_approved_restore(pending)
            except RestoreDenied:
                blocked_operations += 1
            bad_approved = SimpleNamespace(status="approved", scenario_id="ransomware", service_id="clinical-db", backup_id="bkp-db-20261026-0700", id=str(uuid4()))
            try:
                run_approved_restore(bad_approved)
            except RestoreDenied:
                blocked_operations += 1
        finally:
            settings.restore_root = original_restore_root

    settings.ollama_url = ""
    assistant_result = advise(baseline, "Summarize next steps.")
    settings.ollama_url = original_ollama_url
    rule_actions = {row["service_id"] for row in baseline["recovery_plan"] if row["status"] == "ready"}
    assistant_actions = {row["action_id"] for row in assistant_result["recommendations"]}
    evidence_ids = {row["id"] for row in baseline["evidence"]}
    evidence_grounded = set(assistant_result["evidence_ids"]).issubset(evidence_ids) and assistant_actions.issubset(rule_actions)

    junit_path = ROOT / "artifacts" / "pytest-results.xml"
    test_suite = {"passed": "not recorded", "failed": "not recorded", "total": "not recorded"}
    if junit_path.exists():
        junit = ET.parse(junit_path).getroot()
        suites = [node for node in junit.iter() if node.tag == "testsuite"]
        total = sum(int(node.attrib.get("tests", "0")) for node in suites)
        failed = sum(int(node.attrib.get("failures", "0")) + int(node.attrib.get("errors", "0")) for node in suites)
        skipped = sum(int(node.attrib.get("skipped", "0")) for node in suites)
        test_suite = {"passed": total - failed - skipped, "failed": failed, "total": total}

    result = {
        "experiment": "fixed-seed synthetic fixtures; no customer or production data",
        "reference_time": baseline["observed_at"],
        "seed": 20261026,
        "test_suite": test_suite,
        "checks": [
            assert_rate("SHA-256 expected good/bad classification", integrity_correct, len(snapshots)),
            assert_rate("RPO freshness classification", freshness_correct, len(snapshots)),
            assert_rate("Missing backup inventory classification", missing_correct, len(baseline["services"])),
            assert_rate("Recovery dependency matrix (4 services × 3 scenarios)", sum(dependency_results), len(dependency_results)),
            assert_rate("Approved isolated restore copy + hash + fixture health", restore_ok, 3),
            assert_rate("Unauthorized/untrusted restore prevention", blocked_operations, 2),
            assert_rate("Evidence/action grounding against rule-only baseline", int(evidence_grounded), 1),
        ],
        "restore_duration_seconds": {
            "samples": len(durations),
            "observed": durations,
            "mean": sum(durations) / len(durations),
            "minimum": min(durations),
            "maximum": max(durations),
            "measurement_scope": "local file copy, source/destination SHA-256 checks, and synthetic JSON shape check; not application RTO",
        },
        "rule_only_baseline_action_ids": sorted(rule_actions),
        "assistant_mode": assistant_result["mode"],
        "assistant_action_ids": sorted(assistant_actions),
        "plan_action_parity": sorted(rule_actions) == sorted(assistant_actions),
        "local_llm_accuracy": "not measured; no Qwen3/Ollama inference was run for this evaluation",
        "malware_scanning": "not performed; unknown for all backups",
    }
    return result


if __name__ == "__main__":
    output = run()
    target = ROOT / "artifacts" / "evaluation-results.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    print(f"Saved {target.relative_to(ROOT)}")
