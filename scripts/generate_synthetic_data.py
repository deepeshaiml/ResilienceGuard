#!/usr/bin/env python3
"""Generate fixed-seed ResilienceGuard demo inventory and sample snapshots."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BACKUPS = DATA / "backups"
SEED = 20261026
AS_OF = "2026-10-26T08:00:00Z"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stamp(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)


def snapshot(kind: str, records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "fixture": True,
        "data_type": kind,
        "schema_version": 1,
        "records": records,
        "record_count": len(records),
    }


def main() -> None:
    rng = random.Random(SEED)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    for old in BACKUPS.iterdir():
        if old.is_file():
            old.unlink()

    clinical_rows = [
        {"record_id": f"SIM-P-{i:04d}", "encounter_code": f"E-{rng.randrange(100000, 999999)}", "synthetic": True}
        for i in range(1, 21)
    ]
    app_rows = [
        {"record_id": f"SIM-A-{i:04d}", "queue": "triage" if i % 2 else "lab", "synthetic": True}
        for i in range(1, 13)
    ]
    identity_rows = [
        {"principal_id": f"SIM-U-{i:04d}", "role": "clinician" if i % 2 else "operator", "synthetic": True}
        for i in range(1, 9)
    ]

    specifications = [
        ("bkp-app-20261026-0600", "hospital-app", "2026-10-26T06:00:00Z", "vault-west", "application", app_rows, False),
        ("bkp-db-20261026-0300", "clinical-db", "2026-10-26T03:00:00Z", "vault-east", "database", clinical_rows, False),
        ("bkp-db-20261026-0500", "clinical-db", "2026-10-26T05:00:00Z", "vault-west", "database", clinical_rows, False),
        ("bkp-db-20261026-0700", "clinical-db", "2026-10-26T07:00:00Z", "vault-west", "database", clinical_rows, True),
        ("bkp-id-20261026-0715", "identity-service", "2026-10-26T07:15:00Z", "vault-west", "identity", identity_rows, False),
    ]
    backups = []
    for backup_id, service_id, created_at, location_id, data_type, rows, corrupt in specifications:
        filename = f"{backup_id}.json"
        payload = snapshot(data_type, rows)
        path = BACKUPS / filename
        encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        expected = hashlib.sha256(encoded).hexdigest()
        if corrupt:
            encoded = encoded.replace(b"SIM-P-0001", b"TAMPERED-P-0001", 1)
        path.write_bytes(encoded)
        backups.append({
            "id": backup_id,
            "service_id": service_id,
            "created_at": created_at,
            "location_id": location_id,
            "relative_path": filename,
            "manifest_sha256": expected,
            "evidence_id": f"BK-{len(backups) + 1:03d}",
            "retention_class": "daily-30d",
            "synthetic": True,
            "scenario_untrusted": ["ransomware" ] if corrupt else [],
        })
    write_json(DATA / "backup_records.json", backups)

    services = [
        {"id": "hospital-app", "name": "Hospital Care Coordination", "tier": 0, "rpo_seconds": 14400, "rto_seconds": 7200, "estimated_restore_seconds": 95, "dependencies": ["clinical-db", "identity-service"], "critical": True},
        {"id": "clinical-db", "name": "Clinical Records Database", "tier": 0, "rpo_seconds": 7200, "rto_seconds": 3600, "estimated_restore_seconds": 150, "dependencies": ["recovery-storage", "recovery-network"], "critical": True},
        {"id": "identity-service", "name": "Clinical Identity Service", "tier": 0, "rpo_seconds": 3600, "rto_seconds": 1800, "estimated_restore_seconds": 75, "dependencies": ["directory-store", "recovery-network"], "critical": True},
        {"id": "directory-store", "name": "Directory Data Store", "tier": 1, "rpo_seconds": 14400, "rto_seconds": 3600, "estimated_restore_seconds": 60, "dependencies": ["recovery-storage", "recovery-network"], "critical": True},
    ]
    write_json(DATA / "service_catalog.json", services)

    infrastructure = [
        {"id": "primary-compute", "name": "Primary data center compute", "failure_domain": "dc-primary", "kind": "compute"},
        {"id": "primary-network", "name": "Primary site network", "failure_domain": "dc-primary", "kind": "network"},
        {"id": "primary-storage", "name": "Primary storage array", "failure_domain": "dc-primary", "kind": "storage"},
        {"id": "recovery-storage", "name": "Recovery site storage", "failure_domain": "dc-recovery", "kind": "storage"},
        {"id": "recovery-network", "name": "Independent recovery network", "failure_domain": "dc-recovery", "kind": "network"},
        {"id": "recovery-compute", "name": "Isolated recovery host", "failure_domain": "dc-recovery", "kind": "compute"},
        {"id": "vault-east", "name": "East backup vault", "failure_domain": "dc-primary", "kind": "backup_location"},
        {"id": "vault-west", "name": "West backup vault", "failure_domain": "dc-recovery", "kind": "backup_location"},
    ]
    write_json(DATA / "infrastructure.json", infrastructure)

    scenarios = [
        {
            "id": "physical-disaster", "name": "Primary data center lost", "description": "Physical loss of the primary data center; the independent recovery site and west vault remain available.", "as_of": AS_OF,
            "unavailable_nodes": ["hospital-app", "clinical-db", "identity-service", "directory-store", "primary-compute", "primary-network", "primary-storage", "vault-east"],
            "unavailable_locations": ["vault-east"], "untrusted_backup_ids": [],
            "evidence_id": "SC-001"
        },
        {
            "id": "ransomware", "name": "Ransomware and untrusted snapshot", "description": "A ransomware event leaves the newest clinical database snapshot corrupted and explicitly untrusted; older recovery points remain for comparison.", "as_of": AS_OF,
            "unavailable_nodes": ["hospital-app", "clinical-db"], "unavailable_locations": [], "untrusted_backup_ids": ["bkp-db-20261026-0700"],
            "evidence_id": "SC-002"
        },
        {
            "id": "power-network", "name": "Concurrent power and network disruption", "description": "Primary site power and network fail while the east vault is lost; the west vault and isolated recovery network remain reachable.", "as_of": AS_OF,
            "unavailable_nodes": ["hospital-app", "clinical-db", "identity-service", "directory-store", "primary-compute", "primary-network", "primary-storage", "vault-east"],
            "unavailable_locations": ["vault-east"], "untrusted_backup_ids": [],
            "evidence_id": "SC-003"
        },
    ]
    write_json(DATA / "scenarios.json", scenarios)

    print(f"Generated {len(services)} services, {len(backups)} backup records, {len(scenarios)} scenarios (seed={SEED}, as_of={AS_OF}).")


if __name__ == "__main__":
    main()
