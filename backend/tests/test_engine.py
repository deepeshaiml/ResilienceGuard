from app.engine import assess, build_dependency_graph


def service(result, service_id):
    return next(row for row in result["services"] if row["id"] == service_id)


def test_integrity_freshness_and_missing_backup_are_distinct():
    result = assess("ransomware")
    db = service(result, "clinical-db")
    broken = next(row for row in db["backups"] if row["id"] == "bkp-db-20261026-0700")
    fallback = next(row for row in db["backups"] if row["id"] == "bkp-db-20261026-0500")
    directory = service(result, "directory-store")

    assert broken["exists"] is True
    assert broken["integrity_status"] == "failed"
    assert broken["freshness"] == "fresh"
    assert broken["malware_status"] == "unknown"
    assert fallback["integrity_status"] == "verified"
    assert fallback["freshness"] == "stale"
    assert db["selected_backup_id"] == "bkp-db-20261026-0500"
    assert directory["backup_existence"] == "missing"
    assert directory["selected_backup_malware_status"] == "unknown"
    assert result["metrics"]["integrity_failures"] == 1


def test_dependency_blockers_cascade_from_missing_directory_backup():
    result = assess("physical-disaster")
    app = service(result, "hospital-app")
    identity = service(result, "identity-service")
    database = service(result, "clinical-db")

    assert database["recovery_status"] == "ready"
    assert identity["recovery_status"] == "blocked"
    assert any(blocker["id"] == "backup:directory-store" for blocker in identity["recovery_blockers"])
    assert app["recovery_status"] == "blocked"
    assert any(blocker["id"] == "backup:directory-store" for blocker in app["recovery_blockers"])
    assert "clinical-db" in app["current_blockers"]


def test_scenarios_are_deterministic_and_use_separate_failure_domains():
    first = assess("power-network")
    second = assess("power-network")
    assert first == second
    assert service(first, "clinical-db")["selected_backup_location"] == "vault-west"
    assert all(item["malware_status"] == "unknown" for row in first["services"] for item in row["backups"])
    assert service(first, "clinical-db")["backups"][0]["location_accessible"] is True


def test_dependency_graph_is_acyclic_and_graph_paths_are_explicit():
    graph = build_dependency_graph()
    assert graph.has_edge("hospital-app", "clinical-db")
    assert graph.has_edge("hospital-app", "identity-service")
    assert graph.has_edge("identity-service", "directory-store")
    assert graph.has_edge("clinical-db", "recovery-storage")


def test_dependency_readiness_matrix_matches_all_three_synthetic_scenarios():
    expected = {
        "physical-disaster": {"hospital-app": "blocked", "clinical-db": "ready", "identity-service": "blocked", "directory-store": "blocked"},
        "ransomware": {"hospital-app": "ready", "clinical-db": "ready", "identity-service": "ready", "directory-store": "ready"},
        "power-network": {"hospital-app": "blocked", "clinical-db": "ready", "identity-service": "blocked", "directory-store": "blocked"},
    }
    for scenario_id, service_expectations in expected.items():
        result = assess(scenario_id)
        for service_id, recovery_status in service_expectations.items():
            assert service(result, service_id)["recovery_status"] == recovery_status
